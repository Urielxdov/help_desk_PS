"""
Puerto (interfaz) e implementación Django para el dominio users.

Regla de sustitución:
  - tickets, assignments y classification dependen solo de IUserRepository
    y IDepartmentRepository — nunca de los modelos Django directamente.
  - Para cambiar a API externa: implementar ExternalAPIUserRepository(IUserRepository),
    conectarla en services.py. El resto del sistema no toca nada.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from .dtos import UserDTO, DepartmentDTO
from .mappers import UserMapper, DepartmentMapper


# ── Departamentos ─────────────────────────────────────────────────────────────

class IDepartmentRepository(ABC):
    @abstractmethod
    def get_by_id(self, dept_id: str) -> Optional[DepartmentDTO]:
        ...

    @abstractmethod
    def list_active(self) -> list[DepartmentDTO]:
        ...

    @abstractmethod
    def create(self, name: str, keywords: str = "", sla_hours: int = 24) -> DepartmentDTO:
        ...


class DjangoDepartmentRepository(IDepartmentRepository):
    def get_by_id(self, dept_id: str) -> Optional[DepartmentDTO]:
        from .models import Department
        try:
            return DepartmentMapper.to_dto(Department.objects.get(id=dept_id, is_active=True))
        except Department.DoesNotExist:
            return None

    def list_active(self) -> list[DepartmentDTO]:
        from .models import Department
        return [DepartmentMapper.to_dto(d) for d in Department.objects.filter(is_active=True)]

    def create(self, name: str, keywords: str = "", sla_hours: int = 24) -> DepartmentDTO:
        from .models import Department
        dept = Department.objects.create(name=name, keywords=keywords, sla_hours=sla_hours)
        return DepartmentMapper.to_dto(dept)


# ── Usuarios ──────────────────────────────────────────────────────────────────

class IUserRepository(ABC):
    @abstractmethod
    def get_by_id(self, user_id: str) -> Optional[UserDTO]:
        ...

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[UserDTO]:
        ...

    @abstractmethod
    def list_by_department(self, department_id: str) -> list[UserDTO]:
        ...

    @abstractmethod
    def create(self, email: str, full_name: str, role: str, department_id: Optional[str] = None, password: str = None) -> UserDTO:
        ...

    @abstractmethod
    def soft_delete(self, user_id: str) -> None:
        ...

    @abstractmethod
    def count_active_tickets(self, user_id: str) -> int:
        """Carga actual del agente: tickets abiertos asignados."""
        ...


class DjangoUserRepository(IUserRepository):
    def get_by_id(self, user_id: str) -> Optional[UserDTO]:
        from .models import User
        try:
            return UserMapper.to_dto(User.objects.get(id=user_id, is_active=True))
        except User.DoesNotExist:
            return None

    def get_by_email(self, email: str) -> Optional[UserDTO]:
        from .models import User
        try:
            return UserMapper.to_dto(User.objects.get(email=email, is_active=True))
        except User.DoesNotExist:
            return None

    def list_by_department(self, department_id: str) -> list[UserDTO]:
        from .models import User
        return [
            UserMapper.to_dto(u)
            for u in User.objects.filter(department_id=department_id, is_active=True)
        ]

    def create(self, email: str, full_name: str, role: str, department_id: Optional[str] = None, password: str = None) -> UserDTO:
        from .models import User
        user = User.objects.create_user(
            email=email,
            full_name=full_name,
            role=role,
            department_id=department_id,
            password=password,
        )
        return UserMapper.to_dto(user)

    def soft_delete(self, user_id: str) -> None:
        from .models import User
        try:
            user = User.objects.get(id=user_id)
            user.soft_delete()
        except User.DoesNotExist:
            pass

    def count_active_tickets(self, user_id: str) -> int:
        # assignments domain publica esto vía evento; aquí devolvemos 0 como default
        # para no crear dependencia circular. assignments.services llama esto a través
        # de su propia lógica de balance.
        return 0
