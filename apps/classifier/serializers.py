from rest_framework import serializers

from .models import ClassificationFeedback, ServiceKeyword


class ServiceKeywordSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source='service.name', read_only=True)

    class Meta:
        model = ServiceKeyword
        fields = ['id', 'service', 'service_name', 'keyword', 'weight', 'created_at']
        read_only_fields = ['id', 'created_at', 'service_name']


class ClassifySerializer(serializers.Serializer):
    text = serializers.CharField(min_length=3)


class ClassificationFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClassificationFeedback
        fields = [
            'id', 'problem_description',
            'suggested_service', 'chosen_service',
            'accepted', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']

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
