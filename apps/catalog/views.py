from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Department, ServiceCategory, Service
from .serializers import DepartmentSerializer, ServiceCategorySerializer, ServiceSerializer
from .permissions import IsAreaAdmin, IsSuperAdmin


class DepartmentViewSet(viewsets.ModelViewSet):
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
        qs = ServiceCategory.objects.filter(department=department, activo=True)
        serializer = ServiceCategorySerializer(qs, many=True)
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
        qs = Service.objects.filter(category=category, activo=True)
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
        service = self.get_object()
        service.activo = not service.activo
        service.save(update_fields=['activo'])
        return Response(ServiceSerializer(service).data)
