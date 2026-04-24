"""
Vistas del módulo de Help Desk.

Three ViewSets with separate responsibilities:
- HelpDeskViewSet: full ticket lifecycle (create, list, change status, assign, resolve, close).
- HDAttachmentViewSet: file and URL attachments for a ticket.
- HDCommentViewSet: public and internal comments on a ticket.
- IncidentViewSet: creation and management of incident groups (master tickets).

Ticket visibility in the list is a security rule:
each role only accesses the tickets that belong to them (see get_queryset).
"""
import django_filters
from collections import defaultdict
from django.conf import settings as django_settings
from django.db.models import Exists, OuterRef, Prefetch
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from config.business_hours import calculate_due_date
from apps.catalog.permissions import IsAreaAdmin
from .models import (
    VALID_TRANSITIONS, HDAttachment, HDComment, HelpDesk, Incident,
    IMPACT_CHOICES, PRIORITY_CHOICES, ORIGIN_CHOICES, STATUS_CHOICES,
)
from .permissions import IsTechnicianOrAdmin
from .serializers import (
    HDAttachmentSerializer,
    HDCommentSerializer,
    HelpDeskAssignSerializer,
    HelpDeskCreateSerializer,
    HelpDeskSerializer,
    IncidentSerializer,
    IncidentCreateSerializer,
    LinkTicketsSerializer,
)
from .storage import get_storage

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB


class HelpDeskFilter(django_filters.FilterSet):
    department = django_filters.NumberFilter(field_name='service__category__department_id')

    class Meta:
        model = HelpDesk
        fields = ['status', 'priority', 'service', 'assignee_id', 'department']


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def choices_view(request):
    return Response({
        'impact': [k for k, _ in IMPACT_CHOICES],
        'priority': [k for k, _ in PRIORITY_CHOICES],
        'origin': [k for k, _ in ORIGIN_CHOICES],
        'status': [k for k, _ in STATUS_CHOICES],
    })


def _link_tickets(incident, ticket_ids):
    """
    Vincula tickets existentes a un incidente.

    - Hereda due_date y espeja el status del master.
    - Elimina los tickets de la ServiceQueue (ya no se auto-asignan).
    - Inserta un comentario público en cada hijo informando al usuario.
    Tickets ya vinculados a otro incidente o que son masters se omiten silenciosamente.
    """
    from apps.sla.models import ServiceQueue  # lazy import — evita dependencia circular

    tickets = HelpDesk.objects.filter(
        pk__in=ticket_ids,
        incident__isnull=True,         # no vinculado a otro incidente
        incident_master__isnull=True,  # no es él mismo un master
    )
    master = incident.master_ticket
    for ticket in tickets:
        ticket.incident = incident
        ticket.due_date = master.due_date
        ticket.status = master.status
        ticket.save(update_fields=['incident', 'due_date', 'status', 'updated_at'])

        ServiceQueue.objects.filter(help_desk=ticket).delete()

        HDComment.objects.create(
            help_desk=ticket,
            author_id=None,
            content=(
                f'Tu ticket está siendo atendido como parte del incidente {master.folio}. '
                'Recibirás actualizaciones aquí.'
            ),
            is_internal=False,
        )


def _cascade_close_children(incident, solution_description):
    """Cierra todos los tickets hijos y les notifica con la solución del master."""
    now = timezone.now()
    for child in incident.linked_tickets.exclude(status='closed'):
        child.status = 'closed'
        child.solution_description = solution_description
        child.resolved_at = now
        child.save(update_fields=['status', 'solution_description', 'resolved_at', 'updated_at'])
        HDComment.objects.create(
            help_desk=child,
            author_id=None,
            content=(
                f'Incidente {incident.master_ticket.folio} resuelto. '
                'Tu ticket fue cerrado automáticamente.\n\n'
                f'Solución: {solution_description}'
            ),
            is_internal=False,
        )


class HelpDeskViewSet(viewsets.GenericViewSet):
    serializer_class = HelpDeskSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = HelpDeskFilter

    def get_queryset(self):
        user = self.request.user
        role = getattr(user, 'role', None)
        qs = (
            HelpDesk.objects
            .select_related('service__category__department')
            .prefetch_related(
                'attachments',
                Prefetch('incident', queryset=Incident.objects.select_related('master_ticket')),
                Prefetch('incident_master__linked_tickets'),
            )
            .annotate(
                _is_master=Exists(Incident.objects.filter(master_ticket=OuterRef('pk')))
            )
        )

        if role == 'user':
            return qs.filter(requester_id=user.user_id)
        if role == 'technician':
            return qs.filter(assignee_id=user.user_id)
        return qs

    def list(self, request):
        qs = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(HelpDeskSerializer(page, many=True).data)
        return Response(HelpDeskSerializer(qs, many=True).data)

    def create(self, request):
        serializer = HelpDeskCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        hd = serializer.save(requester_id=getattr(request.user, 'user_id', None))
        return Response(HelpDeskSerializer(hd).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        hd = get_object_or_404(self.get_queryset(), pk=pk)
        return Response(HelpDeskSerializer(hd).data)

    @action(detail=True, methods=['patch'], url_path='status',
            permission_classes=[IsTechnicianOrAdmin])
    def change_status(self, request, pk=None):
        hd = get_object_or_404(self.get_queryset(), pk=pk)

        if hd.incident_id is not None:
            raise ValidationError(
                {'detail': f'Este ticket pertenece al incidente {hd.incident.master_ticket.folio}. '
                           'Su estado es gestionado por el ticket maestro.'}
            )

        new_status = request.data.get('status')
        if new_status not in VALID_TRANSITIONS.get(hd.status, []):
            raise ValidationError(
                {'status': f'Transition not allowed: {hd.status} → {new_status}. '
                           f'Valid options: {VALID_TRANSITIONS[hd.status]}'}
            )

        if getattr(request.user, 'real_role', None) == 'technician' and new_status in ('resolved', 'closed'):
            raise PermissionDenied('Technicians cannot mark tickets as resolved or closed from this endpoint.')

        hd.status = new_status
        hd.save(update_fields=['status', 'updated_at'])

        # Espeja el estado en todos los tickets hijos del incidente
        try:
            hd.incident_master.linked_tickets.exclude(status='closed').update(
                status=new_status,
                updated_at=timezone.now(),
            )
        except Exception:
            pass

        return Response(HelpDeskSerializer(hd).data)

    @action(detail=True, methods=['patch'], url_path='assign',
            permission_classes=[IsAreaAdmin])
    def assign(self, request, pk=None):
        hd = get_object_or_404(self.get_queryset(), pk=pk)
        serializer = HelpDeskAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        now = timezone.now()
        hd.assignee_id = serializer.validated_data['assignee_id']
        hd.assigned_at = now
        if serializer.validated_data.get('due_date'):
            hd.due_date = serializer.validated_data['due_date']
        elif not hd.due_date:
            from apps.sla.services import get_config, _config_value
            config = get_config(hd.service.category.department)
            hd.due_date = calculate_due_date(
                now,
                _config_value(config, 'resolution_time'),
                _config_value(config, 'resolution_unit'),
            )
        if serializer.validated_data.get('impact'):
            hd.impact = serializer.validated_data['impact']
        hd.save(update_fields=['assignee_id', 'assigned_at', 'due_date', 'impact', 'updated_at'])
        return Response(HelpDeskSerializer(hd).data)

    @action(detail=True, methods=['patch'], url_path='resolve',
            permission_classes=[IsTechnicianOrAdmin])
    def resolve(self, request, pk=None):
        hd = get_object_or_404(self.get_queryset(), pk=pk)

        if hd.incident_id is not None:
            raise ValidationError(
                {'detail': f'Este ticket pertenece al incidente {hd.incident.master_ticket.folio}. '
                           'No puede resolverse individualmente.'}
            )

        if hd.status not in ('in_progress', 'on_hold', 'resolved'):
            raise ValidationError(
                {'status': f'Can only resolve from in_progress or on_hold. Current status: {hd.status}'}
            )

        solution_description = request.data.get('solution_description', '').strip()
        if not solution_description:
            raise ValidationError({'solution_description': 'This field is required to resolve a ticket.'})

        hd.status = 'resolved'
        hd.solution_description = solution_description
        hd.resolved_at = timezone.now()
        hd.save(update_fields=['status', 'solution_description', 'resolved_at', 'updated_at'])

        try:
            _cascade_close_children(hd.incident_master, solution_description)
        except Exception:
            pass

        return Response(HelpDeskSerializer(hd).data)

    @action(detail=False, methods=['get'], url_path='monitor',
            permission_classes=[IsAreaAdmin])
    def monitor(self, request):
        """
        Vista de monitoreo de incidentes potenciales.

        Devuelve los servicios con tickets activos (open/in_progress/on_hold)
        sin incidente asignado que superan el threshold del departamento.

        El threshold se resuelve en este orden:
          1. ?threshold=N en la query string (override puntual del admin)
          2. SLAConfig.incident_threshold del departamento
          3. SLAConfig.incident_threshold de la config global (department=null)
          4. settings.INCIDENT_CANDIDATE_THRESHOLD (default del sistema)
        """
        from apps.sla.models import SLAConfig, ServiceQueue  # lazy — evita circular

        system_default = getattr(django_settings, 'INCIDENT_CANDIDATE_THRESHOLD', 5)

        # Override manual desde query param
        try:
            qs_threshold = int(request.query_params['threshold'])
        except (KeyError, ValueError, TypeError):
            qs_threshold = None

        # Cargar todos los thresholds en una sola query
        sla_configs = {c.department_id: c.incident_threshold for c in SLAConfig.objects.all()}
        global_threshold = sla_configs.get(None, system_default)

        # Tickets activos sin incidente
        active_qs = (
            HelpDesk.objects
            .filter(status__in=['open', 'in_progress', 'on_hold'], incident__isnull=True)
            .select_related('service__category__department')
        )
        if dept_id := request.query_params.get('department'):
            active_qs = active_qs.filter(service__category__department_id=dept_id)

        # Agrupar por servicio en Python (un solo hit a BD)
        groups: dict = defaultdict(lambda: {
            'service_id': None, 'service_name': '',
            'department_id': None, 'department_name': '',
            'ticket_ids': [], 'folios': [],
        })
        for hd in active_qs:
            sid = hd.service_id
            g = groups[sid]
            if g['service_id'] is None:
                g['service_id'] = sid
                g['service_name'] = hd.service.name
                g['department_id'] = hd.service.category.department_id
                g['department_name'] = hd.service.category.department.name
            g['ticket_ids'].append(hd.id)
            g['folios'].append(hd.folio)

        # Filtrar por threshold correspondiente a cada departamento
        candidates = []
        for g in groups.values():
            threshold = qs_threshold or sla_configs.get(g['department_id'], global_threshold)
            count = len(g['ticket_ids'])
            if count >= threshold:
                candidates.append({
                    **g,
                    'open_tickets': count,
                    'threshold': threshold,
                })
        candidates.sort(key=lambda x: x['open_tickets'], reverse=True)

        return Response({
            'system_default_threshold': system_default,
            'candidates': candidates,
            'total_active_unlinked': sum(len(g['ticket_ids']) for g in groups.values()),
            'total_queued': ServiceQueue.objects.count(),
        })

    @action(detail=True, methods=['patch'], url_path='close',
            permission_classes=[IsAuthenticated])
    def close(self, request, pk=None):
        hd = get_object_or_404(self.get_queryset(), pk=pk)

        if hd.incident_id is not None:
            raise ValidationError(
                {'detail': f'Este ticket pertenece al incidente {hd.incident.master_ticket.folio}. '
                           'Será cerrado automáticamente cuando el incidente se resuelva.'}
            )

        role = getattr(request.user, 'real_role', None)
        is_requester = hd.requester_id == request.user.user_id

        if role == 'technician':
            raise PermissionDenied('Technicians cannot close tickets.')

        if role == 'user':
            if not is_requester:
                raise PermissionDenied('Only the ticket requester can close it.')
            if not hd.service.client_close:
                raise PermissionDenied('This service type does not allow the requester to close the ticket.')

        if hd.status != 'resolved':
            raise ValidationError({'status': f'Can only close a resolved ticket. Current status: {hd.status}'})

        hd.status = 'closed'
        hd.save(update_fields=['status', 'updated_at'])
        return Response(HelpDeskSerializer(hd).data)


class IncidentViewSet(viewsets.GenericViewSet):
    """
    Gestión de incidentes masivos.

    list/retrieve: IsAuthenticated — cualquier rol puede consultar incidentes
      activos (necesario para mostrar el banner al crear un ticket).
    create/link: IsAreaAdmin — solo admins pueden crear o vincular incidentes.

    Filtros disponibles en list:
      ?service=<id>   — incidentes cuyo master_ticket pertenece a ese servicio
    """
    serializer_class = IncidentSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ('create', 'link'):
            return [IsAreaAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = (
            Incident.objects
            .select_related('master_ticket__service__category__department')
            .prefetch_related(
                Prefetch('linked_tickets', queryset=HelpDesk.objects.only(
                    'id', 'folio', 'requester_id', 'status', 'assigned_at'
                ))
            )
        )
        service_id = self.request.query_params.get('service')
        if service_id:
            qs = qs.filter(master_ticket__service_id=service_id)
        return qs

    def list(self, request):
        qs = self.get_queryset()
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(IncidentSerializer(page, many=True).data)
        return Response(IncidentSerializer(qs, many=True).data)

    def retrieve(self, request, pk=None):
        incident = get_object_or_404(self.get_queryset(), pk=pk)
        return Response(IncidentSerializer(incident).data)

    def create(self, request):
        serializer = IncidentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        ticket_ids = data.pop('ticket_ids', [])

        master = HelpDesk.objects.create(
            requester_id=getattr(request.user, 'user_id', None),
            **data,
        )
        incident = Incident.objects.create(
            master_ticket=master,
            created_by_id=getattr(request.user, 'user_id', None),
        )

        if ticket_ids:
            _link_tickets(incident, ticket_ids)

        incident.refresh_from_db()
        return Response(IncidentSerializer(incident).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='link')
    def link(self, request, pk=None):
        incident = get_object_or_404(self.get_queryset(), pk=pk)

        if incident.master_ticket.status in ('resolved', 'closed'):
            raise ValidationError(
                {'detail': 'No se pueden vincular tickets a un incidente ya resuelto o cerrado.'}
            )

        serializer = LinkTicketsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        _link_tickets(incident, serializer.validated_data['ticket_ids'])

        incident.refresh_from_db()
        return Response(IncidentSerializer(incident).data)


class HDAttachmentViewSet(
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = HDAttachmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return HDAttachment.objects.filter(help_desk_id=self.kwargs['helpdesk_pk'])

    def create(self, request, helpdesk_pk=None):
        hd = get_object_or_404(HelpDesk, pk=helpdesk_pk)
        type_ = request.data.get('type')
        name = request.data.get('name', '')

        if type_ == 'file':
            file = request.FILES.get('file')
            if not file:
                raise ValidationError({'file': 'A file is required when type=file.'})
            if file.size > MAX_UPLOAD_SIZE:
                raise ValidationError({'file': f'File exceeds the maximum size of {MAX_UPLOAD_SIZE // (1024 * 1024)}MB.'})
            storage = get_storage()
            value = storage.save(file, file.name)
        elif type_ == 'url':
            value = request.data.get('value', '').strip()
            if not value:
                raise ValidationError({'value': 'A URL is required when type=url.'})
        else:
            raise ValidationError({'type': 'Must be "file" or "url".'})

        attachment = HDAttachment.objects.create(
            help_desk=hd, type=type_, name=name, value=value
        )
        return Response(HDAttachmentSerializer(attachment).data, status=status.HTTP_201_CREATED)

    def destroy(self, request, helpdesk_pk=None, pk=None):
        attachment = get_object_or_404(self.get_queryset(), pk=pk)
        if attachment.type == 'file':
            get_storage().delete(attachment.value)
        attachment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class HDCommentViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = HDCommentSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        qs = HDComment.objects.filter(help_desk_id=self.kwargs['helpdesk_pk'])
        if getattr(self.request.user, 'role', None) == 'user':
            qs = qs.filter(is_internal=False)
        return qs

    def perform_create(self, serializer):
        hd = get_object_or_404(HelpDesk, pk=self.kwargs['helpdesk_pk'])
        serializer.save(
            help_desk=hd,
            author_id=getattr(self.request.user, 'user_id', None),
        )
