from rest_framework import serializers

from .models import SLAConfig, ServiceQueue, TechnicianProfile


class TechnicianProfileSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)

    class Meta:
        model = TechnicianProfile
        fields = ['id', 'user_id', 'department', 'department_name', 'active', 'created_at']
        read_only_fields = ['id', 'created_at']


class SLAConfigSerializer(serializers.ModelSerializer):
    department_name = serializers.SerializerMethodField()

    class Meta:
        model = SLAConfig
        fields = [
            'id', 'department', 'department_name', 'max_load',
            'resolution_time', 'resolution_unit',
            'score_overdue',
            'score_company', 'score_area', 'score_individual',
            'score_critical', 'score_high', 'score_medium', 'score_low',
        ]
        read_only_fields = ['id']

    def get_department_name(self, obj):
        return obj.department.name if obj.department else 'Global'


class ServiceQueueSerializer(serializers.ModelSerializer):
    folio = serializers.CharField(source='help_desk.folio', read_only=True)
    priority = serializers.CharField(source='help_desk.priority', read_only=True)
    impact = serializers.CharField(source='help_desk.impact', read_only=True)
    department = serializers.CharField(
        source='help_desk.service.category.department.name', read_only=True
    )
    due_date = serializers.DateTimeField(source='help_desk.due_date', read_only=True)

    class Meta:
        model = ServiceQueue
        fields = [
            'id', 'folio', 'priority', 'impact', 'department',
            'due_date', 'urgency_score', 'queued_at',
        ]
        read_only_fields = fields
