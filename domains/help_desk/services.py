from datetime import timedelta
from django.utils import timezone

from shared.exceptions import NotFoundError, ForbiddenError, ConflictError
from .classifier import HelpDeskClassifier
from .dtos import TicketDTO, CommentDTO, TicketHistoryDTO
from .events import emit_ticket_created, emit_status_changed, emit_deadline_set, emit_ticket_closed
from .repository import ITicketRepository, DjangoTicketRepository

# Máquina de estados: qué transiciones son válidas desde cada estado
VALID_TRANSITIONS: dict[str, list[str]] = {
    'open':         ['in_progress'],
    'in_progress':  ['pending_user', 'resolved', 'escalated'],
    'pending_user': ['in_progress', 'resolved'],
    'escalated':    ['in_progress', 'resolved'],
    'resolved':     ['closed'],
    'closed':       [],
}


class TicketService:
    def __init__(self, repo: ITicketRepository = None, classifier: HelpDeskClassifier = None):
        self._repo = repo or DjangoTicketRepository()
        self._classifier = classifier or HelpDeskClassifier()

    # ── Creación ──────────────────────────────────────────────────────────────

    def create_ticket(
        self,
        subject: str,
        description: str,
        created_by: str,
        accept_suggestion: bool = False,
    ) -> TicketDTO:
        result = self._classifier.classify(subject, description)

        # El agente puede aceptar la sugerencia en la misma llamada de creación
        final_category = result.category if accept_suggestion else ''
        final_priority = result.priority if accept_suggestion else 'medium'

        ticket = self._repo.create({
            'folio': self._repo.generate_folio(),
            'subject': subject,
            'description': description,
            'status': 'open',
            'priority': final_priority,
            'category': final_category,
            'created_by': created_by,
            'suggested_category': result.category,
            'suggested_priority': result.priority,
            'classifier_confidence': result.confidence,
            'suggestion_accepted': accept_suggestion if accept_suggestion else None,
        })

        emit_ticket_created(ticket)
        return ticket

    def confirm_classification(
        self,
        ticket_id: str,
        category: str,
        priority: str,
        accepted: bool,
        confirmed_by: str,
    ) -> TicketDTO:
        """El agente acepta o corrige la sugerencia del clasificador."""
        ticket = self._get_or_404(ticket_id)
        if ticket.suggestion_accepted is not None:
            raise ConflictError('La clasificación ya fue confirmada')

        updated = self._repo.update(
            ticket_id,
            category=category,
            priority=priority,
            suggestion_accepted=accepted,
        )
        self._repo.add_history(ticket_id, 'classification', '', f'{category}/{priority}', confirmed_by)
        return updated

    # ── Ciclo de vida ─────────────────────────────────────────────────────────

    def change_status(self, ticket_id: str, new_status: str, changed_by: str) -> TicketDTO:
        ticket = self._get_or_404(ticket_id)

        if new_status not in VALID_TRANSITIONS.get(ticket.status, []):
            raise ConflictError(
                f"Transición '{ticket.status}' → '{new_status}' no permitida. "
                f"Válidas: {VALID_TRANSITIONS.get(ticket.status, [])}"
            )

        extra = {}
        if new_status == 'resolved':
            extra['resolved_at'] = timezone.now()
        if new_status == 'closed':
            extra['closed_at'] = timezone.now()

        old_status = ticket.status
        updated = self._repo.update(ticket_id, status=new_status, **extra)
        self._repo.add_history(ticket_id, 'status', old_status, new_status, changed_by)
        emit_status_changed(updated, from_status=old_status, changed_by=changed_by)

        if new_status == 'closed':
            emit_ticket_closed(updated, closed_by=changed_by)

        return updated

    def assign_ticket(self, ticket_id: str, agent_id: str, assigned_by: str) -> TicketDTO:
        ticket = self._get_or_404(ticket_id)
        old_agent = ticket.assigned_to or ''
        updated = self._repo.update(
            ticket_id, assigned_to=agent_id, assigned_at=timezone.now()
        )
        self._repo.add_history(ticket_id, 'assigned_to', old_agent, agent_id, assigned_by)
        return updated

    def set_deadline(self, ticket_id: str, deadline, set_by: str, role: str) -> TicketDTO:
        if role not in ('admin', 'hd_manager'):
            raise ForbiddenError('Solo un HD Manager puede fijar la fecha de compromiso')
        ticket = self._get_or_404(ticket_id)
        updated = self._repo.update(ticket_id, sla_deadline=deadline)
        self._repo.add_history(ticket_id, 'sla_deadline', '', str(deadline), set_by)
        emit_deadline_set(updated, set_by=set_by)
        return updated

    # ── Comentarios ───────────────────────────────────────────────────────────

    def add_comment(self, ticket_id: str, author_id: str, body: str) -> CommentDTO:
        self._get_or_404(ticket_id)
        return self._repo.add_comment(ticket_id, author_id, body)

    def get_comments(self, ticket_id: str) -> list[CommentDTO]:
        self._get_or_404(ticket_id)
        return self._repo.get_comments(ticket_id)

    # ── Consultas ─────────────────────────────────────────────────────────────

    def get_ticket(self, ticket_id: str) -> TicketDTO:
        return self._get_or_404(ticket_id)

    def list_tickets(self, filters: dict = None) -> list[TicketDTO]:
        return self._repo.list(filters)

    def get_history(self, ticket_id: str) -> list[TicketHistoryDTO]:
        self._get_or_404(ticket_id)
        return self._repo.get_history(ticket_id)

    def delete_ticket(self, ticket_id: str, requesting_role: str) -> None:
        if requesting_role != 'admin':
            raise ForbiddenError('Solo un admin puede eliminar tickets')
        self._get_or_404(ticket_id)
        self._repo.soft_delete(ticket_id)

    # ── Interno ───────────────────────────────────────────────────────────────

    def _get_or_404(self, ticket_id: str) -> TicketDTO:
        ticket = self._repo.get_by_id(ticket_id)
        if not ticket:
            raise NotFoundError(f"Ticket '{ticket_id}' no encontrado")
        return ticket
