from shared.exceptions import NotFoundError, ConflictError
from .dtos import TenantDTO, TenantConfigDTO
from .repository import ITenantRepository, DjangoTenantRepository


class TenantService:
    def __init__(self, repo: ITenantRepository = None):
        self._repo = repo or DjangoTenantRepository()

    def create_tenant(self, name: str, slug: str) -> TenantDTO:
        existing = self._repo.get_by_slug(slug)
        if existing:
            raise ConflictError(f"Ya existe una enpresa con el slug '{slug}'")
        return self._repo.create(name=name, slug=slug)

    def get_tenant(self, tenant_id: str) -> TenantDTO:
        tenant = self._repo.get_by_id(tenant_id)
        if not tenant:
            raise NotFoundError(f"Empresa '{tenant_id}' no encontrado")
        return tenant

    def get_config(self, tenant_id: str) -> TenantConfigDTO:
        config = self._repo.get_config(tenant_id)
        if not config:
            raise NotFoundError(f"Configuración de ka enpresa '{tenant_id}' no encontrada")
        return config
