from rest_framework.response import Response


def success_response(data, message: str = "OK", status: int = 200) -> Response:
    return Response({"data": data, "message": message}, status=status)


def error_response(message: str, code: str = "Error", status: int = 400) -> Response:
    return Response({"error": message, "code": code}, status=status)
