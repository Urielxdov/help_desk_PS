from django.db import models
from shared.models import BaseModel, SoftDeleteModel


class Tenant(SoftDeleteModel):
    """Organización registrada en el sistema. Vive en schema público."""
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=100)
    schema_name = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = "tenants_tenant"

    def __str__(self):
        return self.name


class TenantConfig(BaseModel):
    """Configuración operativa por organización."""
    tenant = models.OneToOneField(
        Tenant, on_delete=models.CASCADE, related_name="config"
    )
    sla_hours_low = models.PositiveIntegerField(default=72)
    sla_hours_medium = models.PositiveIntegerField(default=24)
    sla_hours_high = models.PositiveIntegerField(default=4)
    classification_threshold = models.FloatField(default=0.4)
    max_tickets_per_agent = models.PositiveIntegerField(default=20)

    class Meta:
        db_table = "tenants_config"

    def __str__(self):
        return f"Config({self.tenant.slug})"
