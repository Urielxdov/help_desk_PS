from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class TicketDTO:
    id: str
    folio: str
    subject: str
    description: str
    status: str
    priority: str
    category: str
    created_by: Optional[str]
    assigned_to: Optional[str]
    sla_deadline: Optional[datetime]
    resolved_at: Optional[datetime]
    closed_at: Optional[datetime]
    created_at: Optional[datetime]
    # Datos del clasificador
    suggested_category: Optional[str] = None
    suggested_priority: Optional[str] = None
    classifier_confidence: Optional[float] = None
    suggestion_accepted: Optional[bool] = None


@dataclass
class CommentDTO:
    id: str
    ticket_id: str
    author_id: str
    body: str
    created_at: Optional[datetime] = None


@dataclass
class TicketHistoryDTO:
    id: str
    ticket_id: str
    field_changed: str
    old_value: str
    new_value: str
    changed_by: Optional[str]
    created_at: Optional[datetime] = None
