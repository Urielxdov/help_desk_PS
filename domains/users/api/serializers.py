from rest_framework import serializers


ROLE_CHOICES = ["admin", "hd_manager", "agent", "end_user"]


class DepartmentCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    keywords = serializers.CharField(default="", allow_blank=True)
    sla_hours = serializers.IntegerField(default=24, min_value=1)


class DepartmentResponseSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    keywords = serializers.CharField()
    sla_hours = serializers.IntegerField()
    is_active = serializers.BooleanField()


class UserCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    full_name = serializers.CharField(max_length=200)
    role = serializers.ChoiceField(choices=ROLE_CHOICES)
    department_id = serializers.CharField(required=False, allow_null=True)
    password = serializers.CharField(write_only=True, min_length=8)


class UserResponseSerializer(serializers.Serializer):
    id = serializers.CharField()
    email = serializers.CharField()
    full_name = serializers.CharField()
    role = serializers.CharField()
    department_id = serializers.CharField(allow_null=True)
    is_active = serializers.BooleanField()
