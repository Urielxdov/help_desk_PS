"""
Mocks en memoria de IUserRepository e IDepartmentRepository para tests.

Uso:
    user_repo = MockUserRepository([
        UserDTO(id="u1", email="agent@test.com", full_name="Agent One",
                role="agent", department_id="d1"),
    ])
    service = UserService(repo=user_repo)
    # → tests sin base de datos ni migraciones
"""
from typing import Optional

from domains.users.dtos import UserDTO, DepartmentDTO
from domains.users.repository import IUserRepository, IDepartmentRepository


class MockDepartmentRepository(IDepartmentRepository):
    def __init__(self, departments: list[DepartmentDTO] = None):
        self._depts: dict[str, DepartmentDTO] = {d.id: d for d in (departments or [])}
        self._next_id = 100

    def get_by_id(self, dept_id: str) -> Optional[DepartmentDTO]:
        return self._depts.get(dept_id)

    def list_active(self) -> list[DepartmentDTO]:
        return [d for d in self._depts.values() if d.is_active]

    def create(self, name: str, keywords: str = "", sla_hours: int = 24) -> DepartmentDTO:
        dept_id = str(self._next_id)
        self._next_id += 1
        dept = DepartmentDTO(id=dept_id, name=name, keywords=keywords, sla_hours=sla_hours)
        self._depts[dept_id] = dept
        return dept


class MockUserRepository(IUserRepository):
    def __init__(self, users: list[UserDTO] = None):
        self._users: dict[str, UserDTO] = {u.id: u for u in (users or [])}
        self._next_id = 200

    def get_by_id(self, user_id: str) -> Optional[UserDTO]:
        u = self._users.get(user_id)
        return u if (u and u.is_active) else None

    def get_by_email(self, email: str) -> Optional[UserDTO]:
        return next(
            (u for u in self._users.values() if u.email == email and u.is_active),
            None,
        )

    def list_by_department(self, department_id: str) -> list[UserDTO]:
        return [u for u in self._users.values() if u.department_id == department_id and u.is_active]

    def create(self, email: str, full_name: str, role: str, department_id: Optional[str] = None, password: str = None) -> UserDTO:
        user_id = str(self._next_id)
        self._next_id += 1
        user = UserDTO(id=user_id, email=email, full_name=full_name, role=role, department_id=department_id)
        self._users[user_id] = user
        return user

    def soft_delete(self, user_id: str) -> None:
        if user_id in self._users:
            u = self._users[user_id]
            self._users[user_id] = UserDTO(
                id=u.id, email=u.email, full_name=u.full_name,
                role=u.role, is_active=False, department_id=u.department_id,
            )

    def count_active_tickets(self, user_id: str) -> int:
        return 0
