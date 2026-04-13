from rest_framework.views import exception_handler as drf_exception_handler


def custom_exception_handler(exc, context):
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
