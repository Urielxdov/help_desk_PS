"""
Convierte entre la fuente de datos (modelo Django o respuesta de API externa)
y los DTOs del dominio users.

Para migrar a API externa:
  1. Implementar ExternalAPIUserRepository(IUserRepository).
  2. En sus métodos, pasar el dict de respuesta directamente a UserMapper.to_dto().
  3. Ajustar los nombres de campo del dict si la API usa convenciones distintas.
  Nada fuera de este archivo y del repositorio necesita cambiar.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Union

from .dtos import UserDTO, DepartmentDTO

if TYPE_CHECKING:
    from .models import User, Department


class DepartmentMapper:
    @staticmethod
    def to_dto(source: Union["Department", dict]) -> DepartmentDTO:
        if isinstance(source, dict):
            return DepartmentDTO(
                id=source["id"],
                name=source["name"],
                keywords=source.get("keywords", ""),
                sla_hours=source.get("sla_hours", 24),
                is_active=source.get("is_active", True),
            )
        return DepartmentDTO(
            id=str(source.id),
            name=source.name,
            keywords=source.keywords or "",
            sla_hours=source.sla_hours,
            is_active=source.is_active,
        )

    @staticmethod
    def to_create_kwargs(dto: DepartmentDTO) -> dict:
        return {
            "name": dto.name,
            "keywords": dto.keywords,
            "sla_hours": dto.sla_hours,
        }


class UserMapper:
    @staticmethod
    def to_dto(source: Union["User", dict]) -> UserDTO:
        if isinstance(source, dict):
            return UserDTO(
                id=source["id"],
                email=source["email"],
                full_name=source.get("full_name", ""),
                role=source.get("role", "end_user"),
                is_active=source.get("is_active", True),
                department_id=source.get("department_id"),
                position=source.get("position"),
            )
        return UserDTO(
            id=str(source.id),
            email=source.email,
            full_name=source.full_name,
            role=source.role,
            is_active=source.is_active,
            department_id=str(source.department_id) if source.department_id else None,
            position=source.position,
        )

    @staticmethod
    def to_create_kwargs(dto: UserDTO) -> dict:
        return {
            "email": dto.email,
            "full_name": dto.full_name,
            "role": dto.role,
            "department_id": dto.department_id,
            "position": dto.position,
        }
