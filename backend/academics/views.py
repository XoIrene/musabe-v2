from datetime import date as date_cls
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Count
from rest_framework import viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response

from core import audit
from core.models import Role
from core.permissions import has_role
from students.models import ClassRoom, Student
from students.views import assert_branch, students_for
from .models import Assessment, Attendance, Mark, Subject, Term
from .serializers import AssessmentSerializer, SubjectSerializer, TermSerializer

SETUP = (Role.ADMIN, Role.HEAD_MASTER, Role.ACADEMIC_MASTER)
TEACHING = (Role.HEAD_MASTER, Role.ACADEMIC_MASTER, Role.STAFF)
READERS = (Role.MANAGER, Role.LIBRARIAN, Role.STAFF, Role.PARENT)


def scope(user, qs, field='branch'):
    return qs if user.is_central else qs.filter(**{f'{field}__in': user.branch_ids()})


class BranchSetupViewSet(viewsets.ModelViewSet):
    """Subjects and terms: set up by the Admin, Head Master or Academic Master of that school."""
    permission_classes = [has_role(*SETUP, read=(Role.MANAGER, Role.LIBRARIAN, Role.STAFF))]
    http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        qs = scope(self.request.user, super().get_queryset())
        return qs.filter(branch=self.request.query_params['branch']) if self.request.query_params.get('branch') else qs

    def perform_create(self, serializer):
        assert_branch(self.request.user, serializer.validated_data['branch'].pk)
        audit.log(self.request.user, f'{self.queryset.model.__name__.lower()}.created', serializer.save())

    def perform_update(self, serializer):
        assert_branch(self.request.user, serializer.instance.branch_id)
        serializer.save()

    def perform_destroy(self, instance):
        assert_branch(self.request.user, instance.branch_id)
        instance.delete()


class SubjectViewSet(BranchSetupViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer


class TermViewSet(BranchSetupViewSet):
    queryset = Term.objects.select_related('branch')
    serializer_class = TermSerializer


class AssessmentViewSet(viewsets.ModelViewSet):
    """Tests and exams. Teachers, the Academic Master and the Head Master create them and enter marks."""
    serializer_class = AssessmentSerializer
    permission_classes = [has_role(*TEACHING, read=(Role.ADMIN, Role.MANAGER))]
    http_method_names = ['get', 'post', 'put', 'patch', 'head', 'options']

    def get_queryset(self):
        qs = scope(self.request.user, Assessment.objects.select_related('term', 'subject', 'classroom'))
        p = self.request.query_params
        for key in ('term', 'classroom', 'subject'):
            if p.get(key):
                qs = qs.filter(**{key: p[key]})
        return qs

    def perform_create(self, serializer):
        room = serializer.validated_data['classroom']
        assert_branch(self.request.user, room.branch_id)
        audit.log(self.request.user, 'assessment.created',
                  serializer.save(branch=room.branch, created_by=self.request.user))

    @action(detail=True, methods=['get', 'post'])
    def marks(self, request, pk=None):
        """GET: the class list with any marks. POST {marks:[{student, score}]}: save or update marks."""
        a = self.get_object()
        students = a.classroom.students.filter(status='ACTIVE')
        if request.method == 'GET':
            scores = {m.student_id: m.score for m in a.marks.all()}
            return Response({'assessment': AssessmentSerializer(a).data, 'students': [
                {'student': s.id, 'admission_no': s.admission_no, 'full_name': s.full_name,
                 'score': scores.get(s.id)} for s in students]})
        if request.user.is_central:
            raise PermissionDenied('Marks are entered by school staff.')
        ids = set(students.values_list('id', flat=True))
        with transaction.atomic():
            for row in request.data.get('marks', []):
                if row.get('score') in (None, ''):
                    continue
                try:
                    score = Decimal(str(row['score']))
                except InvalidOperation:
                    raise ValidationError(f"Bad score for student {row.get('student')}.")
                if row.get('student') not in ids:
                    raise ValidationError(f"Student {row.get('student')} is not in this class.")
                if not 0 <= score <= a.max_score:
                    raise ValidationError(f'Scores must be between 0 and {a.max_score}.')
                Mark.objects.update_or_create(assessment=a, student_id=row['student'],
                                              defaults={'score': score, 'entered_by': request.user})
            audit.log(request.user, 'marks.saved', a, f'{a.subject.name} {a.name}: {a.marks.count()} marks')
        return Response({'saved': a.marks.count()})


class AttendanceViewSet(viewsets.GenericViewSet):
    """Daily class register."""
    permission_classes = [has_role(*TEACHING, read=(Role.ADMIN, Role.MANAGER))]

    def _room(self, request, room_id):
        room = scope(request.user, ClassRoom.objects.all()).filter(pk=room_id).first()
        if not room:
            raise NotFound('No such class.')
        return room

    def list(self, request):
        """GET ?classroom=&date=  ->  the class list with that day's marks (default today)."""
        room = self._room(request, request.query_params.get('classroom'))
        day = request.query_params.get('date') or date_cls.today().isoformat()
        got = dict(Attendance.objects.filter(student__classroom=room, date=day).values_list('student_id', 'status'))
        return Response({'date': day, 'students': [
            {'student': s.id, 'admission_no': s.admission_no, 'full_name': s.full_name, 'status': got.get(s.id)}
            for s in room.students.filter(status='ACTIVE')]})

    @action(detail=False, methods=['post'])
    def mark(self, request):
        if request.user.is_central:
            raise PermissionDenied('Registers are taken by school staff.')
        room = self._room(request, request.data.get('classroom'))
        day = request.data.get('date')
        try:
            date_cls.fromisoformat(day)
        except (TypeError, ValueError):
            raise ValidationError({'date': 'Give the date as YYYY-MM-DD.'})
        ids = set(room.students.filter(status='ACTIVE').values_list('id', flat=True))
        with transaction.atomic():
            for row in request.data.get('records', []):
                if row.get('student') not in ids or row.get('status') not in ('P', 'A', 'L'):
                    raise ValidationError('Each record needs a student of this class and status P, A or L.')
                Attendance.objects.update_or_create(student_id=row['student'], date=day,
                                                    defaults={'status': row['status'], 'recorded_by': request.user})
            audit.log(request.user, 'attendance.taken', room, day, branch=room.branch)
        return Response({'ok': True})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_report(request, pk):
    """Report card: marks by term and subject, plus attendance. Parents only reach their own children."""
    student = students_for(request.user).filter(pk=pk).first()
    if not student:
        raise NotFound('No such student.')
    if request.user.role in (Role.STOREKEEPER, Role.LIBRARIAN):
        raise PermissionDenied('Not allowed.')
    marks = Mark.objects.filter(student=student).select_related('assessment__subject', 'assessment__term')
    terms = {}
    for m in marks:
        a = m.assessment
        t = terms.setdefault(a.term_id, {'term': a.term.name, 'start': a.term.start_date, 'subjects': {}})
        subj = t['subjects'].setdefault(a.subject.name, {'subject': a.subject.name, 'results': []})
        subj['results'].append({'assessment': a.name, 'score': m.score, 'max': a.max_score,
                                'percent': round(float(m.score) * 100 / a.max_score, 1), 'date': a.date})
    out = []
    for t in sorted(terms.values(), key=lambda t: t['start'], reverse=True):
        subs = []
        for s in t['subjects'].values():
            s['average'] = round(sum(r['percent'] for r in s['results']) / len(s['results']), 1)
            subs.append(s)
        out.append({'term': t['term'], 'subjects': subs,
                    'overall': round(sum(s['average'] for s in subs) / len(subs), 1) if subs else None})
    counts = dict(Attendance.objects.filter(student=student).values_list('status').annotate(n=Count('id')))
    total = sum(counts.values())
    return Response({
        'student': {'id': student.id, 'full_name': student.full_name, 'admission_no': student.admission_no,
                    'class_name': student.classroom.name if student.classroom else None, 'branch': student.branch.name},
        'terms': out,
        'attendance': {'present': counts.get('P', 0), 'late': counts.get('L', 0), 'absent': counts.get('A', 0),
                       'days': total, 'percent': round((counts.get('P', 0) + counts.get('L', 0)) * 100 / total, 1) if total else None},
    })
