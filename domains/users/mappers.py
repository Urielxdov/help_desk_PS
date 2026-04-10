"""
Mapper entre la fuente de datos (modelo Django o dict de API externa) y UserDTO.

Para cambiar a API externa: crear ExternalAPIUserRepository(IUserRepository)
y en sus métodos pasar el dict de respuesta a UserMapper.to_dto().
Solo cambia el repositorio — el mapper ya acepta ambos formatos.
"""
from __future__ import annotations
from typing import TYPE_CHECKING, Union
from .dtos import UserDTO

if TYPE_CHECKING:
    from .models import User


class UserMapper:
    @staticmethod
    def to_dto(source: Union["User", dict]) -> UserDTO:
        if isinstance(source, dict):
            return UserDTO(
                id=source["id"],
                email=source["email"],
                full_name=source.get("full_name", ""),
                role=source.get("role", "agent"),
                is_active=source.get("is_active", True),
            )
        return UserDTO(
            id=str(source.id),
            email=source.email,
            full_name=source.full_name,
            role=source.role,
            is_active=source.is_active,
        )
