from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from core import audit
from core.models import Role, User
from core.permissions import has_role
from core.serializers import UserSerializer
from inventory.models import Issue
from inventory.serializers import IssueSerializer
from .models import ClassRoom, Guardian, Student
from .serializers import ClassRoomSerializer, GuardianSerializer, StudentSerializer

# Who may register students and parents (the Admin centrally, the school's own heads inside a school).
MANAGERS = (Role.ADMIN, Role.HEAD_MASTER, Role.ACADEMIC_MASTER)
# Who may look students up. Storekeeper is left out on purpose; parents only ever see their own children.
READERS = (Role.MANAGER, Role.BURSAR, Role.LIBRARIAN, Role.STAFF, Role.PARENT)


def students_for(user):
    qs = Student.objects.select_related('branch', 'classroom')
    if user.role == Role.PARENT:
        return qs.filter(guardians__user=user)
    return qs if user.is_central else qs.filter(branch__in=user.branch_ids())


def assert_branch(user, branch_id):
    if not user.is_central and int(branch_id) not in user.branch_ids():
        raise PermissionDenied('You do not belong to that school.')


class ClassRoomViewSet(viewsets.ModelViewSet):
    serializer_class = ClassRoomSerializer
    permission_classes = [has_role(*MANAGERS, read=READERS)]

    def get_queryset(self):
        u = self.request.user
        qs = ClassRoom.objects.select_related('branch', 'class_teacher')
        if u.role == Role.PARENT:
            qs = qs.filter(students__guardians__user=u).distinct()
        elif not u.is_central:
            qs = qs.filter(branch__in=u.branch_ids())
        if self.request.query_params.get('branch'):
            qs = qs.filter(branch=self.request.query_params['branch'])
        return qs

    def perform_create(self, serializer):
        assert_branch(self.request.user, serializer.validated_data['branch'].pk)
        audit.log(self.request.user, 'class.created', serializer.save())

    def perform_update(self, serializer):
        assert_branch(self.request.user, serializer.instance.branch_id)
        serializer.save()


class StudentViewSet(viewsets.ModelViewSet):
    serializer_class = StudentSerializer
    permission_classes = [has_role(*MANAGERS, read=READERS)]
    http_method_names = ['get', 'post', 'put', 'patch', 'head', 'options']   # students are never deleted, only marked as left

    def get_queryset(self):
        qs = students_for(self.request.user).prefetch_related('guardians')
        p = self.request.query_params
        for key in ('branch', 'classroom', 'status'):
            if p.get(key):
                qs = qs.filter(**{key: p[key]})
        if p.get('q'):
            qs = qs.filter(Q(full_name__icontains=p['q']) | Q(admission_no__icontains=p['q']))
        return qs.distinct()

    def perform_create(self, serializer):
        assert_branch(self.request.user, serializer.validated_data['branch'].pk)
        s = serializer.save()
        audit.log(self.request.user, 'student.registered', s, f'{s.full_name} ({s.admission_no})')

    def perform_update(self, serializer):
        assert_branch(self.request.user, serializer.instance.branch_id)
        s = serializer.save()
        audit.log(self.request.user, 'student.updated', s, f'status={s.status}')

    @action(detail=True, methods=['get'])
    def loans(self, request, pk=None):
        """Link to the library: everything this student has borrowed or been issued."""
        student = self.get_object()
        qs = Issue.objects.filter(student=student).select_related('item', 'copy', 'issued_by')
        return Response(IssueSerializer(qs, many=True).data)


class GuardianViewSet(viewsets.ModelViewSet):
    serializer_class = GuardianSerializer
    permission_classes = [has_role(*MANAGERS, read=(Role.MANAGER, Role.BURSAR, Role.LIBRARIAN))]
    http_method_names = ['get', 'post', 'put', 'patch', 'head', 'options']

    def get_queryset(self):
        u = self.request.user
        qs = Guardian.objects.prefetch_related('students')
        if not u.is_central:
            qs = qs.filter(students__branch__in=u.branch_ids()).distinct()
        if self.request.query_params.get('student'):
            qs = qs.filter(students=self.request.query_params['student'])
        return qs

    def _check_students(self, students):
        for s in students:
            assert_branch(self.request.user, s.branch_id)

    def perform_create(self, serializer):
        self._check_students(serializer.validated_data.get('students', []))
        g = serializer.save()
        audit.log(self.request.user, 'guardian.registered', g, g.full_name, branch=None)

    def perform_update(self, serializer):
        self._check_students(serializer.validated_data.get('students', []))
        serializer.save()

    @action(detail=True, methods=['post'])
    def create_login(self, request, pk=None):
        """Give a parent a login (role Parent). Only the Admin and Head Masters do this."""
        if request.user.role not in (Role.ADMIN, Role.HEAD_MASTER):
            raise PermissionDenied('Only the Admin or a Head Master creates parent logins.')
        g = self.get_object()
        if g.user_id:
            raise ValidationError('This parent already has a login.')
        kids = list(g.students.all())
        if not kids:
            raise ValidationError('Link at least one child first.')
        email = (request.data.get('email') or g.email or '').strip()
        ser = UserSerializer(data={'full_name': g.full_name, 'email': email, 'password': request.data.get('password', ''),
                                   'role': Role.PARENT, 'branches': sorted({k.branch_id for k in kids})},
                             context={'allow_parent': True})
        ser.is_valid(raise_exception=True)
        user = ser.save()
        g.user, g.email = user, email
        g.save(update_fields=['user', 'email'])
        audit.log(request.user, 'guardian.login_created', g, email, branch=kids[0].branch)
        return Response(GuardianSerializer(g).data)
