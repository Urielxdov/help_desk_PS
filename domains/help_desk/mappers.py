from __future__ import annotations
from typing import TYPE_CHECKING, Union
from .dtos import TicketDTO, CommentDTO, TicketHistoryDTO

if TYPE_CHECKING:
    from .models import HelpDeskTicket, Comment, HelpDeskHistory


class TicketMapper:
    @staticmethod
    def to_dto(source: Union["HelpDeskTicket", dict]) -> TicketDTO:
        if isinstance(source, dict):
            return TicketDTO(
                id=source['id'],
                folio=source['folio'],
                subject=source['subject'],
                description=source['description'],
                status=source['status'],
                priority=source['priority'],
                category=source.get('category', ''),
                created_by=source.get('created_by'),
                assigned_to=source.get('assigned_to'),
                sla_deadline=source.get('sla_deadline'),
                resolved_at=source.get('resolved_at'),
                closed_at=source.get('closed_at'),
                created_at=source.get('created_at'),
                suggested_category=source.get('suggested_category'),
                suggested_priority=source.get('suggested_priority'),
                classifier_confidence=source.get('classifier_confidence'),
                suggestion_accepted=source.get('suggestion_accepted'),
            )
        return TicketDTO(
            id=str(source.id),
            folio=source.folio,
            subject=source.subject,
            description=source.description,
            status=source.status,
            priority=source.priority,
            category=source.category,
            created_by=str(source.created_by) if source.created_by else None,
            assigned_to=str(source.assigned_to) if source.assigned_to else None,
            sla_deadline=source.sla_deadline,
            resolved_at=source.resolved_at,
            closed_at=source.closed_at,
            created_at=source.created_at,
            suggested_category=source.suggested_category,
            suggested_priority=source.suggested_priority,
            classifier_confidence=source.classifier_confidence,
            suggestion_accepted=source.suggestion_accepted,
        )


class CommentMapper:
    @staticmethod
    def to_dto(source: Union["Comment", dict]) -> CommentDTO:
        if isinstance(source, dict):
            return CommentDTO(
                id=source['id'],
                ticket_id=source['ticket_id'],
                author_id=source['author_id'],
                body=source['body'],
                created_at=source.get('created_at'),
            )
        return CommentDTO(
            id=str(source.id),
            ticket_id=str(source.ticket_id),
            author_id=str(source.author_id),
            body=source.body,
            created_at=source.created_at,
        )


class HistoryMapper:
    @staticmethod
    def to_dto(source: Union["HelpDeskHistory", dict]) -> TicketHistoryDTO:
        if isinstance(source, dict):
            return TicketHistoryDTO(
                id=source['id'],
                ticket_id=source['ticket_id'],
                field_changed=source['field_changed'],
                old_value=source.get('old_value', ''),
                new_value=source.get('new_value', ''),
                changed_by=source.get('changed_by'),
                created_at=source.get('created_at'),
            )
        return TicketHistoryDTO(
            id=str(source.id),
            ticket_id=str(source.ticket_id),
            field_changed=source.field_changed,
            old_value=source.old_value or '',
            new_value=source.new_value or '',
            changed_by=str(source.changed_by) if source.changed_by else None,
            created_at=source.created_at,
        )
