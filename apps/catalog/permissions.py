from rest_framework.permissions import BasePermission


class IsAreaAdmin(BasePermission):
    """area_admin o superior."""

    def has_permission(self, request, view):
        return getattr(request.user, 'role', None) in ('area_admin', 'super_admin')


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return getattr(request.user, 'role', None) == 'super_admin'
