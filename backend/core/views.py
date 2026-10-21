from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from . import audit
from .models import AuditLog, Branch, Role, User
from .permissions import has_role
from .serializers import AuditSerializer, BranchSerializer, LoginSerializer, UserSerializer


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    return Response(UserSerializer(request.user).data)


class BranchViewSet(viewsets.ModelViewSet):
    """Everyone can read branches; only the Admin registers them."""
    queryset = Branch.objects.all()
    serializer_class = BranchSerializer
    permission_classes = [has_role(Role.ADMIN, read_any=True)]

    def perform_create(self, serializer):
        audit.log(self.request.user, 'branch.registered', serializer.save())


class StaffViewSet(viewsets.ModelViewSet):
    """Admin registers staff, sets their role and places them in branch(es)."""
    queryset = User.objects.exclude(role=Role.PARENT).prefetch_related('branches').order_by('full_name')
    serializer_class = UserSerializer
    permission_classes = [has_role(Role.ADMIN)]

    def perform_create(self, serializer):
        user = serializer.save()
        audit.log(self.request.user, 'staff.registered', user, f'role={user.role}')

    def perform_update(self, serializer):
        user = serializer.save()
        audit.log(self.request.user, 'staff.updated', user, f'role={user.role}')


class AuditViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related('actor', 'branch')
    serializer_class = AuditSerializer
    permission_classes = [has_role(Role.ADMIN, Role.MANAGER, Role.HEAD_MASTER)]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.role == Role.HEAD_MASTER:
            qs = qs.filter(branch__in=self.request.user.branch_ids())
        for key in ('entity', 'entity_id'):
            if self.request.query_params.get(key):
                qs = qs.filter(**{key: self.request.query_params[key]})
        return qs[:300]
