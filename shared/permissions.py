from rest_framework.permissions import BasePermission


class IsTenantMember(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and hasattr(request, 'tenant')
            and request.tenant is not None
        )


class IsTenantAdmin(IsTenantMember):
    def has_permission(self, request, view):
        return (
            super().has_permission(request, view)
            and getattr(request.user, 'role', None) == 'admin'
        )


class IsHDManager(IsTenantMember):
    def has_permission(self, request, view):
        return (
            super().has_permission(request, view)
            and getattr(request.user, 'role', None) in ('admin', 'hd_manager')
        )


class IsAgent(IsTenantMember):
    def has_permission(self, request, view):
        return (
            super().has_permission(request, view)
            and getattr(request.user, 'role', None) in ('admin', 'hd_manager', 'agent')
        )
