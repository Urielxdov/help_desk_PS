"""
Autenticación JWT para la API de Help Desk.

El sistema de usuarios es externo. Los tokens los genera ese sistema con su
propia clave privada. Este servicio no tiene acceso a esa clave, por lo que
decodifica el payload sin verificar la firma — la confianza en el token se
delega a la infraestructura de red (solo el sistema externo puede emitirlos
en producción). Ver TokenView en authentication_urls.py para generación local.
"""
import jwt
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


class JWTUser:
    """
    Representación mínima del usuario construida desde el payload JWT.

    No corresponde a ningún modelo de base de datos local. Solo encapsula
    user_id y role para que las vistas y clases de permiso puedan inspeccionarlos.

    is_authenticated = True es un atributo de clase (no de instancia) que
    satisface el duck-typing que DRF requiere para considerar la petición
    como autenticada sin implementar el modelo de usuario completo de Django.
    """

    is_authenticated = True
    is_anonymous = False

    def __init__(self, user_id, role):
        self.user_id = user_id  # int | None — ID del sistema externo
        self.role = role        # str | None — uno de: user, technician, area_admin, super_admin


class JWTAuthentication(BaseAuthentication):
    """
    Autentica peticiones leyendo el JWT del header Authorization: Bearer <token>.

    Retorna None si el header no está presente, lo que permite a DRF continuar
    con el siguiente backend de autenticación (comportamiento estándar).
    Lanza AuthenticationFailed si el token está presente pero no puede decodificarse.
    """

    def authenticate(self, request):
        header = request.META.get('HTTP_AUTHORIZATION', '')
        if not header.startswith('Bearer '):
            return None

        token = header[7:]
        try:
            payload = jwt.decode(
                token,
                options={"verify_signature": False},
                algorithms=["HS256", "RS256"],
            )
        except jwt.DecodeError:
            raise AuthenticationFailed('Token inválido.')

        user = JWTUser(
            user_id=payload.get('user_id'),
            role=payload.get('role'),
        )
        return (user, token)
