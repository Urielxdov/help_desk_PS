import jwt
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


class JWTUser:
    """Usuario mínimo construido desde el payload del JWT externo."""

    is_authenticated = True
    is_anonymous = False

    def __init__(self, user_id, role):
        self.user_id = user_id  # int | None
        self.role = role        # str | None


class JWTAuthentication(BaseAuthentication):
    """
    Decodifica el JWT sin validar la firma.
    El token lo genera el sistema externo de usuarios.
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
