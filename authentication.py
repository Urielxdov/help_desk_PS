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

ROLE_LEVEL = {'user': 0, 'technician': 1, 'area_admin': 2, 'super_admin': 3}


class JWTUser:
    """
    Representación mínima del usuario construida desde el payload JWT.

    No corresponde a ningún modelo de base de datos local. Solo encapsula
    user_id y role para que las vistas y clases de permiso puedan inspeccionarlos.

    is_authenticated = True es un atributo de clase (no de instancia) que
    satisface el duck-typing que DRF requiere para considerar la petición
    como autenticada sin implementar el modelo de usuario completo de Django.

    Atributos de rol:
      real_role  — rol original del JWT; usado por las clases de permiso.
      active_role — rol temporal de override (None si no hay override).
      role       — rol efectivo: active_role si está activo, si no real_role.
                   Usado por las vistas para filtrar datos y dar forma a respuestas.
    """

    is_authenticated = True
    is_anonymous = False

    def __init__(self, user_id, real_role, active_role=None):
        self.user_id = user_id
        self.real_role = real_role
        self.active_role = active_role
        self.role = active_role if active_role else real_role


class JWTAuthentication(BaseAuthentication):
    """
    Autentica peticiones leyendo el JWT del header Authorization: Bearer <token>.

    Retorna None si el header no está presente, lo que permite a DRF continuar
    con el siguiente backend de autenticación (comportamiento estándar).
    Lanza AuthenticationFailed si el token está presente pero no puede decodificarse.

    Si el payload contiene active_role y es de menor jerarquía que role,
    se construye un JWTUser con override activo.
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

        real_role = payload.get('role')
        active_role = payload.get('active_role')

        # Solo aceptar active_role si es estrictamente menor que real_role
        if active_role and (
            ROLE_LEVEL.get(active_role, -1) >= ROLE_LEVEL.get(real_role, -1)
        ):
            active_role = None

        user = JWTUser(
            user_id=payload.get('user_id'),
            real_role=real_role,
            active_role=active_role,
        )
        return (user, token)
