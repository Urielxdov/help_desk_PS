"""
Serializers del módulo de Help Desk.

Two separate serializers are used for HelpDesk:
- HelpDeskCreateSerializer: write-only for POST /helpdesks/. Exposes only
  the fields the requester can provide at creation time.
- HelpDeskSerializer: for reading and as response in all endpoints.
  Status, control dates and attachments are read-only because they are only
  modified through dedicated endpoints that apply business validations.
"""
from rest_framework import serializers
from .models import HelpDesk, HDAttachment, HDComment


class HDAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = HDAttachment
        fields = ['id', 'type', 'name', 'value', 'created_at']
        read_only_fields = ['id', 'created_at']


class HDCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = HDComment
        fields = ['id', 'author_id', 'content', 'is_internal', 'created_at']
        read_only_fields = ['id', 'author_id', 'created_at']


class HelpDeskSerializer(serializers.ModelSerializer):
    attachments = HDAttachmentSerializer(many=True, read_only=True)
    service_name = serializers.CharField(source='service.name', read_only=True)
    service_client_close = serializers.BooleanField(source='service.client_close', read_only=True)

    class Meta:
        model = HelpDesk
        fields = [
            'id', 'folio', 'requester_id', 'assignee_id',
            'service', 'service_name', 'service_client_close',
            'origin', 'priority', 'status',
            'problem_description', 'solution_description',
            'assigned_at', 'due_date', 'resolved_at',
            'estimated_hours', 'attachments', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'folio', 'requester_id', 'assignee_id', 'status',
            'assigned_at', 'resolved_at', 'service_name',
            'attachments', 'created_at', 'updated_at',
        ]


class HelpDeskCreateSerializer(serializers.ModelSerializer):
    """
    Write serializer exclusive to POST /helpdesks/.

    estimated_hours is optional: if not provided in the body, it is inherited
    from the selected service's estimated_hours field. This allows IT to configure
    standard times per service without forcing the requester to know them.

    due_date is not exposed here — it is the area_admin's responsibility
    when assigning the ticket via the /assign/ endpoint.
    """

    class Meta:
        model = HelpDesk
        fields = [
            'service', 'origin', 'priority', 'problem_description',
            'estimated_hours',
        ]
        extra_kwargs = {'estimated_hours': {'required': False}}

    def validate(self, attrs):
        if 'estimated_hours' not in attrs:
            attrs['estimated_hours'] = attrs['service'].estimated_hours
        return attrs


class HelpDeskAssignSerializer(serializers.Serializer):
    """Validates fields for the /assign/ endpoint."""
    assignee_id = serializers.IntegerField()
    due_date = serializers.DateTimeField(required=False, allow_null=True)
