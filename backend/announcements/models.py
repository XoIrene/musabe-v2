from django.conf import settings
from django.db import models

from core.models import Branch


class Announcement(models.Model):
    class Audience(models.TextChoices):
        ALL = 'ALL', 'Everyone'
        STAFF = 'STAFF', 'Staff only'
        PARENTS = 'PARENTS', 'Parents only'

    title = models.CharField(max_length=150)
    body = models.TextField()
    audience = models.CharField(max_length=8, choices=Audience.choices, default=Audience.ALL)
    # Blank branch = a notice for every school, from Central Administration.
    branch = models.ForeignKey(Branch, null=True, blank=True, on_delete=models.CASCADE, related_name='announcements')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']
