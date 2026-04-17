from rest_framework import serializers
from .models import Department, ServiceCategory, Service


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'name', 'description', 'active', 'created_at']
        read_only_fields = ['id', 'created_at']


class ServiceCategorySerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)

    class Meta:
        model = ServiceCategory
        fields = ['id', 'name', 'department', 'department_name', 'active']
        read_only_fields = ['id', 'department_name', 'active']

    def validate_department(self, value):
        if not value.active:
            raise serializers.ValidationError('El departamento está inactivo.')
        return value


class ServiceSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Service
        fields = [
            'id', 'name', 'description', 'category', 'category_name',
            'estimated_hours', 'client_close', 'active', 'created_at',
        ]
        read_only_fields = ['id', 'category_name', 'created_at', 'active']

    def validate_category(self, value):
        if not value.active:
            raise serializers.ValidationError('La categoría está inactiva.')
        return value
