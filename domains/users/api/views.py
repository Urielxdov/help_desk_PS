from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from shared.responses import success_response, error_response
from shared.exceptions import DomainException
from shared.permissions import IsTenantAdmin, IsHDManager
from ..services import UserService, DepartmentService
from .serializers import (
    UserCreateSerializer, UserResponseSerializer,
    DepartmentCreateSerializer, DepartmentResponseSerializer,
)


class UserListCreateView(APIView):
    permission_classes = [IsTenantAdmin]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._service = UserService()

    def post(self, request):
        serializer = UserCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(serializer.errors, code="ValidationError", status=422)

        try:
            user = self._service.create_user(**serializer.validated_data)
        except DomainException as e:
            return error_response(e.message, code=type(e).__name__, status=e.status_code)

        return success_response(UserResponseSerializer(user).data, status=201)


class UserDetailView(APIView):
    permission_classes = [IsTenantAdmin]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._service = UserService()

    def get(self, request, user_id: str):
        try:
            user = self._service.get_user(user_id)
        except DomainException as e:
            return error_response(e.message, code=type(e).__name__, status=e.status_code)
        return success_response(UserResponseSerializer(user).data)

    def delete(self, request, user_id: str):
        try:
            self._service.delete_user(
                user_id=user_id,
                requesting_role=getattr(request.user, 'role', ''),
            )
        except DomainException as e:
            return error_response(e.message, code=type(e).__name__, status=e.status_code)
        return success_response(None, message="Usuario eliminado")


class DepartmentListCreateView(APIView):
    permission_classes = [IsTenantAdmin]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._service = DepartmentService()

    def get(self, request):
        depts = self._service.list_departments()
        return success_response(DepartmentResponseSerializer(depts, many=True).data)

    def post(self, request):
        serializer = DepartmentCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(serializer.errors, code="ValidationError", status=422)

        try:
            dept = self._service.create_department(**serializer.validated_data)
        except DomainException as e:
            return error_response(e.message, code=type(e).__name__, status=e.status_code)

        return success_response(DepartmentResponseSerializer(dept).data, status=201)


class DepartmentAgentsView(APIView):
    permission_classes = [IsHDManager]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._service = DepartmentService()

    def get(self, request, dept_id: str):
        try:
            agents = self._service.list_agents(dept_id)
        except DomainException as e:
            return error_response(e.message, code=type(e).__name__, status=e.status_code)
        return success_response(UserResponseSerializer(agents, many=True).data)
