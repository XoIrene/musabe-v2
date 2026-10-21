from rest_framework import viewsets

from core import audit
from core.models import Role
from core.permissions import has_role
from students.views import assert_branch, students_for
from .models import Route, TransportAssignment
from .serializers import AssignmentSerializer, RouteSerializer

MANAGERS = (Role.ADMIN, Role.HEAD_MASTER)
READERS = (Role.MANAGER, Role.ACADEMIC_MASTER, Role.LIBRARIAN, Role.STAFF, Role.PARENT)


class RouteViewSet(viewsets.ModelViewSet):
    serializer_class = RouteSerializer
    permission_classes = [has_role(*MANAGERS, read=READERS)]

    def get_queryset(self):
        u, qs = self.request.user, Route.objects.select_related('branch')
        if u.role == Role.PARENT:
            return qs.filter(assignments__student__in=students_for(u).values('pk')).distinct()
        return qs if u.is_central else qs.filter(branch__in=u.branch_ids())

    def perform_create(self, serializer):
        assert_branch(self.request.user, serializer.validated_data['branch'].pk)
        audit.log(self.request.user, 'route.created', serializer.save())

    def perform_update(self, serializer):
        assert_branch(self.request.user, serializer.instance.branch_id)
        serializer.save()

    def perform_destroy(self, instance):
        assert_branch(self.request.user, instance.branch_id)
        instance.delete()


class AssignmentViewSet(viewsets.ModelViewSet):
    serializer_class = AssignmentSerializer
    permission_classes = [has_role(*MANAGERS, read=READERS)]
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        qs = TransportAssignment.objects.select_related('student', 'route')
        qs = qs.filter(student__in=students_for(self.request.user).values('pk'))
        p = self.request.query_params
        for key in ('route', 'student'):
            if p.get(key):
                qs = qs.filter(**{key: p[key]})
        return qs

    def perform_create(self, serializer):
        assert_branch(self.request.user, serializer.validated_data['student'].branch_id)
        a = serializer.save()
        audit.log(self.request.user, 'transport.assigned', a, f'{a.student.full_name} -> {a.route.name}', branch=a.route.branch)

    def perform_destroy(self, instance):
        audit.log(self.request.user, 'transport.removed', instance, instance.student.full_name, branch=instance.route.branch)
        instance.delete()
