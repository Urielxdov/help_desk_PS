"""
Puerto (interfaz) e implementación Django para el dominio tenants.

Regla de sustitución:
  - Todos los demás dominios dependen únicamente de ITenantRepository.
  - Para cambiar a API externa: crear ExternalAPITenantRepository(ITenantRepository)
    y actualizar el binding en services.py — nada más cambia.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from .dtos import TenantDTO, TenantConfigDTO
from .mappers import TenantMapper, TenantConfigMapper


class ITenantRepository(ABC):
    @abstractmethod
    def get_by_id(self, tenant_id: str) -> Optional[TenantDTO]:
        ...

    @abstractmethod
    def get_by_slug(self, slug: str) -> Optional[TenantDTO]:
        ...

    @abstractmethod
    def create(self, name: str, slug: str) -> TenantDTO:
        ...

    @abstractmethod
    def get_config(self, tenant_id: str) -> Optional[TenantConfigDTO]:
        ...


class DjangoTenantRepository(ITenantRepository):
    """Implementación sobre modelos Django. Único lugar donde se importan los modelos."""

    def get_by_id(self, tenant_id: str) -> Optional[TenantDTO]:
        from .models import Tenant
        try:
            return TenantMapper.to_dto(Tenant.objects.get(id=tenant_id, is_active=True))
        except Tenant.DoesNotExist:
            return None

    def get_by_slug(self, slug: str) -> Optional[TenantDTO]:
        from .models import Tenant
        try:
            return TenantMapper.to_dto(Tenant.objects.get(slug=slug, is_active=True))
        except Tenant.DoesNotExist:
            return None

    def create(self, name: str, slug: str) -> TenantDTO:
        from .models import Tenant, TenantConfig
        tenant = Tenant.objects.create(name=name, slug=slug, schema_name=slug)
        TenantConfig.objects.create(tenant=tenant)
        return TenantMapper.to_dto(tenant)

    def get_config(self, tenant_id: str) -> Optional[TenantConfigDTO]:
        from .models import TenantConfig
        try:
            return TenantConfigMapper.to_dto(
                TenantConfig.objects.get(tenant_id=tenant_id)
            )
        except TenantConfig.DoesNotExist:
            return None
