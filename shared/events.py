import uuid
from dataclasses import dataclass, field
from datetime import datetime
from django.dispatch import Signal
from django.utils import timezone


domain_event_signal = Signal()


@dataclass
class DomainEvent:
    event_type: str
    payload: dict
    tenant_id: str = ""
    occurred_at: datetime = field(default_factory=timezone.now)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))


def publish_event(event: DomainEvent) -> None:
    """
    Despacha un evento de dominio vía Django signal.
    En Fase 2 se reemplaza por Celery/message broker sin tocar los dominios.
    """
    domain_event_signal.send(
        sender=event.event_type,
        event=event,
    )
