from decimal import Decimal, InvalidOperation

from django.db import transaction
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from core import audit
from core.models import Role
from core.permissions import has_role
from students.models import Student
from students.views import assert_branch, students_for
from .models import Fee, Invoice, Payment
from .serializers import FeeSerializer, InvoiceSerializer

# Fees are set centrally; the Bursar collects. Head Masters can see their own school's picture.
FINANCE = (Role.ADMIN, Role.BURSAR)


class FeeViewSet(viewsets.ModelViewSet):
    serializer_class = FeeSerializer
    permission_classes = [has_role(*FINANCE, read=(Role.MANAGER, Role.HEAD_MASTER))]
    http_method_names = ['get', 'post', 'put', 'patch', 'head', 'options']

    def get_queryset(self):
        qs = Fee.objects.select_related('branch', 'classroom')
        u = self.request.user
        return qs if u.is_central else qs.filter(branch__in=u.branch_ids())

    def perform_create(self, serializer):
        fee = serializer.save()
        audit.log(self.request.user, 'fee.created', fee, f'{fee.name} {fee.amount}')

    @action(detail=True, methods=['post'])
    def generate(self, request, pk=None):
        """Invoice every active student the fee applies to (safe to repeat: nobody is billed twice)."""
        fee = self.get_object()
        students = Student.objects.filter(branch=fee.branch, status='ACTIVE')
        if fee.classroom_id:
            students = students.filter(classroom=fee.classroom)
        have = set(fee.invoices.values_list('student_id', flat=True))
        new = [Invoice(student=s, fee=fee, amount=fee.amount) for s in students if s.pk not in have]
        Invoice.objects.bulk_create(new)
        audit.log(request.user, 'fee.invoiced', fee, f'{len(new)} new invoices')
        return Response({'created': len(new)})


class InvoiceViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = InvoiceSerializer
    permission_classes = [has_role(Role.BURSAR, read=(Role.ADMIN, Role.MANAGER, Role.HEAD_MASTER, Role.PARENT))]

    def get_queryset(self):
        qs = Invoice.objects.select_related('student__branch', 'fee').prefetch_related('payments__received_by')
        qs = qs.filter(student__in=students_for(self.request.user).values('pk'))
        p = self.request.query_params
        for key in ('student', 'fee'):
            if p.get(key):
                qs = qs.filter(**{key: p[key]})
        if p.get('branch'):
            qs = qs.filter(student__branch=p['branch'])
        if p.get('unpaid') == '1':
            qs = qs.filter(id__in=[i.id for i in qs if i.balance > 0])
        return qs

    @action(detail=True, methods=['post'])
    def pay(self, request, pk=None):
        """Only the Bursar records payments."""
        if request.user.role != Role.BURSAR:
            raise PermissionDenied('Only the Bursar records payments.')
        with transaction.atomic():
            inv = Invoice.objects.select_for_update().filter(pk=pk).first()
            if not inv:
                raise ValidationError('No such invoice.')
            try:
                amount = Decimal(str(request.data.get('amount')))
            except InvalidOperation:
                raise ValidationError({'amount': 'Enter the amount paid.'})
            if amount <= 0 or amount > inv.balance:
                raise ValidationError({'amount': f'Between 1 and the balance of {inv.balance}.'})
            method = request.data.get('method')
            if method not in ('CASH', 'BANK', 'MOBILE'):
                raise ValidationError({'method': 'Choose CASH, BANK or MOBILE.'})
            pay = Payment.objects.create(invoice=inv, amount=amount, method=method,
                                         reference=request.data.get('reference', ''), received_by=request.user)
            audit.log(request.user, 'fee.payment', pay, f'{pay.receipt_no} {amount} for {inv.student.full_name}',
                      branch=inv.student.branch)
        return Response(self.get_serializer(Invoice.objects.get(pk=pk)).data)
