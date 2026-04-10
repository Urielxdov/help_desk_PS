class TenantFilterMixin:
    """Filtra automáticamente el QuerySet por request.tenant."""

    def get_queryset(self):
        qs = super().get_queryset()
        tenant = getattr(self.request, 'tenant', None)
        if tenant is not None and hasattr(qs.model, 'tenant_id'):
            qs = qs.filter(tenant_id=tenant.id)
        return qs


class AuditMixin:
    """Asigna created_by / updated_by desde request.user."""

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user.id)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user.id)
