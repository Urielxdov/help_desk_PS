from shared.events import DomainEvent


def create_snapshot_from_event(event: DomainEvent) -> None:
    """
    Persiste un HelpDeskSnapshot a partir de un DomainEvent de help_desk.
    Llamado por la signal en apps.py — nunca importa modelos de help_desk.
    Toda la información llega en event.payload.
    """
    from .models import HelpDeskSnapshot

    payload = event.payload
    ticket_id = payload.get('ticket_id')
    if not ticket_id:
        return

    event_type_map = {
        'help_desk.ticket_created': 'created',
        'help_desk.status_changed': 'status_changed',
        'help_desk.deadline_set': 'deadline_set',
        'help_desk.ticket_closed': 'closed',
    }
    event_type = event_type_map.get(event.event_type)
    if not event_type:
        return

    HelpDeskSnapshot.objects.create(
        ticket_id=ticket_id,
        event_type=event_type,
        status=payload.get('status', ''),
        priority=payload.get('priority', ''),
        category=payload.get('category', ''),
        assigned_to=payload.get('assigned_to') or None,
        was_escalated=payload.get('was_escalated', False),
        suggested_category=payload.get('suggested_category'),
        suggested_priority=payload.get('suggested_priority'),
        accepted_category=payload.get('category') if payload.get('suggestion_accepted') else None,
        accepted_priority=payload.get('priority') if payload.get('suggestion_accepted') else None,
        suggestion_accepted=payload.get('suggestion_accepted'),
        classifier_confidence=payload.get('classifier_confidence'),
        snapshot_data=payload,
    )
