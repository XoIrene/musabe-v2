from django.conf import settings
from django.db import models

from core.models import Branch
from students.models import ClassRoom, Student


class Subject(models.Model):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='subjects')
    name = models.CharField(max_length=80)

    class Meta:
        ordering = ['name']
        unique_together = [('branch', 'name')]

    def __str__(self):
        return self.name


class Term(models.Model):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='terms')
    name = models.CharField(max_length=60)          # e.g. "Term 1 2027"
    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
        ordering = ['-start_date']
        unique_together = [('branch', 'name')]

    def __str__(self):
        return f'{self.name} ({self.branch.code})'


class Assessment(models.Model):
    """A test or exam for one subject in one class."""
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='assessments')
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name='assessments')
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name='assessments')
    classroom = models.ForeignKey(ClassRoom, on_delete=models.PROTECT, related_name='assessments')
    name = models.CharField(max_length=80)           # "Midterm", "Terminal exam"
    max_score = models.PositiveIntegerField(default=100)
    date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')

    class Meta:
        ordering = ['-date', '-id']


class Mark(models.Model):
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name='marks')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='marks')
    score = models.DecimalField(max_digits=6, decimal_places=2)
    entered_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='+')

    class Meta:
        unique_together = [('assessment', 'student')]


class Attendance(models.Model):
    class Status(models.TextChoices):
        PRESENT = 'P', 'Present'
        ABSENT = 'A', 'Absent'
        LATE = 'L', 'Late'

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendance')
    date = models.DateField()
    status = models.CharField(max_length=1, choices=Status.choices)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='+')

    class Meta:
        unique_together = [('student', 'date')]
        ordering = ['-date']
