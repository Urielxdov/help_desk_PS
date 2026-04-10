from rest_framework import serializers

ROLE_CHOICES = ['admin', 'hd_manager', 'agent']


class UserCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    full_name = serializers.CharField(max_length=200)
    role = serializers.ChoiceField(choices=ROLE_CHOICES)
    password = serializers.CharField(write_only=True, min_length=8)


class UserUpdateSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=200, required=False)
    role = serializers.ChoiceField(choices=ROLE_CHOICES, required=False)


class UserResponseSerializer(serializers.Serializer):
    id = serializers.CharField()
    email = serializers.CharField()
    full_name = serializers.CharField()
    role = serializers.CharField()
    is_active = serializers.BooleanField()
