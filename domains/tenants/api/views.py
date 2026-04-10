from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from shared.responses import success_response, error_response
from shared.exceptions import DomainException
from ..services import TenantService
from .serializers import TenantCreateSerializer, TenantResponseSerializer


class TenantListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._service = TenantService()

    def post(self, request):
        serializer = TenantCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(serializer.errors, code="ValidationError", status=422)

        try:
            tenant = self._service.create_tenant(
                name=serializer.validated_data["name"],
                slug=serializer.validated_data["slug"],
            )
        except DomainException as e:
            return error_response(e.message, code=type(e).__name__, status=e.status_code)

        return success_response(
            TenantResponseSerializer(tenant).data,
            message="Tenant creado",
            status=201,
        )


class TenantDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._service = TenantService()

    def get(self, request, tenant_id: str):
        try:
            tenant = self._service.get_tenant(tenant_id)
        except DomainException as e:
            return error_response(e.message, code=type(e).__name__, status=e.status_code)

        return success_response(TenantResponseSerializer(tenant).data)
