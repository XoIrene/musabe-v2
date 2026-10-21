from django.db.models import Q
from rest_framework import mixins, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError

from core import audit
from core.models import Role
from core.permissions import has_role
from .models import Announcement
from .serializers import AnnouncementSerializer

WRITERS = (Role.ADMIN, Role.MANAGER, Role.HEAD_MASTER)


class AnnouncementViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
                          mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """Central Administration notices reach every school; a Head Master writes for their own school."""
    serializer_class = AnnouncementSerializer
    permission_classes = [has_role(*WRITERS, read_any=True)]

    def get_queryset(self):
        u, qs = self.request.user, Announcement.objects.select_related('author', 'branch')
        if u.is_central:
            return qs
        qs = qs.filter(Q(branch__isnull=True) | Q(branch__in=u.branch_ids()))
        if u.role == Role.PARENT:
            return qs.filter(audience__in=['ALL', 'PARENTS'])
        return qs.filter(audience__in=['ALL', 'STAFF'])

    def perform_create(self, serializer):
        u, branch = self.request.user, serializer.validated_data.get('branch')
        if u.role == Role.HEAD_MASTER and (not branch or branch.pk not in u.branch_ids()):
            raise ValidationError({'branch': 'A Head Master writes notices for their own school.'})
        audit.log(u, 'announcement.posted', serializer.save(author=u), serializer.validated_data['title'])

    def perform_destroy(self, instance):
        u = self.request.user
        if u.role not in (Role.ADMIN, Role.MANAGER) and instance.author_id != u.id:
            raise PermissionDenied('You can only remove your own notices.')
        instance.delete()
