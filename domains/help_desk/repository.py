from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional
from .dtos import TicketDTO, CommentDTO, TicketHistoryDTO
from .mappers import TicketMapper, CommentMapper, HistoryMapper


class ITicketRepository(ABC):
    @abstractmethod
    def get_by_id(self, ticket_id: str) -> Optional[TicketDTO]: ...

    @abstractmethod
    def get_by_folio(self, folio: str) -> Optional[TicketDTO]: ...

    @abstractmethod
    def list(self, filters: dict = None) -> list[TicketDTO]: ...

    @abstractmethod
    def create(self, data: dict) -> TicketDTO: ...

    @abstractmethod
    def update(self, ticket_id: str, **fields) -> TicketDTO: ...

    @abstractmethod
    def soft_delete(self, ticket_id: str) -> None: ...

    @abstractmethod
    def add_history(self, ticket_id: str, field: str, old: str, new: str, by: str) -> TicketHistoryDTO: ...

    @abstractmethod
    def get_history(self, ticket_id: str) -> list[TicketHistoryDTO]: ...

    @abstractmethod
    def add_comment(self, ticket_id: str, author_id: str, body: str) -> CommentDTO: ...

    @abstractmethod
    def get_comments(self, ticket_id: str) -> list[CommentDTO]: ...

    @abstractmethod
    def generate_folio(self) -> str: ...


class DjangoTicketRepository(ITicketRepository):
    def get_by_id(self, ticket_id: str) -> Optional[TicketDTO]:
        from .models import HelpDeskTicket
        try:
            return TicketMapper.to_dto(HelpDeskTicket.objects.get(id=ticket_id, is_active=True))
        except HelpDeskTicket.DoesNotExist:
            return None

    def get_by_folio(self, folio: str) -> Optional[TicketDTO]:
        from .models import HelpDeskTicket
        try:
            return TicketMapper.to_dto(HelpDeskTicket.objects.get(folio=folio))
        except HelpDeskTicket.DoesNotExist:
            return None

    def list(self, filters: dict = None) -> list[TicketDTO]:
        from .models import HelpDeskTicket
        qs = HelpDeskTicket.objects.filter(is_active=True)
        if filters:
            if filters.get('status'):
                qs = qs.filter(status=filters['status'])
            if filters.get('priority'):
                qs = qs.filter(priority=filters['priority'])
            if filters.get('assigned_to'):
                qs = qs.filter(assigned_to=filters['assigned_to'])
            if filters.get('category'):
                qs = qs.filter(category=filters['category'])
        return [TicketMapper.to_dto(t) for t in qs]

    def create(self, data: dict) -> TicketDTO:
        from .models import HelpDeskTicket
        ticket = HelpDeskTicket.objects.create(**data)
        return TicketMapper.to_dto(ticket)

    def update(self, ticket_id: str, **fields) -> TicketDTO:
        from .models import HelpDeskTicket
        HelpDeskTicket.objects.filter(id=ticket_id).update(**fields)
        return self.get_by_id(ticket_id)

    def soft_delete(self, ticket_id: str) -> None:
        from .models import HelpDeskTicket
        try:
            HelpDeskTicket.objects.get(id=ticket_id).soft_delete()
        except HelpDeskTicket.DoesNotExist:
            pass

    def add_history(self, ticket_id: str, field: str, old: str, new: str, by: str) -> TicketHistoryDTO:
        from .models import HelpDeskHistory
        entry = HelpDeskHistory.objects.create(
            ticket_id=ticket_id,
            field_changed=field,
            old_value=old or '',
            new_value=new or '',
            changed_by=by,
        )
        return HistoryMapper.to_dto(entry)

    def get_history(self, ticket_id: str) -> list[TicketHistoryDTO]:
        from .models import HelpDeskHistory
        return [HistoryMapper.to_dto(h) for h in HelpDeskHistory.objects.filter(ticket_id=ticket_id)]

    def add_comment(self, ticket_id: str, author_id: str, body: str) -> CommentDTO:
        from .models import Comment
        comment = Comment.objects.create(ticket_id=ticket_id, author_id=author_id, body=body)
        return CommentMapper.to_dto(comment)

    def get_comments(self, ticket_id: str) -> list[CommentDTO]:
        from .models import Comment
        return [CommentMapper.to_dto(c) for c in Comment.objects.filter(ticket_id=ticket_id)]

    def generate_folio(self) -> str:
        from django.utils import timezone
        from .models import HelpDeskTicket
        year = timezone.now().year
        count = HelpDeskTicket.objects.filter(created_at__year=year).count() + 1
        return f'HD-{year}-{count:05d}'
