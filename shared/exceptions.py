from rest_framework.views import exception_handler
from rest_framework.response import Response


class DomainException(Exception):
    status_code = 400
    default_message = "Error de dominio"

    def __init__(self, message: str = None):
        self.message = message or self.default_message
        super().__init__(self.message)


class NotFoundError(DomainException):
    status_code = 404
    default_message = "Recurso no encontrado"


class ForbiddenError(DomainException):
    status_code = 403
    default_message = "Sin permisos suficientes"


class ConflictError(DomainException):
    status_code = 409
    default_message = "Conflicto con el estado actual"


class ValidationError(DomainException):
    status_code = 422
    default_message = "Datos inválidos"


def custom_exception_handler(exc, context):
    if isinstance(exc, DomainException):
        return Response(
            {"error": exc.message, "code": type(exc).__name__},
            status=exc.status_code,
        )
    return exception_handler(exc, context)
