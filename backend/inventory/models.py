from django.conf import settings
from django.db import models

from core.models import Branch


class Category(models.TextChoices):
    BOOK = 'BOOK', 'Book / textbook'
    STATIONERY = 'STATIONERY', 'Stationery'
    UNIFORM = 'UNIFORM', 'Uniform'
    FABRIC = 'FABRIC', 'Sewing material (vitambaa)'
    PRIMARY = 'PRIMARY', 'Primary School item'
    OTHER = 'OTHER', 'Other'


class Item(models.Model):
    """A stock line in one school's store. Books: one Item per title, with a BookCopy per physical copy."""
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='items')
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=12, choices=Category.choices)
    size = models.CharField(max_length=30, blank=True)          # uniforms etc.
    author = models.CharField(max_length=150, blank=True)       # books
    isbn = models.CharField(max_length=30, blank=True)          # books
    quantity = models.PositiveIntegerField(default=0)           # non-book stock on hand
    reorder_level = models.PositiveIntegerField(default=5)

    class Meta:
        ordering = ['name']
        unique_together = [('branch', 'name', 'category', 'size')]

    @property
    def on_hand(self):
        if self.category == Category.BOOK:
            return self.copies.filter(status=BookCopy.Status.AVAILABLE).count()
        return self.quantity


class BookCopy(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = 'AVAILABLE', 'Available'
        ISSUED = 'ISSUED', 'Issued'
        LOST = 'LOST', 'Lost (pending write-off)'
        DAMAGED = 'DAMAGED', 'Damaged (pending write-off)'
        WRITTEN_OFF = 'WRITTEN_OFF', 'Written off'

    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='copies')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='copies')
    code = models.CharField(max_length=40, unique=True)   # unique per copy: NPS-0012-003
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.AVAILABLE)

    class Meta:
        ordering = ['code']

    @classmethod
    def next_codes(cls, item, n):
        """Codes are BRANCH-ITEM-SEQ; the sequence never reuses a number, even after write-off."""
        last = cls.objects.filter(item=item).count()
        return [f'{item.branch.code}-{item.pk:04d}-{last + i + 1:03d}' for i in range(n)]


class Issue(models.Model):
    """One loan of a book copy, or a quantity/size of another item. Only the Librarian creates these."""
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='issues')
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name='issues')
    copy = models.ForeignKey(BookCopy, null=True, blank=True, on_delete=models.PROTECT, related_name='issues')
    quantity = models.PositiveIntegerField(default=1)
    borrower_name = models.CharField(max_length=150)
    borrower_type = models.CharField(max_length=20, default='STUDENT')  # STUDENT / TEACHER / OTHER
    student = models.ForeignKey('students.Student', null=True, blank=True, on_delete=models.PROTECT, related_name='issues')
    issued_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    issued_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['-issued_at']


class WriteOff(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Waiting for Head Master'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'

    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='writeoffs')
    copy = models.ForeignKey(BookCopy, on_delete=models.PROTECT, related_name='writeoffs')
    kind = models.CharField(max_length=10, choices=[('LOST', 'Lost'), ('DAMAGED', 'Damaged')])
    reason = models.TextField()
    previous_status = models.CharField(max_length=12)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    reported_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    reported_at = models.DateTimeField(auto_now_add=True)
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name='+')
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['-reported_at']


class ParentContribution(models.Model):
    """Primary School only: items given by parents, an extra way stock enters the store."""
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='contributions')
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name='contributions')
    quantity = models.PositiveIntegerField()
    parent_name = models.CharField(max_length=150, blank=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class Movement(models.Model):
    """Every stock movement in or out, kept forever."""
    class Type(models.TextChoices):
        IN_PURCHASE = 'IN_PURCHASE', 'Received from purchase'
        IN_PARENT = 'IN_PARENT', 'Parent contribution'
        OUT_ISSUE = 'OUT_ISSUE', 'Issued'
        IN_RETURN = 'IN_RETURN', 'Returned'
        OUT_WRITEOFF = 'OUT_WRITEOFF', 'Written off'

    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='movements')
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='movements')
    copy = models.ForeignKey(BookCopy, null=True, blank=True, on_delete=models.SET_NULL, related_name='movements')
    type = models.CharField(max_length=14, choices=Type.choices)
    quantity = models.IntegerField()
    reference = models.CharField(max_length=60, blank=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']
