from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from shared.permissions import IsAdmin
from shared.responses import success_response, error_response
from shared.exceptions import DomainException
from ..services import UserService
from .serializers import UserCreateSerializer, UserUpdateSerializer, UserResponseSerializer


class UserViewSet(ViewSet):
    """
    list:   GET  /api/v1/users/
    create: POST /api/v1/users/
    retrieve: GET /api/v1/users/{pk}/
    partial_update: PATCH /api/v1/users/{pk}/
    destroy: DELETE /api/v1/users/{pk}/
    """

    def get_permissions(self):
        return [IsAdmin()]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._service = UserService()

    def list(self, request):
        users = self._service.list_users()
        return success_response(UserResponseSerializer(users, many=True).data)

    def create(self, request):
        serializer = UserCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(serializer.errors, code='ValidationError', status=422)
        try:
            user = self._service.create_user(**serializer.validated_data)
        except DomainException as e:
            return error_response(e.message, code=type(e).__name__, status=e.status_code)
        return success_response(UserResponseSerializer(user).data, status=201)

    def retrieve(self, request, pk=None):
        try:
            user = self._service.get_user(pk)
        except DomainException as e:
            return error_response(e.message, code=type(e).__name__, status=e.status_code)
        return success_response(UserResponseSerializer(user).data)

    def partial_update(self, request, pk=None):
        serializer = UserUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(serializer.errors, code='ValidationError', status=422)
        try:
            user = self._service.update_user(pk, **serializer.validated_data)
        except DomainException as e:
            return error_response(e.message, code=type(e).__name__, status=e.status_code)
        return success_response(UserResponseSerializer(user).data)

    def destroy(self, request, pk=None):
        try:
            self._service.delete_user(
                user_id=pk,
                requesting_role=getattr(request.user, 'role', ''),
            )
        except DomainException as e:
            return error_response(e.message, code=type(e).__name__, status=e.status_code)
        return success_response(None, message='Usuario eliminado')
