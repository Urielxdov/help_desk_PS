"""
Tests del servicio analytics sin base de datos.
Se valida que create_snapshot_from_event persiste los campos correctos.
Estos tests necesitan pytest-django y la DB porque usan el ORM.
Para tests puros de lógica ver test_snapshot_logic.py
"""
import pytest
from shared.events import DomainEvent
from domains.analytics.services import create_snapshot_from_event


@pytest.mark.django_db
def test_snapshot_created_on_ticket_created_event():
    from domains.analytics.models import HelpDeskSnapshot
    import uuid

    ticket_id = str(uuid.uuid4())
    event = DomainEvent(
        event_type='help_desk.ticket_created',
        payload={
            'ticket_id': ticket_id,
            'status': 'open',
            'priority': 'medium',
            'category': 'software',
            'suggested_category': 'software',
            'suggested_priority': 'medium',
            'classifier_confidence': 0.75,
            'suggestion_accepted': True,
        },
    )
    create_snapshot_from_event(event)

    snap = HelpDeskSnapshot.objects.get(ticket_id=ticket_id)
    assert snap.event_type == 'created'
    assert snap.status == 'open'
    assert snap.classifier_confidence == 0.75
    assert snap.suggestion_accepted is True


@pytest.mark.django_db
def test_unknown_event_type_is_ignored():
    from domains.analytics.models import HelpDeskSnapshot
    import uuid

    ticket_id = str(uuid.uuid4())
    event = DomainEvent(
        event_type='users.user_created',
        payload={'ticket_id': ticket_id},
    )
    create_snapshot_from_event(event)
    assert not HelpDeskSnapshot.objects.filter(ticket_id=ticket_id).exists()
