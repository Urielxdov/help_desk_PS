from rest_framework.permissions import BasePermission


class IsAreaAdmin(BasePermission):
    """
    area_admin o superior. Usado para crear y modificar ServiceCategory y Service.
    El area_admin gestiona el catálogo de su área; super_admin puede hacerlo en todas.
    """

    def has_permission(self, request, view):
        return getattr(request.user, 'role', None) in ('area_admin', 'super_admin')


class IsSuperAdmin(BasePermission):
    """
    Solo super_admin. Usado para operaciones estructurales como crear o modificar
    departamentos, que afectan a toda la organización y su catálogo de servicios.
    """

    def has_permission(self, request, view):
        return getattr(request.user, 'role', None) == 'super_admin'
