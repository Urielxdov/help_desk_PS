from rest_framework.permissions import BasePermission


class IsTechnicianOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return getattr(request.user, 'role', None) in ('technician', 'area_admin', 'super_admin')


class IsAreaAdmin(BasePermission):
    def has_permission(self, request, view):
        return getattr(request.user, 'role', None) in ('area_admin', 'super_admin')


class IsOwnerOrAdmin(BasePermission):
    """El solicitante del HD o un rol administrativo."""

    def has_object_permission(self, request, view, obj):
        role = getattr(request.user, 'role', None)
        if role in ('area_admin', 'super_admin', 'technician'):
            return True
        return obj.solicitante_id == getattr(request.user, 'user_id', None)
