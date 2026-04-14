"""
Manejador de excepciones centralizado para la API.

Normaliza todos los errores al formato uniforme:
    {"error": "descripción legible", "code": "NombreDeExcepción"}

Esto permite a los clientes manejar errores de forma predecible sin importar
si provienen de validación, autenticación o permisos. El campo 'code' expone
el nombre de la clase de excepción y puede usarse en el frontend para
lógica de reintentos o mensajes específicos por tipo de error.
"""
from rest_framework.views import exception_handler as drf_exception_handler


def custom_exception_handler(exc, context):
    """
    Convierte la respuesta estándar de DRF al formato uniforme de error.

    DRF puede retornar errores en distintos shapes según el tipo de excepción:
    - {'detail': ...}       para errores de autenticación y permisos
    - {'campo': [...]}      para errores de validación por campo
    - [...]                 para errores de validación en lista

    Todos se normalizan a una sola cadena legible en 'error'.
    Si response es None, la excepción no fue manejada por DRF y se deja
    propagar al servidor (resultará en HTTP 500).
    """
    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    if isinstance(response.data, dict) and 'detail' in response.data:
        message = str(response.data['detail'])
    elif isinstance(response.data, list):
        message = '; '.join(str(e) for e in response.data)
    elif isinstance(response.data, dict):
        parts = []
        for field, errors in response.data.items():
            if isinstance(errors, list):
                parts.append(f"{field}: {', '.join(str(e) for e in errors)}")
            else:
                parts.append(f"{field}: {errors}")
        message = '; '.join(parts)
    else:
        message = str(response.data)

    response.data = {
        'error': message,
        'code': type(exc).__name__,
    }
    return response
