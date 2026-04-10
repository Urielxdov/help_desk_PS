from shared.events import DomainEvent, publish_event
from .dtos import TicketDTO


def _ticket_payload(ticket: TicketDTO) -> dict:
    return {
        'ticket_id': ticket.id,
        'folio': ticket.folio,
        'subject': ticket.subject,
        'status': ticket.status,
        'priority': ticket.priority,
        'category': ticket.category,
        'assigned_to': ticket.assigned_to,
        'created_by': ticket.created_by,
        'suggested_category': ticket.suggested_category,
        'suggested_priority': ticket.suggested_priority,
        'classifier_confidence': ticket.classifier_confidence,
        'suggestion_accepted': ticket.suggestion_accepted,
        'sla_deadline': ticket.sla_deadline.isoformat() if ticket.sla_deadline else None,
        'created_at': ticket.created_at.isoformat() if ticket.created_at else None,
    }


def emit_ticket_created(ticket: TicketDTO) -> None:
    publish_event(DomainEvent(
        event_type='help_desk.ticket_created',
        payload=_ticket_payload(ticket),
    ))


def emit_status_changed(ticket: TicketDTO, from_status: str, changed_by: str) -> None:
    publish_event(DomainEvent(
        event_type='help_desk.status_changed',
        payload={
            **_ticket_payload(ticket),
            'from_status': from_status,
            'to_status': ticket.status,
            'changed_by': changed_by,
            'was_escalated': ticket.status == 'escalated',
        },
    ))


def emit_deadline_set(ticket: TicketDTO, set_by: str) -> None:
    publish_event(DomainEvent(
        event_type='help_desk.deadline_set',
        payload={
            **_ticket_payload(ticket),
            'set_by': set_by,
            'sla_deadline': ticket.sla_deadline.isoformat() if ticket.sla_deadline else None,
        },
    ))


def emit_ticket_closed(ticket: TicketDTO, closed_by: str) -> None:
    publish_event(DomainEvent(
        event_type='help_desk.ticket_closed',
        payload={
            **_ticket_payload(ticket),
            'closed_by': closed_by,
            'closed_at': ticket.closed_at.isoformat() if ticket.closed_at else None,
            'resolved_at': ticket.resolved_at.isoformat() if ticket.resolved_at else None,
        },
    ))
