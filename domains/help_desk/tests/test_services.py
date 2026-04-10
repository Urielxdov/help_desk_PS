import pytest
from domains.help_desk.classifier import HelpDeskClassifier, ClassificationResult
from domains.help_desk.dtos import TicketDTO
from domains.help_desk.services import TicketService
from shared.exceptions import NotFoundError, ForbiddenError, ConflictError
from .mocks import MockTicketRepository, _make_ticket


class FixedClassifier(HelpDeskClassifier):
    """Clasificador determinista para tests."""
    def classify(self, subject, description):
        return ClassificationResult(
            category='software', priority='high', confidence=0.8
        )


def svc(tickets=None):
    return TicketService(repo=MockTicketRepository(tickets or []), classifier=FixedClassifier())


# ── Creación ──────────────────────────────────────────────────────────────────

def test_create_ticket_sets_folio():
    ticket = svc().create_ticket('App caída', 'No carga', created_by='user-1')
    assert ticket.folio.startswith('HD-')


def test_create_ticket_stores_suggestion():
    ticket = svc().create_ticket('App caída', 'No carga', created_by='user-1')
    assert ticket.suggested_category == 'software'
    assert ticket.suggested_priority == 'high'
    assert ticket.classifier_confidence == 0.8
    assert ticket.suggestion_accepted is None


def test_create_ticket_accept_suggestion():
    ticket = svc().create_ticket('App caída', 'No carga', created_by='u1', accept_suggestion=True)
    assert ticket.category == 'software'
    assert ticket.priority == 'high'
    assert ticket.suggestion_accepted is True


# ── Estado ────────────────────────────────────────────────────────────────────

def test_change_status_valid_transition():
    t = _make_ticket(id='t1', status='open')
    ticket = svc([t]).change_status('t1', 'in_progress', changed_by='u1')
    assert ticket.status == 'in_progress'


def test_change_status_invalid_transition_raises():
    t = _make_ticket(id='t1', status='open')
    with pytest.raises(ConflictError):
        svc([t]).change_status('t1', 'resolved', changed_by='u1')


def test_change_status_closed_to_any_raises():
    t = _make_ticket(id='t1', status='closed')
    with pytest.raises(ConflictError):
        svc([t]).change_status('t1', 'open', changed_by='u1')


def test_change_status_records_history():
    t = _make_ticket(id='t1', status='open')
    repo = MockTicketRepository([t])
    service = TicketService(repo=repo, classifier=FixedClassifier())
    service.change_status('t1', 'in_progress', changed_by='u1')
    history = repo.get_history('t1')
    assert len(history) == 1
    assert history[0].field_changed == 'status'
    assert history[0].old_value == 'open'
    assert history[0].new_value == 'in_progress'


# ── Asignación ────────────────────────────────────────────────────────────────

def test_assign_ticket():
    t = _make_ticket(id='t1')
    ticket = svc([t]).assign_ticket('t1', agent_id='agent-99', assigned_by='mgr-1')
    assert ticket.assigned_to == 'agent-99'


# ── Deadline ─────────────────────────────────────────────────────────────────

def test_set_deadline_requires_hd_manager():
    t = _make_ticket(id='t1')
    from datetime import datetime
    with pytest.raises(ForbiddenError):
        svc([t]).set_deadline('t1', datetime.now(), set_by='u1', role='agent')


def test_set_deadline_as_hd_manager():
    from datetime import datetime
    t = _make_ticket(id='t1')
    deadline = datetime(2025, 12, 31)
    ticket = svc([t]).set_deadline('t1', deadline, set_by='mgr', role='hd_manager')
    assert ticket.sla_deadline == deadline


# ── Comentarios ───────────────────────────────────────────────────────────────

def test_add_and_get_comments():
    t = _make_ticket(id='t1')
    repo = MockTicketRepository([t])
    service = TicketService(repo=repo, classifier=FixedClassifier())
    service.add_comment('t1', 'author-1', 'Primer comentario')
    service.add_comment('t1', 'author-2', 'Segundo comentario')
    comments = service.get_comments('t1')
    assert len(comments) == 2


# ── Errores ───────────────────────────────────────────────────────────────────

def test_get_ticket_not_found():
    with pytest.raises(NotFoundError):
        svc().get_ticket('nonexistent')


def test_delete_ticket_requires_admin():
    t = _make_ticket(id='t1')
    with pytest.raises(ForbiddenError):
        svc([t]).delete_ticket('t1', requesting_role='agent')
