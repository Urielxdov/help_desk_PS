import pytest

from domains.tenants.dtos import TenantDTO
from domains.tenants.services import TenantService
from shared.exceptions import ConflictError, NotFoundError
from .mocks import MockTenantRepository


def make_service(tenants=None):
    return TenantService(repo=MockTenantRepository(tenants or []))


def test_create_tenant():
    service = make_service()
    tenant = service.create_tenant(name="Acme Corp", slug="acme")
    assert tenant.name == "Acme Corp"
    assert tenant.slug == "acme"


def test_create_tenant_duplicate_slug_raises():
    existing = TenantDTO(id="1", name="Acme", slug="acme")
    service = make_service(tenants=[existing])
    with pytest.raises(ConflictError):
        service.create_tenant(name="Otro", slug="acme")


def test_get_tenant_not_found_raises():
    service = make_service()
    with pytest.raises(NotFoundError):
        service.get_tenant("nonexistent-id")


def test_get_tenant_returns_dto():
    existing = TenantDTO(id="abc", name="Test", slug="test")
    service = make_service(tenants=[existing])
    result = service.get_tenant("abc")
    assert result.id == "abc"
    assert result.name == "Test"
