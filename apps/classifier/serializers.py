from rest_framework import serializers

from .models import ClassificationFeedback, ServiceKeyword, UserFeedbackProfile
from .services import normalize


class ServiceKeywordSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source='service.name', read_only=True)

    class Meta:
        model = ServiceKeyword
        fields = ['id', 'service', 'service_name', 'keyword', 'weight', 'created_at']
        read_only_fields = ['id', 'created_at', 'service_name']

    def validate_keyword(self, value):
        return normalize(value)


class ClassifySerializer(serializers.Serializer):
    text = serializers.CharField(min_length=3)


class ClassificationFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClassificationFeedback
        fields = [
            'id', 'problem_description',
            'suggested_service', 'chosen_service',
            'accepted', 'rate_limited', 'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'rate_limited']

    def validate(self, attrs):
        suggested = attrs.get('suggested_service')
        chosen = attrs.get('chosen_service')
        accepted = attrs.get('accepted')

        if suggested is None and accepted:
            raise serializers.ValidationError(
                {'accepted': 'No puede ser True si no hubo sugerencia.'}
            )
        if suggested and chosen == suggested and not accepted:
            raise serializers.ValidationError(
                {'accepted': 'Si chosen_service es igual a suggested_service, accepted debe ser True.'}
            )
        return attrs


class UserFeedbackProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserFeedbackProfile
        fields = [
            'id', 'user_id', 'trust_score', 'flagged',
            'feedback_count', 'rate_limited_count', 'updated_at',
        ]
        read_only_fields = ['id', 'user_id', 'feedback_count', 'rate_limited_count', 'updated_at']

    def validate_trust_score(self, value):
        if not 0.0 <= value <= 1.0:
            raise serializers.ValidationError('Debe estar entre 0.0 y 1.0.')
        return round(value, 4)
