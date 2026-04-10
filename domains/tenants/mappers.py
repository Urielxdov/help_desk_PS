"""
Convierte entre la fuente de datos (modelo Django o respuesta de API externa)
y los DTOs del dominio.

Para cambiar de entidad local a API externa, solo se modifica este archivo:
  - TenantMapper.to_dto() ya acepta tanto modelos Django como dicts de API.
  - El repositorio simplemente pasa la respuesta cruda al mapper.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Union

from .dtos import TenantDTO, TenantConfigDTO

if TYPE_CHECKING:
    from .models import Tenant, TenantConfig


class TenantMapper:
    @staticmethod
    def to_dto(source: Union["Tenant", dict]) -> TenantDTO:
        if isinstance(source, dict):
            # Desde respuesta de API externa
            return TenantDTO(
                id=source["id"],
                name=source["name"],
                slug=source["slug"],
                is_active=source.get("is_active", True),
                schema_name=source.get("schema_name", source["slug"]),
            )
        # Desde modelo Django
        return TenantDTO(
            id=str(source.id),
            name=source.name,
            slug=source.slug,
            is_active=source.is_active,
            schema_name=getattr(source, "schema_name", source.slug),
        )

    @staticmethod
    def to_create_kwargs(dto: TenantDTO) -> dict:
        return {
            "name": dto.name,
            "slug": dto.slug,
            "is_active": dto.is_active,
            "schema_name": dto.schema_name or dto.slug,
        }


class TenantConfigMapper:
    @staticmethod
    def to_dto(source: Union["TenantConfig", dict]) -> TenantConfigDTO:
        if isinstance(source, dict):
            return TenantConfigDTO(
                id=source["id"],
                tenant_id=source["tenant_id"],
                sla_hours_low=source.get("sla_hours_low", 72),
                sla_hours_medium=source.get("sla_hours_medium", 24),
                sla_hours_high=source.get("sla_hours_high", 4),
                classification_threshold=source.get("classification_threshold", 0.4),
                max_tickets_per_agent=source.get("max_tickets_per_agent", 20),
            )
        return TenantConfigDTO(
            id=str(source.id),
            tenant_id=str(source.tenant_id),
            sla_hours_low=source.sla_hours_low,
            sla_hours_medium=source.sla_hours_medium,
            sla_hours_high=source.sla_hours_high,
            classification_threshold=float(source.classification_threshold),
            max_tickets_per_agent=source.max_tickets_per_agent,
        )
