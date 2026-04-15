"""
Vistas del catálogo de servicios. Gestiona la jerarquía Department → ServiceCategory → Service.

Los endpoints de lectura están abiertos a cualquier usuario autenticado para que
puedan navegar el catálogo al crear un ticket. Los de escritura están restringidos
porque los cambios en el catálogo afectan a toda la operación.

ServiceCategory y Service se inactivan en lugar de eliminarse (soft-delete vía
el flag 'activo') para preservar la integridad referencial con tickets históricos.
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
    Gestión de departamentos. Solo super_admin puede crear o modificar.

    Los departamentos reflejan la estructura organizacional de la empresa.
    Un cambio incorrecto afecta todo el catálogo de servicios, por eso la
    escritura requiere el rol más alto. DELETE está excluido de http_method_names
    porque los departamentos con servicios históricos no pueden eliminarse (PROTECT).
    """
    queryset = Department.objects.filter(activo=True)
    serializer_class = DepartmentSerializer
    http_method_names = ['get', 'post', 'put', 'patch', 'head', 'options']

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsSuperAdmin()]
        return [IsAuthenticated()]

    @action(detail=True, methods=['get'], url_path='categories', permission_classes=[IsAuthenticated])
    def categories(self, request, pk=None):
        department = self.get_object()
        qs = ServiceCategory.objects.select_related('department').filter(department=department, activo=True)
        serializer = ServiceCategorySerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='services', permission_classes=[IsAuthenticated])
    def services(self, request, pk=None):
        department = self.get_object()
        qs = Service.objects.select_related('category').filter(
            category__department=department, activo=True
        )
        serializer = ServiceSerializer(qs, many=True)
        return Response(serializer.data)


class ServiceCategoryViewSet(
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = ServiceCategory.objects.filter(activo=True)
    serializer_class = ServiceCategorySerializer
    permission_classes = [IsAreaAdmin]

    @action(detail=True, methods=['get'], url_path='services', permission_classes=[IsAuthenticated])
    def services(self, request, pk=None):
        category = self.get_object()
        qs = Service.objects.select_related('category').filter(category=category, activo=True)
        serializer = ServiceSerializer(qs, many=True)
        return Response(serializer.data)


class ServiceViewSet(
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Service.objects.filter(activo=True)
    serializer_class = ServiceSerializer
    permission_classes = [IsAreaAdmin]

    @action(detail=True, methods=['patch'], url_path='toggle')
    def toggle(self, request, pk=None):
        # Se invierte el flag 'activo' en lugar de eliminar el registro para
        # preservar la referencia histórica en tickets existentes. Un DELETE
        # fallaría por la FK con PROTECT en HelpDesk.service.
        # Se usa get_object_or_404 sin filtro de activo para poder reactivar
        # servicios que fueron previamente desactivados.
        service = get_object_or_404(Service, pk=pk)
        service.activo = not service.activo
        service.save(update_fields=['activo'])
        return Response(ServiceSerializer(service).data)
