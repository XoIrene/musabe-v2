from rest_framework.permissions import BasePermission, SAFE_METHODS


class NotParent(BasePermission):
    """Default for every endpoint: parents only reach the views that opt in to them."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role != 'PARENT'


def has_role(*roles, read_any=False, read=()):
    """Permission factory: user's role must be one of `roles`.
    With read_any=True every authenticated user may read (GET/HEAD/OPTIONS);
    `read` names extra roles that may read but not write."""
    allowed = {str(r) for r in roles}
    readers = allowed | {str(r) for r in read}

    class _HasRole(BasePermission):
        def has_permission(self, request, view):
            if not request.user.is_authenticated:
                return False
            if read_any and request.method in SAFE_METHODS:
                return True
            if request.method in SAFE_METHODS:
                return request.user.role in readers
            return request.user.role in allowed

    return _HasRole


class BranchScopedMixin:
    """Central users see every branch; school users see only their own branches."""
    branch_field = 'branch'

    def scope(self, qs):
        user = self.request.user
        if user.is_central:
            return qs
        return qs.filter(**{f'{self.branch_field}__in': user.branch_ids()})

    def get_queryset(self):
        return self.scope(super().get_queryset())

    def assert_branch(self, branch_id):
        """School users may only act inside their own branches."""
        from rest_framework.exceptions import PermissionDenied
        user = self.request.user
        if not user.is_central and int(branch_id) not in user.branch_ids():
            raise PermissionDenied('You do not belong to that branch.')
