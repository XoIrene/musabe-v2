from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from core import audit
from core.models import Branch, Role
from core.permissions import BranchScopedMixin, has_role
from procurement.models import Request
from students.models import Student
from procurement import workflow as wf
from .models import BookCopy, Category, Issue, Item, Movement, ParentContribution, WriteOff
from .serializers import (ContributionSerializer, CopySerializer, IssueSerializer, ItemSerializer,
                          MovementSerializer, WriteOffSerializer)

LIBRARIAN = has_role(Role.LIBRARIAN)
VIEWERS = has_role(Role.ADMIN, Role.MANAGER, Role.BURSAR, Role.STOREKEEPER, Role.HEAD_MASTER,
                   Role.ACADEMIC_MASTER, Role.LIBRARIAN)


class ItemViewSet(BranchScopedMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Item.objects.select_related('branch')
    serializer_class = ItemSerializer
    permission_classes = [VIEWERS]

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if p.get('branch'):
            qs = qs.filter(branch=p['branch'])
        if p.get('category'):
            qs = qs.filter(category=p['category'])
        if p.get('q'):
            qs = qs.filter(Q(name__icontains=p['q']) | Q(author__icontains=p['q']))
        return qs


class CopyViewSet(BranchScopedMixin, viewsets.ReadOnlyModelViewSet):
    queryset = BookCopy.objects.select_related('item')
    serializer_class = CopySerializer
    permission_classes = [VIEWERS]

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        for key in ('item', 'status', 'branch'):
            if p.get(key):
                qs = qs.filter(**{key: p[key]})
        if p.get('code'):
            qs = qs.filter(code__iexact=p['code'])
        return qs


class IssueViewSet(BranchScopedMixin, mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    """Only the Librarian issues items and takes returns."""
    queryset = Issue.objects.select_related('item', 'copy', 'issued_by')
    serializer_class = IssueSerializer
    permission_classes = [has_role(Role.LIBRARIAN, Role.HEAD_MASTER, Role.ACADEMIC_MASTER, Role.ADMIN, Role.MANAGER)]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get('open') == '1':
            qs = qs.filter(returned_at__isnull=True)
        return qs

    def create(self, request):
        if request.user.role != Role.LIBRARIAN:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Only the Librarian issues items.')
        d = request.data
        student = None
        if d.get('student'):  # Version 1.1: a registered student, so the loan shows on their record
            student = Student.objects.filter(pk=d['student'], status=Student.Status.ACTIVE).first()
            if not student:
                raise ValidationError({'student': 'No active student with that id.'})
            self.assert_branch(student.branch_id)
            borrower, borrower_type = student.full_name, 'STUDENT'
        else:
            borrower, borrower_type = (d.get('borrower_name') or '').strip(), d.get('borrower_type', 'STUDENT')
        if not borrower:
            raise ValidationError({'borrower_name': 'Who is borrowing?'})
        with transaction.atomic():
            if d.get('code'):  # a book copy, traced by its unique code
                copy = BookCopy.objects.select_for_update().filter(code__iexact=d['code']).first()
                if not copy:
                    raise ValidationError({'code': 'No book with that code.'})
                self.assert_branch(copy.branch_id)
                if student and student.branch_id != copy.branch_id:
                    raise ValidationError({'student': 'This student belongs to a different school.'})
                if copy.status != BookCopy.Status.AVAILABLE:
                    raise ValidationError({'code': f'This copy is {copy.get_status_display().lower()}.'})
                copy.status = BookCopy.Status.ISSUED
                copy.save(update_fields=['status'])
                issue = Issue.objects.create(branch=copy.branch, item=copy.item, copy=copy, quantity=1,
                                             borrower_name=borrower, borrower_type=borrower_type, student=student,
                                             due_date=d.get('due_date') or None, issued_by=request.user)
                Movement.objects.create(branch=copy.branch, item=copy.item, copy=copy, type=Movement.Type.OUT_ISSUE,
                                        quantity=-1, reference=f'ISS-{issue.pk}', actor=request.user)
            else:  # stationery, uniforms: by quantity / size
                item = Item.objects.select_for_update().filter(pk=d.get('item')).first()
                if not item or item.category == Category.BOOK:
                    raise ValidationError({'item': 'Choose a stock item (books are issued by code).'})
                self.assert_branch(item.branch_id)
                if student and student.branch_id != item.branch_id:
                    raise ValidationError({'student': 'This student belongs to a different school.'})
                qty = int(d.get('quantity') or 0)
                if qty < 1 or qty > item.quantity:
                    raise ValidationError({'quantity': f'Only {item.quantity} in stock.'})
                item.quantity -= qty
                item.save(update_fields=['quantity'])
                issue = Issue.objects.create(branch=item.branch, item=item, quantity=qty, borrower_name=borrower,
                                             borrower_type=borrower_type, student=student, issued_by=request.user,
                                             returned_at=timezone.now())  # consumed items are not "returned"
                Movement.objects.create(branch=item.branch, item=item, type=Movement.Type.OUT_ISSUE, quantity=-qty,
                                        reference=f'ISS-{issue.pk}', actor=request.user)
            audit.log(request.user, 'item.issued', issue, f'{issue.item.name} x{issue.quantity} -> {borrower}')
        return Response(self.get_serializer(issue).data, status=201)

    @action(detail=True, methods=['post'], url_path='return')
    def return_book(self, request, pk=None):
        if request.user.role != Role.LIBRARIAN:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Only the Librarian takes returns.')
        issue = self.get_object()
        if issue.returned_at or not issue.copy_id:
            raise ValidationError('Nothing to return.')
        with transaction.atomic():
            issue.returned_at = timezone.now()
            issue.save(update_fields=['returned_at'])
            issue.copy.status = BookCopy.Status.AVAILABLE
            issue.copy.save(update_fields=['status'])
            Movement.objects.create(branch=issue.branch, item=issue.item, copy=issue.copy, type=Movement.Type.IN_RETURN,
                                    quantity=1, reference=f'ISS-{issue.pk}', actor=request.user)
            audit.log(request.user, 'item.returned', issue, issue.copy.code)
        return Response(self.get_serializer(issue).data)


class WriteOffViewSet(BranchScopedMixin, mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    """Librarian reports a lost/damaged book; the Head Master gives the final decision."""
    queryset = WriteOff.objects.select_related('copy__item', 'reported_by', 'decided_by')
    serializer_class = WriteOffSerializer
    permission_classes = [has_role(Role.LIBRARIAN, Role.HEAD_MASTER, Role.ADMIN, Role.MANAGER)]

    def create(self, request):
        if request.user.role != Role.LIBRARIAN:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Only the Librarian starts a write-off report.')
        d = request.data
        copy = BookCopy.objects.filter(code__iexact=d.get('code', '')).first()
        if not copy:
            raise ValidationError({'code': 'No book with that code.'})
        self.assert_branch(copy.branch_id)
        kind = d.get('kind')
        if kind not in ('LOST', 'DAMAGED') or not (d.get('reason') or '').strip():
            raise ValidationError('Choose LOST or DAMAGED and give a reason.')
        with transaction.atomic():
            copy = BookCopy.objects.select_for_update().get(pk=copy.pk)
            if copy.status in (BookCopy.Status.LOST, BookCopy.Status.DAMAGED, BookCopy.Status.WRITTEN_OFF):
                raise ValidationError({'code': 'This copy already has a write-off report.'})
            w = WriteOff.objects.create(branch=copy.branch, copy=copy, kind=kind, reason=d['reason'],
                                        previous_status=copy.status, reported_by=request.user)
            copy.status = kind
            copy.save(update_fields=['status'])
            audit.log(request.user, 'writeoff.reported', w, f'{copy.code} {kind}: {d["reason"]}')
        return Response(self.get_serializer(w).data, status=201)

    @action(detail=True, methods=['post'])
    def decide(self, request, pk=None):
        if request.user.role != Role.HEAD_MASTER:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Only the Head Master decides write-offs.')
        w = self.get_object()
        if w.status != WriteOff.Status.PENDING:
            raise ValidationError('Already decided.')
        approve = bool(request.data.get('approve'))
        with transaction.atomic():
            w.status = WriteOff.Status.APPROVED if approve else WriteOff.Status.REJECTED
            w.decided_by, w.decided_at = request.user, timezone.now()
            w.decision_note = request.data.get('note', '')
            w.save()
            copy = w.copy
            if approve:
                copy.status = BookCopy.Status.WRITTEN_OFF
                # a lost book that was out on loan closes that loan
                Issue.objects.filter(copy=copy, returned_at__isnull=True).update(returned_at=timezone.now(), note='written off')
                Movement.objects.create(branch=w.branch, item=copy.item, copy=copy, type=Movement.Type.OUT_WRITEOFF,
                                        quantity=-1, reference=f'WO-{w.pk}', actor=request.user)
            else:
                copy.status = w.previous_status
            copy.save(update_fields=['status'])
            audit.log(request.user, 'writeoff.approved' if approve else 'writeoff.rejected', w, w.decision_note)
        return Response(self.get_serializer(w).data)


class ContributionViewSet(BranchScopedMixin, mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = ParentContribution.objects.select_related('item')
    serializer_class = ContributionSerializer
    permission_classes = [has_role(Role.LIBRARIAN, Role.HEAD_MASTER, Role.ADMIN, Role.MANAGER)]

    def create(self, request):
        if request.user.role != Role.LIBRARIAN:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Only the Librarian records parent contributions.')
        d = request.data
        branch = Branch.objects.filter(pk=d.get('branch')).first()
        if not branch or branch.type != Branch.Type.PRIMARY:
            raise ValidationError({'branch': 'Parent contributions are recorded for Primary schools only.'})
        self.assert_branch(branch.pk)
        name, qty = (d.get('name') or '').strip(), int(d.get('quantity') or 0)
        if not name or qty < 1:
            raise ValidationError('Give an item name and a quantity.')
        with transaction.atomic():
            item, _ = Item.objects.get_or_create(branch=branch, name=name, category=Category.PRIMARY, size='')
            item.quantity += qty
            item.save(update_fields=['quantity'])
            c = ParentContribution.objects.create(branch=branch, item=item, quantity=qty,
                                                  parent_name=d.get('parent_name', ''), recorded_by=request.user)
            Movement.objects.create(branch=branch, item=item, type=Movement.Type.IN_PARENT, quantity=qty,
                                    reference=f'PC-{c.pk}', actor=request.user)
            audit.log(request.user, 'contribution.recorded', c, f'{name} x{qty}')
        return Response(self.get_serializer(c).data, status=201)


class MovementViewSet(BranchScopedMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Movement.objects.select_related('item', 'copy', 'actor')
    serializer_class = MovementSerializer
    permission_classes = [VIEWERS]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get('item'):
            qs = qs.filter(item=self.request.query_params['item'])
        return qs[:300]


@api_view(['GET'])
def summary(request):
    """Core report: live stock by branch, pending requests by who they wait on, open loans, low stock."""
    u = request.user
    branches = Branch.objects.all() if u.is_central else Branch.objects.filter(pk__in=u.branch_ids())
    out = []
    for b in branches:
        books = BookCopy.objects.filter(branch=b)
        out.append({
            'branch': b.name, 'type': b.type,
            'book_titles': Item.objects.filter(branch=b, category=Category.BOOK).count(),
            'copies_available': books.filter(status='AVAILABLE').count(),
            'copies_issued': books.filter(status='ISSUED').count(),
            'copies_lost_or_damaged': books.filter(status__in=['LOST', 'DAMAGED']).count(),
            'copies_written_off': books.filter(status='WRITTEN_OFF').count(),
            'other_items_in_stock': sum(Item.objects.filter(branch=b).exclude(category=Category.BOOK).values_list('quantity', flat=True)),
            'low_stock': [i.name for i in Item.objects.filter(branch=b).exclude(category=Category.BOOK)
                          if i.quantity <= i.reorder_level],
            'pending_writeoffs': WriteOff.objects.filter(branch=b, status='PENDING').count(),
        })
    reqs = Request.objects.filter(branch__in=branches).exclude(status__in=[wf.S.COMPLETED, wf.S.REJECTED])
    pending = {}
    for status, n in reqs.values_list('status').annotate(n=Count('id')):
        pending[wf.WAITING_ON.get(status, status)] = pending.get(wf.WAITING_ON.get(status, status), 0) + n
    return Response({'branches': out, 'pending_requests_by_waiting_on': pending,
                     'open_loans': Issue.objects.filter(branch__in=branches, returned_at__isnull=True).count()})
