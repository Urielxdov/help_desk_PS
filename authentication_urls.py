"""
Endpoints de autenticación — helper de desarrollo.

En producción el JWT lo genera el sistema externo de usuarios.
Este endpoint permite generar tokens localmente para pruebas.
"""
import jwt
from django.conf import settings
from django.urls import path
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication import ROLE_LEVEL

VALID_ROLES = ('user', 'technician', 'area_admin', 'super_admin')


class TokenView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        user_id = request.data.get('user_id')
        role = request.data.get('role')

        if role and role not in VALID_ROLES:
            return Response(
                {'error': f'Rol inválido. Opciones: {", ".join(VALID_ROLES)}'},
                status=400,
            )

        payload = {'user_id': user_id, 'role': role}
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
        return Response({'access': token})


class SwitchRoleView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        real_role = getattr(request.user, 'real_role', None)
        active_role = request.data.get('active_role')

        if active_role is not None:
            if active_role not in VALID_ROLES:
                return Response(
                    {'error': f'Rol inválido. Opciones: {", ".join(VALID_ROLES)}'},
                    status=400,
                )
            if ROLE_LEVEL.get(active_role, -1) >= ROLE_LEVEL.get(real_role, -1):
                return Response(
                    {'error': 'Solo puedes activar un rol de menor jerarquía al tuyo.'},
                    status=400,
                )

        payload = {
            'user_id': request.user.user_id,
            'role': real_role,
        }
        if active_role is not None:
            payload['active_role'] = active_role

        token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
        return Response({
            'token': token,
            'role': real_role,
            'active_role': active_role,
        })


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            'user_id': request.user.user_id,
            'role': getattr(request.user, 'real_role', None),
            'active_role': getattr(request.user, 'active_role', None),
        })


urlpatterns = [
    path('token/', TokenView.as_view(), name='token-obtain'),
    path('switch-role/', SwitchRoleView.as_view(), name='switch-role'),
    path('me/', MeView.as_view(), name='me'),
]
