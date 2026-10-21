from django.conf import settings
from django.db import models

from core.models import Branch


class ClassRoom(models.Model):
    """A class (stream) inside one school, e.g. 'Standard 4A' or 'Form 2 Blue'."""
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='classrooms')
    name = models.CharField(max_length=60)
    class_teacher = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                      related_name='+')

    class Meta:
        ordering = ['branch', 'name']
        unique_together = [('branch', 'name')]

    def __str__(self):
        return f'{self.name} ({self.branch.code})'


class Student(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        LEFT = 'LEFT', 'Left the school'
        GRADUATED = 'GRADUATED', 'Graduated'

    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='students')
    admission_no = models.CharField(max_length=30)
    full_name = models.CharField(max_length=150)
    gender = models.CharField(max_length=1, choices=[('F', 'Female'), ('M', 'Male')])
    date_of_birth = models.DateField(null=True, blank=True)
    classroom = models.ForeignKey(ClassRoom, null=True, blank=True, on_delete=models.SET_NULL, related_name='students')
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['full_name']
        unique_together = [('branch', 'admission_no')]

    def __str__(self):
        return f'{self.full_name} ({self.admission_no})'


class Guardian(models.Model):
    """Parent record. Optionally has a login (user) so the parent can follow their children."""
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    relationship = models.CharField(max_length=30, default='Parent')
    students = models.ManyToManyField(Student, blank=True, related_name='guardians')
    user = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                related_name='guardian')

    class Meta:
        ordering = ['full_name']

    def __str__(self):
        return self.full_name
