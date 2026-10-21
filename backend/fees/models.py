from django.conf import settings
from django.db import models

from core.models import Branch
from students.models import ClassRoom, Student


class Fee(models.Model):
    """A charge set for a school (optionally one class only), e.g. 'School fees Term 1'."""
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='fees')
    name = models.CharField(max_length=120)
    amount = models.DecimalField(max_digits=12, decimal_places=2)       # TZS
    classroom = models.ForeignKey(ClassRoom, null=True, blank=True, on_delete=models.CASCADE, related_name='+')
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = [('branch', 'name', 'classroom')]


class Invoice(models.Model):
    """What one student owes for one fee."""
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='invoices')
    fee = models.ForeignKey(Fee, on_delete=models.CASCADE, related_name='invoices')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']
        unique_together = [('student', 'fee')]

    @property
    def paid(self):
        return sum(p.amount for p in self.payments.all())   # uses prefetch_related('payments') when the caller set it

    @property
    def balance(self):
        return self.amount - self.paid


class Payment(models.Model):
    """Payments are never edited or deleted: a mistake is fixed by a new, audited entry."""
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=20, choices=[('CASH', 'Cash'), ('BANK', 'Bank'), ('MOBILE', 'Mobile money')])
    reference = models.CharField(max_length=60, blank=True)
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def receipt_no(self):
        return f'RCT-{self.pk:06d}'

    class Meta:
        ordering = ['-created_at', '-id']
