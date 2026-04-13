"""
Endpoints de autenticación — helper de desarrollo.

En producción el JWT lo genera el sistema externo de usuarios.
Este endpoint permite generar tokens localmente para pruebas.
"""
import jwt
from django.conf import settings
from django.urls import path
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

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


urlpatterns = [
    path('token/', TokenView.as_view(), name='token-obtain'),
]
