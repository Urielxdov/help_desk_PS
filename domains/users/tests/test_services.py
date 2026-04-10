import pytest
from domains.users.dtos import UserDTO
from domains.users.services import UserService
from shared.exceptions import ConflictError, NotFoundError, ForbiddenError
from .mocks import MockUserRepository


def svc(users=None):
    return UserService(repo=MockUserRepository(users or []))


def test_create_user():
    user = svc().create_user('a@test.com', 'Agent One', 'agent', 'pass1234')
    assert user.email == 'a@test.com'
    assert user.role == 'agent'


def test_create_user_duplicate_raises():
    existing = UserDTO(id='1', email='dup@test.com', full_name='Dup', role='agent')
    with pytest.raises(ConflictError):
        svc([existing]).create_user('dup@test.com', 'Other', 'agent', 'pass1234')


def test_get_user_not_found():
    with pytest.raises(NotFoundError):
        svc().get_user('nonexistent')


def test_delete_user_requires_admin():
    u = UserDTO(id='1', email='x@test.com', full_name='X', role='agent')
    with pytest.raises(ForbiddenError):
        svc([u]).delete_user('1', requesting_role='agent')


def test_delete_user_as_admin():
    u = UserDTO(id='1', email='x@test.com', full_name='X', role='agent')
    repo = MockUserRepository([u])
    UserService(repo=repo).delete_user('1', requesting_role='admin')
    assert repo.get_by_id('1') is None


def test_list_agents_filters_by_role():
    users = [
        UserDTO(id='1', email='a@t.com', full_name='A', role='agent'),
        UserDTO(id='2', email='b@t.com', full_name='B', role='hd_manager'),
    ]
    agents = svc(users).list_agents()
    assert len(agents) == 1
    assert agents[0].role == 'agent'
