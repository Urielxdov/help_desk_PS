"""
Mock en memoria de ITenantRepository para tests.

Uso:
    repo = MockTenantRepository([
        TenantDTO(id="t1", name="Acme", slug="acme"),
    ])
    service = TenantService(repo=repo)
    # → tests sin base de datos
"""
from typing import Optional

from domains.tenants.dtos import TenantDTO, TenantConfigDTO
from domains.tenants.repository import ITenantRepository


class MockTenantRepository(ITenantRepository):
    def __init__(self, tenants: list[TenantDTO] = None):
        self._tenants: dict[str, TenantDTO] = {t.id: t for t in (tenants or [])}
        self._configs: dict[str, TenantConfigDTO] = {}
        self._next_id = 100

    def get_by_id(self, tenant_id: str) -> Optional[TenantDTO]:
        return self._tenants.get(tenant_id)

    def get_by_slug(self, slug: str) -> Optional[TenantDTO]:
        return next((t for t in self._tenants.values() if t.slug == slug), None)

    def create(self, name: str, slug: str) -> TenantDTO:
        tenant_id = str(self._next_id)
        self._next_id += 1
        tenant = TenantDTO(id=tenant_id, name=name, slug=slug)
        self._tenants[tenant_id] = tenant
        self._configs[tenant_id] = TenantConfigDTO(id=str(self._next_id), tenant_id=tenant_id)
        return tenant

    def get_config(self, tenant_id: str) -> Optional[TenantConfigDTO]:
        return self._configs.get(tenant_id)
