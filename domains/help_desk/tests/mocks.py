"""Mock en memoria de ITicketRepository para tests sin base de datos."""
from typing import Optional, List
from datetime import datetime
import uuid

from domains.help_desk.dtos import TicketDTO, CommentDTO, TicketHistoryDTO
from domains.help_desk.repository import ITicketRepository

print(list)

def _make_ticket(**kwargs) -> TicketDTO:
    return TicketDTO(
        id=kwargs.get('id', str(uuid.uuid4())),
        folio=kwargs.get('folio', 'HD-2025-00001'),
        subject=kwargs.get('subject', 'Test'),
        description=kwargs.get('description', ''),
        status=kwargs.get('status', 'open'),
        priority=kwargs.get('priority', 'medium'),
        category=kwargs.get('category', ''),
        created_by=kwargs.get('created_by'),
        assigned_to=kwargs.get('assigned_to'),
        sla_deadline=kwargs.get('sla_deadline'),
        resolved_at=kwargs.get('resolved_at'),
        closed_at=kwargs.get('closed_at'),
        created_at=kwargs.get('created_at', datetime.now()),
        suggested_category=kwargs.get('suggested_category'),
        suggested_priority=kwargs.get('suggested_priority'),
        classifier_confidence=kwargs.get('classifier_confidence'),
        suggestion_accepted=kwargs.get('suggestion_accepted'),
    )


class MockTicketRepository(ITicketRepository):
    def __init__(self, tickets: List[TicketDTO] = None):
        self._tickets: dict[str, TicketDTO] = {t.id: t for t in (tickets or [])}
        self._history: List[TicketHistoryDTO] = []
        self._comments: List[CommentDTO] = []
        self._folio_counter = 1

    
    def get_by_id(self, ticket_id: str) -> Optional[TicketDTO]:
        '''
            Un get no asegura la existencia de un ticket, puede regresar tanto 
            la DTO como un nulo
        '''
        return self._tickets.get(ticket_id)

    def get_by_folio(self, folio: str) -> Optional[TicketDTO]:
        '''
            
        '''
        return next((t for t in self._tickets.values() if t.folio == folio), None)

    def list(self, filters: dict = None) -> list[TicketDTO]:
        tickets = list(self._tickets.values())
        if filters:
            for k, v in filters.items():
                tickets = [t for t in tickets if getattr(t, k, None) == v]
        return tickets

    def create(self, data: dict) -> TicketDTO:
        ticket = _make_ticket(**data)
        self._tickets[ticket.id] = ticket
        return ticket

    def update(self, ticket_id: str, **fields) -> Optional[TicketDTO]:
        t = self._tickets.get(ticket_id)
        if not t:
            return None
        updated_data = {
            'id': t.id, 'folio': t.folio, 'subject': t.subject,
            'description': t.description, 'status': t.status, 'priority': t.priority,
            'category': t.category, 'created_by': t.created_by, 'assigned_to': t.assigned_to,
            'sla_deadline': t.sla_deadline, 'resolved_at': t.resolved_at,
            'closed_at': t.closed_at, 'created_at': t.created_at,
            'suggested_category': t.suggested_category, 'suggested_priority': t.suggested_priority,
            'classifier_confidence': t.classifier_confidence, 'suggestion_accepted': t.suggestion_accepted,
        }
        updated_data.update(fields)
        new_ticket = _make_ticket(**updated_data)
        self._tickets[ticket_id] = new_ticket
        return new_ticket

    def soft_delete(self, ticket_id: str) -> None:
        self._tickets.pop(ticket_id, None)

    def add_history(self, ticket_id: str, field: str, old: str, new: str, by: str) -> TicketHistoryDTO:
        entry = TicketHistoryDTO(
            id=str(uuid.uuid4()), ticket_id=ticket_id,
            field_changed=field, old_value=old, new_value=new,
            changed_by=by, created_at=datetime.now(),
        )
        self._history.append(entry)
        return entry

    def get_history(self, ticket_id: str) -> list[TicketHistoryDTO]:
        return [h for h in self._history if h.ticket_id == ticket_id]

    def add_comment(self, ticket_id: str, author_id: str, body: str) -> CommentDTO:
        comment = CommentDTO(
            id=str(uuid.uuid4()), ticket_id=ticket_id,
            author_id=author_id, body=body, created_at=datetime.now(),
        )
        self._comments.append(comment)
        return comment

    def get_comments(self, ticket_id: str) -> list[CommentDTO]:
        return [c for c in self._comments if c.ticket_id == ticket_id]

    def generate_folio(self) -> str:
        folio = f'HD-2025-{self._folio_counter:05d}'
        self._folio_counter += 1
        return folio
