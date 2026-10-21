from django.db import models

from core.models import Branch
from students.models import Student


class Route(models.Model):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='routes')
    name = models.CharField(max_length=80)
    vehicle = models.CharField(max_length=40, blank=True)         # plate number
    driver_name = models.CharField(max_length=100, blank=True)
    driver_phone = models.CharField(max_length=30, blank=True)
    capacity = models.PositiveIntegerField(default=30)
    stops = models.TextField(blank=True)                          # one stop per line

    class Meta:
        ordering = ['branch', 'name']
        unique_together = [('branch', 'name')]


class TransportAssignment(models.Model):
    """A student rides at most one route."""
    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name='transport')
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='assignments')
    pickup_point = models.CharField(max_length=100, blank=True)
