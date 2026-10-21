from django.conf import settings
from django.db import models

from core.models import Branch
from inventory.models import Category


class Request(models.Model):
    class Kind(models.TextChoices):
        BOOKS = 'BOOKS', 'Books / textbooks (13 steps)'
        OTHER = 'OTHER', 'Other items (9 steps)'

    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='requests')
    kind = models.CharField(max_length=6, choices=Kind.choices)
    title = models.CharField(max_length=200)
    justification = models.TextField(blank=True)
    requestor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='requests')
    status = models.CharField(max_length=24)
    requisition_no = models.CharField(max_length=20, blank=True)
    po_number = models.CharField(max_length=20, blank=True)
    supplier = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']


class RequestLine(models.Model):
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name='lines')
    name = models.CharField(max_length=200)            # book title or item name
    category = models.CharField(max_length=12, choices=Category.choices, default=Category.BOOK)
    quantity = models.PositiveIntegerField()
    size = models.CharField(max_length=30, blank=True)
    author = models.CharField(max_length=150, blank=True)
    isbn = models.CharField(max_length=30, blank=True)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)


class Step(models.Model):
    """Timeline of a request: who did what, when, with what note."""
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name='steps')
    action = models.CharField(max_length=30)
    from_status = models.CharField(max_length=24)
    to_status = models.CharField(max_length=24)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='+')
    note = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']
