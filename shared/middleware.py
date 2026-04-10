class TenantMiddleware:
    """
    Inyecta request.tenant en cada request.
    Resuelve el tenant por subdominio o por header X-Tenant-ID.

    En Fase 1 con django-tenants, el tenant ya viene resuelto por el
    middleware de django-tenants. Este middleware actúa como adaptador
    para exponer request.tenant de forma uniforme en toda la app.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.tenant = self._resolve_tenant(request)
        return self.get_response(request)

    def _resolve_tenant(self, request):
        # Prioridad 1: tenant ya resuelto por django-tenants
        if hasattr(request, 'tenant'):
            return request.tenant

        # Prioridad 2: header explícito (útil para tests y API-to-API)
        tenant_id = request.headers.get('X-Tenant-ID')
        if tenant_id:
            return self._load_tenant_by_id(tenant_id)

        return None

    def _load_tenant_by_id(self, tenant_id: str):
        try:
            from domains.tenants.models import Tenant
            return Tenant.objects.get(id=tenant_id, is_active=True)
        except Exception:
            return None
