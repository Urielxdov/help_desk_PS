"""
Permisos del módulo de Help Desk.

Jerarquía de roles (de menor a mayor acceso):
    user < technician < area_admin < super_admin

Los permisos son inclusivos hacia arriba: IsAreaAdmin (en catalog.permissions)
permite area_admin y super_admin; IsTechnicianOrAdmin permite technician,
area_admin y super_admin.
"""
from rest_framework.permissions import BasePermission


class IsTechnicianOrAdmin(BasePermission):
    """Técnicos y roles administrativos. Usado para acciones sobre el ciclo de vida del ticket."""

    def has_permission(self, request, view):
        return getattr(request.user, 'role', None) in ('technician', 'area_admin', 'super_admin')
