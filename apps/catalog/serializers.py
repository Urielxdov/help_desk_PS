from rest_framework import serializers
from .models import Department, ServiceCategory, Service


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'nombre', 'descripcion', 'activo', 'created_at']
        read_only_fields = ['id', 'created_at']


class ServiceCategorySerializer(serializers.ModelSerializer):
    department_nombre = serializers.CharField(source='department.nombre', read_only=True)

    class Meta:
        model = ServiceCategory
        fields = ['id', 'nombre', 'department', 'department_nombre', 'activo']
        read_only_fields = ['id', 'department_nombre']


class ServiceSerializer(serializers.ModelSerializer):
    category_nombre = serializers.CharField(source='category.nombre', read_only=True)

    class Meta:
        model = Service
        fields = [
            'id', 'nombre', 'descripcion', 'category', 'category_nombre',
            'tiempo_estimado_default', 'activo', 'created_at',
        ]
        read_only_fields = ['id', 'category_nombre', 'created_at']
