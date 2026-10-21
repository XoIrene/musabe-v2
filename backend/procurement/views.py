from django.db.models import Q
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.models import Role
from . import services
from . import workflow as wf
from .models import Request
from .serializers import RequestSerializer


class RequestViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = RequestSerializer

    def get_queryset(self):
        qs = Request.objects.select_related('branch', 'requestor').prefetch_related('lines', 'steps__actor')
        u = self.request.user
        if u.is_central:
            # Central roles see what has reached Central Administration (plus everything for Admin/Manager).
            if u.role in (Role.ADMIN, Role.MANAGER):
                pass
            else:
                qs = qs.exclude(status__in=[wf.S.PENDING_ACADEMIC, wf.S.PENDING_HEAD, wf.S.PENDING_APPROVAL,
                                            wf.S.PENDING_REQUISITION, wf.S.PENDING_LIBRARIAN])
        elif u.role in (Role.HEAD_MASTER, Role.ACADEMIC_MASTER, Role.LIBRARIAN):
            qs = qs.filter(branch__in=u.branch_ids())
        else:  # requesting staff see only their own requests
            qs = qs.filter(requestor=u)
        p = self.request.query_params
        if p.get('status'):
            qs = qs.filter(status=p['status'])
        if p.get('kind'):
            qs = qs.filter(kind=p['kind'])
        if p.get('mine') == '1':
            qs = qs.filter(requestor=u)
        if p.get('todo') == '1':  # requests waiting on this user
            ids = [r.id for r in qs if wf.available_actions(u, r)]
            qs = qs.filter(id__in=ids)
        return qs

    def perform_create(self, serializer):
        d = serializer.validated_data
        lines = [dict(l) for l in d['lines']]
        serializer.instance = services.create_request(
            self.request.user, d['branch'], d['kind'], d['title'], d.get('justification', ''), lines)

    @action(detail=True, methods=['post'])
    def act(self, request, pk=None):
        req = self.get_object()
        d = request.data
        req = services.perform(request.user, req, d.get('action', ''), d.get('note', ''), d.get('supplier', ''))
        return Response(self.get_serializer(self.get_queryset().get(pk=req.pk)).data)
