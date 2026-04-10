from rest_framework import serializers

STATUS_CHOICES = ['open', 'in_progress', 'pending_user', 'resolved', 'closed', 'escalated']
PRIORITY_CHOICES = ['low', 'medium', 'high', 'critical']


class TicketCreateSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=300)
    description = serializers.CharField()
    accept_suggestion = serializers.BooleanField(default=False)


class TicketUpdateSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=300, required=False)
    description = serializers.CharField(required=False)


class TicketResponseSerializer(serializers.Serializer):
    id = serializers.CharField()
    folio = serializers.CharField()
    subject = serializers.CharField()
    description = serializers.CharField()
    status = serializers.CharField()
    priority = serializers.CharField()
    category = serializers.CharField()
    created_by = serializers.CharField(allow_null=True)
    assigned_to = serializers.CharField(allow_null=True)
    sla_deadline = serializers.DateTimeField(allow_null=True)
    resolved_at = serializers.DateTimeField(allow_null=True)
    closed_at = serializers.DateTimeField(allow_null=True)
    created_at = serializers.DateTimeField(allow_null=True)
    suggested_category = serializers.CharField(allow_null=True)
    suggested_priority = serializers.CharField(allow_null=True)
    classifier_confidence = serializers.FloatField(allow_null=True)
    suggestion_accepted = serializers.BooleanField(allow_null=True)


class StatusChangeSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=STATUS_CHOICES)


class AssignSerializer(serializers.Serializer):
    agent_id = serializers.CharField()


class DeadlineSerializer(serializers.Serializer):
    sla_deadline = serializers.DateTimeField()


class ClassificationConfirmSerializer(serializers.Serializer):
    category = serializers.CharField(max_length=100)
    priority = serializers.ChoiceField(choices=PRIORITY_CHOICES)
    accepted = serializers.BooleanField()


class CommentCreateSerializer(serializers.Serializer):
    body = serializers.CharField()


class CommentResponseSerializer(serializers.Serializer):
    id = serializers.CharField()
    ticket_id = serializers.CharField()
    author_id = serializers.CharField()
    body = serializers.CharField()
    created_at = serializers.DateTimeField(allow_null=True)


class HistoryResponseSerializer(serializers.Serializer):
    id = serializers.CharField()
    field_changed = serializers.CharField()
    old_value = serializers.CharField()
    new_value = serializers.CharField()
    changed_by = serializers.CharField(allow_null=True)
    created_at = serializers.DateTimeField(allow_null=True)
