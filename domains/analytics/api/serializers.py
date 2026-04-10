from rest_framework import serializers


class SnapshotResponseSerializer(serializers.Serializer):
    id = serializers.CharField()
    ticket_id = serializers.UUIDField()
    event_type = serializers.CharField()
    status = serializers.CharField()
    priority = serializers.CharField()
    category = serializers.CharField()
    assigned_to = serializers.UUIDField(allow_null=True)
    was_escalated = serializers.BooleanField()
    suggested_category = serializers.CharField(allow_null=True)
    suggested_priority = serializers.CharField(allow_null=True)
    accepted_category = serializers.CharField(allow_null=True)
    accepted_priority = serializers.CharField(allow_null=True)
    suggestion_accepted = serializers.BooleanField(allow_null=True)
    classifier_confidence = serializers.FloatField(allow_null=True)
    snapshot_data = serializers.JSONField()
    created_at = serializers.DateTimeField()
