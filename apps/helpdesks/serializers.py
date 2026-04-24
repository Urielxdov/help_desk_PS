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
from .models import HelpDesk, HDAttachment, HDComment, Incident, ORIGIN_CHOICES, PRIORITY_CHOICES


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


class IncidentSummarySerializer(serializers.ModelSerializer):
    """
    Resumen del incidente expuesto en cada ticket hijo.
    Permite al usuario ver que su ticket está siendo atendido
    como parte de un incidente y consultar el estado del master.
    """
    master_folio = serializers.CharField(source='master_ticket.folio', read_only=True)
    master_status = serializers.CharField(source='master_ticket.status', read_only=True)
    master_description = serializers.CharField(source='master_ticket.problem_description', read_only=True)
    master_due_date = serializers.DateTimeField(source='master_ticket.due_date', read_only=True)

    class Meta:
        model = Incident
        fields = ['id', 'master_folio', 'master_status', 'master_description', 'master_due_date']


class LinkedTicketSerializer(serializers.ModelSerializer):
    """Resumen de ticket hijo mostrado en el detalle del incidente."""
    class Meta:
        model = HelpDesk
        fields = ['id', 'folio', 'requester_id', 'status', 'assigned_at']
        read_only_fields = ['id', 'folio', 'requester_id', 'status', 'assigned_at']


class HelpDeskSerializer(serializers.ModelSerializer):
    attachments = HDAttachmentSerializer(many=True, read_only=True)
    service_name = serializers.CharField(source='service.name', read_only=True)
    service_client_close = serializers.BooleanField(source='service.client_close', read_only=True)
    # incident: null para tickets normales y maestros; populated para tickets hijos
    incident = IncidentSummarySerializer(read_only=True)
    # is_master: calculado vía anotación en get_queryset (sin campo DB derivado)
    is_master = serializers.SerializerMethodField()
    linked_tickets = serializers.SerializerMethodField()
    linked_tickets_count = serializers.SerializerMethodField()

    class Meta:
        model = HelpDesk
        fields = [
            'id', 'folio', 'requester_id', 'assignee_id',
            'service', 'service_name', 'service_client_close',
            'origin', 'priority', 'impact', 'status',
            'problem_description', 'solution_description',
            'assigned_at', 'due_date', 'resolved_at',
            'estimated_hours', 'attachments',
            'incident', 'is_master', 'linked_tickets_count', 'linked_tickets',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'folio', 'requester_id', 'assignee_id', 'status',
            'assigned_at', 'resolved_at', 'service_name', 'attachments',
            'incident', 'is_master', 'linked_tickets_count', 'linked_tickets',
            'created_at', 'updated_at',
        ]

    def get_is_master(self, obj):
        # _is_master es una anotación Exists() añadida en get_queryset.
        # Fallback False para contextos sin anotación (ej. tests, signals).
        return getattr(obj, '_is_master', False)

    def get_linked_tickets(self, obj):
        try:
            # incident_master es el reverse OneToOne de Incident.master_ticket.
            # Prefetchado en get_queryset — no genera query adicional.
            return LinkedTicketSerializer(
                obj.incident_master.linked_tickets.all(), many=True
            ).data
        except Exception:
            return []

    def get_linked_tickets_count(self, obj):
        try:
            # len() usa el cache del prefetch; .count() emitiría otra query.
            return len(obj.incident_master.linked_tickets.all())
        except Exception:
            return 0


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
        attrs['impact'] = attrs['service'].impact
        return attrs


class HelpDeskAssignSerializer(serializers.Serializer):
    """Validates fields for the /assign/ endpoint."""
    assignee_id = serializers.IntegerField()
    due_date = serializers.DateTimeField(required=False, allow_null=True)
    impact = serializers.ChoiceField(
        choices=['individual', 'area', 'company'],
        required=False,
    )


class IncidentSerializer(serializers.ModelSerializer):
    """
    Serializer principal del Incident. Usado en IncidentViewSet.
    master_ticket expone el ticket de seguimiento completo.
    linked_tickets lista los tickets agrupados bajo este incidente.
    """
    master_ticket = HelpDeskSerializer(read_only=True)
    linked_tickets = LinkedTicketSerializer(many=True, read_only=True)
    linked_tickets_count = serializers.SerializerMethodField()

    class Meta:
        model = Incident
        fields = [
            'id', 'master_ticket', 'linked_tickets',
            'linked_tickets_count', 'created_by_id', 'created_at',
        ]
        read_only_fields = fields

    def get_linked_tickets_count(self, obj):
        return len(obj.linked_tickets.all())


class IncidentCreateSerializer(serializers.Serializer):
    """
    Write serializer para POST /helpdesks/incidents/.

    Crea el HelpDesk maestro y su Incident contenedor en una sola operación.
    ticket_ids es opcional para vincular tickets existentes al crear.
    """
    from apps.catalog.models import Service
    service = serializers.PrimaryKeyRelatedField(queryset=Service.objects.filter(active=True))
    origin = serializers.ChoiceField(choices=ORIGIN_CHOICES)
    priority = serializers.ChoiceField(choices=PRIORITY_CHOICES)
    problem_description = serializers.CharField()
    estimated_hours = serializers.IntegerField(required=False, min_value=1)
    due_date = serializers.DateTimeField(required=False, allow_null=True)
    ticket_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list,
    )

    def validate(self, attrs):
        if not attrs.get('estimated_hours'):
            attrs['estimated_hours'] = attrs['service'].estimated_hours
        attrs['impact'] = attrs['service'].impact
        return attrs


class LinkTicketsSerializer(serializers.Serializer):
    """Validates the body for POST /helpdesks/incidents/{id}/link/."""
    ticket_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
    )
