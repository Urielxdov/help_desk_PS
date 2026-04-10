import pytest

from domains.users.dtos import UserDTO, DepartmentDTO
from domains.users.services import UserService, DepartmentService
from shared.exceptions import ConflictError, NotFoundError, ForbiddenError
from .mocks import MockUserRepository, MockDepartmentRepository


# ── UserService ───────────────────────────────────────────────────────────────

def test_create_user():
    service = UserService(repo=MockUserRepository())
    user = service.create_user(
        email="agent@test.com", full_name="Agent One", role="agent", password="secret123"
    )
    assert user.email == "agent@test.com"
    assert user.role == "agent"


def test_create_user_duplicate_email_raises():
    existing = UserDTO(id="1", email="dup@test.com", full_name="Dup", role="agent")
    service = UserService(repo=MockUserRepository([existing]))
    with pytest.raises(ConflictError):
        service.create_user(email="dup@test.com", full_name="Other", role="agent")


def test_get_user_not_found_raises():
    service = UserService(repo=MockUserRepository())
    with pytest.raises(NotFoundError):
        service.get_user("nonexistent")


def test_delete_user_requires_admin():
    existing = UserDTO(id="u1", email="x@test.com", full_name="X", role="agent")
    service = UserService(repo=MockUserRepository([existing]))
    with pytest.raises(ForbiddenError):
        service.delete_user(user_id="u1", requesting_role="agent")


def test_delete_user_as_admin():
    existing = UserDTO(id="u1", email="x@test.com", full_name="X", role="agent")
    repo = MockUserRepository([existing])
    service = UserService(repo=repo)
    service.delete_user(user_id="u1", requesting_role="admin")
    assert service._repo.get_by_id("u1") is None


# ── DepartmentService ─────────────────────────────────────────────────────────

def test_create_department():
    service = DepartmentService(repo=MockDepartmentRepository())
    dept = service.create_department(name="IT", keywords="servidor red vpn", sla_hours=8)
    assert dept.name == "IT"
    assert dept.keywords == "servidor red vpn"


def test_get_department_not_found_raises():
    service = DepartmentService(repo=MockDepartmentRepository())
    with pytest.raises(NotFoundError):
        service.get_department("nonexistent")


def test_list_agents_in_department():
    dept = DepartmentDTO(id="d1", name="IT")
    users = [
        UserDTO(id="u1", email="a@t.com", full_name="A", role="agent", department_id="d1"),
        UserDTO(id="u2", email="b@t.com", full_name="B", role="agent", department_id="d2"),
    ]
    dept_repo = MockDepartmentRepository([dept])
    user_repo = MockUserRepository(users)
    service = DepartmentService(repo=dept_repo)
    agents = service.list_agents("d1", user_repo=user_repo)
    assert len(agents) == 1
    assert agents[0].id == "u1"
