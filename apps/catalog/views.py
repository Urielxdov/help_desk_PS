"""
Vistas del catálogo de servicios. Gestiona la jerarquía Department → ServiceCategory → Service.

Read endpoints are open to any authenticated user so they can browse
the catalog when creating a ticket. Write endpoints are restricted
because catalog changes affect the entire operation.

ServiceCategory and Service are deactivated instead of deleted (soft-delete via
the 'active' flag) to preserve referential integrity with historical tickets.
"""
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Department, ServiceCategory, Service
from .serializers import DepartmentSerializer, ServiceCategorySerializer, ServiceSerializer
from .permissions import IsAreaAdmin, IsSuperAdmin


class DepartmentViewSet(viewsets.ModelViewSet):
    """
    Department management. Only super_admin can create or modify.

    Departments reflect the organizational structure of the company.
    An incorrect change affects the entire service catalog, so writes
    require the highest role. DELETE is excluded from http_method_names
    because departments with historical services cannot be deleted (PROTECT).
    """
    queryset = Department.objects.filter(active=True)
    serializer_class = DepartmentSerializer
    http_method_names = ['get', 'post', 'put', 'patch', 'head', 'options']

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsSuperAdmin()]
        return [IsAuthenticated()]

    @action(detail=True, methods=['get'], url_path='categories', permission_classes=[IsAuthenticated])
    def categories(self, request, pk=None):
        department = self.get_object()
        qs = ServiceCategory.objects.select_related('department').filter(department=department, active=True)
        serializer = ServiceCategorySerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='services', permission_classes=[IsAuthenticated])
    def services(self, request, pk=None):
        department = self.get_object()
        qs = Service.objects.select_related('category').filter(
            category__department=department, active=True
        )
        serializer = ServiceSerializer(qs, many=True)
        return Response(serializer.data)


class ServiceCategoryViewSet(
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = ServiceCategory.objects.filter(active=True)
    serializer_class = ServiceCategorySerializer
    permission_classes = [IsAreaAdmin]

    @action(detail=True, methods=['get'], url_path='services', permission_classes=[IsAuthenticated])
    def services(self, request, pk=None):
        category = self.get_object()
        qs = Service.objects.select_related('category').filter(category=category, active=True)
        serializer = ServiceSerializer(qs, many=True)
        return Response(serializer.data)


class ServiceViewSet(
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Service.objects.filter(active=True)
    serializer_class = ServiceSerializer
    permission_classes = [IsAreaAdmin]

    @action(detail=True, methods=['patch'], url_path='toggle')
    def toggle(self, request, pk=None):
        # The 'active' flag is inverted instead of deleting the record to
        # preserve the historical reference in existing tickets. A DELETE
        # would fail due to the PROTECT FK in HelpDesk.service.
        # get_object_or_404 without active filter allows reactivating
        # previously deactivated services.
        service = get_object_or_404(Service, pk=pk)
        service.active = not service.active
        service.save(update_fields=['active'])
        return Response(ServiceSerializer(service).data)
