from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action

from shared.permissions import IsAgent, IsHDManager, IsAdmin
from shared.responses import success_response, error_response
from shared.exceptions import DomainException
from ..services import TicketService
from .serializers import (
    TicketCreateSerializer, TicketUpdateSerializer, TicketResponseSerializer,
    StatusChangeSerializer, AssignSerializer, DeadlineSerializer,
    ClassificationConfirmSerializer,
    CommentCreateSerializer, CommentResponseSerializer,
    HistoryResponseSerializer,
)


class HelpDeskViewSet(ViewSet):
    """
    Endpoints estándar (via router):
      GET    /help-desk/              → list
      POST   /help-desk/              → create
      GET    /help-desk/{pk}/         → retrieve
      PATCH  /help-desk/{pk}/         → partial_update
      DELETE /help-desk/{pk}/         → destroy

    Acciones extra (@action):
      PATCH  /help-desk/{pk}/status/         → change_status
      PATCH  /help-desk/{pk}/assign/         → assign
      PATCH  /help-desk/{pk}/deadline/       → set_deadline
      PATCH  /help-desk/{pk}/classify/       → confirm_classification
      GET    /help-desk/{pk}/history/        → history
      GET    /help-desk/{pk}/comments/       → comments (lista)
      POST   /help-desk/{pk}/comments/       → comments (crear)
    """

    def get_permissions(self):
        if self.action == 'destroy':
            return [IsAdmin()]
        if self.action in ('assign', 'set_deadline'):
            return [IsHDManager()]
        return [IsAgent()]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._service = TicketService()

    # ── CRUD base ─────────────────────────────────────────────────────────────

    def list(self, request):
        filters = {k: v for k, v in request.query_params.items()
                   if k in ('status', 'priority', 'assigned_to', 'category')}
        tickets = self._service.list_tickets(filters or None)
        return success_response(TicketResponseSerializer(tickets, many=True).data)

    def create(self, request):
        serializer = TicketCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(serializer.errors, code='ValidationError', status=422)
        try:
            ticket = self._service.create_ticket(
                subject=serializer.validated_data['subject'],
                description=serializer.validated_data['description'],
                created_by=str(request.user.id),
                accept_suggestion=serializer.validated_data.get('accept_suggestion', False),
            )
        except DomainException as e:
            return error_response(e.message, code=type(e).__name__, status=e.status_code)
        return success_response(TicketResponseSerializer(ticket).data, status=201)

    def retrieve(self, request, pk=None):
        try:
            ticket = self._service.get_ticket(pk)
        except DomainException as e:
            return error_response(e.message, code=type(e).__name__, status=e.status_code)
        return success_response(TicketResponseSerializer(ticket).data)

    def partial_update(self, request, pk=None):
        serializer = TicketUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(serializer.errors, code='ValidationError', status=422)
        try:
            ticket = self._service.get_ticket(pk)  # valida existencia
            from ..repository import DjangoTicketRepository
            ticket = DjangoTicketRepository().update(pk, **serializer.validated_data)
        except DomainException as e:
            return error_response(e.message, code=type(e).__name__, status=e.status_code)
        return success_response(TicketResponseSerializer(ticket).data)

    def destroy(self, request, pk=None):
        try:
            self._service.delete_ticket(
                ticket_id=pk,
                requesting_role=getattr(request.user, 'role', ''),
            )
        except DomainException as e:
            return error_response(e.message, code=type(e).__name__, status=e.status_code)
        return success_response(None, message='Ticket eliminado')

    # ── Acciones de ciclo de vida ─────────────────────────────────────────────

    @action(detail=True, methods=['patch'], url_path='status')
    def change_status(self, request, pk=None):
        serializer = StatusChangeSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(serializer.errors, code='ValidationError', status=422)
        try:
            ticket = self._service.change_status(
                ticket_id=pk,
                new_status=serializer.validated_data['status'],
                changed_by=str(request.user.id),
            )
        except DomainException as e:
            return error_response(e.message, code=type(e).__name__, status=e.status_code)
        return success_response(TicketResponseSerializer(ticket).data)

    @action(detail=True, methods=['patch'], url_path='assign')
    def assign(self, request, pk=None):
        serializer = AssignSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(serializer.errors, code='ValidationError', status=422)
        try:
            ticket = self._service.assign_ticket(
                ticket_id=pk,
                agent_id=serializer.validated_data['agent_id'],
                assigned_by=str(request.user.id),
            )
        except DomainException as e:
            return error_response(e.message, code=type(e).__name__, status=e.status_code)
        return success_response(TicketResponseSerializer(ticket).data)

    @action(detail=True, methods=['patch'], url_path='deadline')
    def set_deadline(self, request, pk=None):
        serializer = DeadlineSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(serializer.errors, code='ValidationError', status=422)
        try:
            ticket = self._service.set_deadline(
                ticket_id=pk,
                deadline=serializer.validated_data['sla_deadline'],
                set_by=str(request.user.id),
                role=getattr(request.user, 'role', ''),
            )
        except DomainException as e:
            return error_response(e.message, code=type(e).__name__, status=e.status_code)
        return success_response(TicketResponseSerializer(ticket).data)

    @action(detail=True, methods=['patch'], url_path='classify')
    def confirm_classification(self, request, pk=None):
        serializer = ClassificationConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(serializer.errors, code='ValidationError', status=422)
        try:
            ticket = self._service.confirm_classification(
                ticket_id=pk,
                category=serializer.validated_data['category'],
                priority=serializer.validated_data['priority'],
                accepted=serializer.validated_data['accepted'],
                confirmed_by=str(request.user.id),
            )
        except DomainException as e:
            return error_response(e.message, code=type(e).__name__, status=e.status_code)
        return success_response(TicketResponseSerializer(ticket).data)

    # ── Comentarios e historial ───────────────────────────────────────────────

    @action(detail=True, methods=['get', 'post'], url_path='comments')
    def comments(self, request, pk=None):
        if request.method == 'GET':
            try:
                comments = self._service.get_comments(pk)
            except DomainException as e:
                return error_response(e.message, code=type(e).__name__, status=e.status_code)
            return success_response(CommentResponseSerializer(comments, many=True).data)

        serializer = CommentCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(serializer.errors, code='ValidationError', status=422)
        try:
            comment = self._service.add_comment(
                ticket_id=pk,
                author_id=str(request.user.id),
                body=serializer.validated_data['body'],
            )
        except DomainException as e:
            return error_response(e.message, code=type(e).__name__, status=e.status_code)
        return success_response(CommentResponseSerializer(comment).data, status=201)

    @action(detail=True, methods=['get'], url_path='history')
    def history(self, request, pk=None):
        try:
            entries = self._service.get_history(pk)
        except DomainException as e:
            return error_response(e.message, code=type(e).__name__, status=e.status_code)
        return success_response(HistoryResponseSerializer(entries, many=True).data)
