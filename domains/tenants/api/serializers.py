from rest_framework import serializers


class TenantCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    slug = serializers.SlugField(max_length=100)


class TenantResponseSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    slug = serializers.CharField()
    is_active = serializers.BooleanField()


class TenantConfigResponseSerializer(serializers.Serializer):
    sla_hours_low = serializers.IntegerField()
    sla_hours_medium = serializers.IntegerField()
    sla_hours_high = serializers.IntegerField()
    classification_threshold = serializers.FloatField()
    max_tickets_per_agent = serializers.IntegerField()
