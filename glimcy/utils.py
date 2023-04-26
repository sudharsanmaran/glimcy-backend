from rest_framework.views import Response
from rest_framework.views import exception_handler
from typing import Any


def api_exception_handler(exc: Exception, context: dict[str, Any]) -> Response:
    """Custom API exception handler."""

    response = exception_handler(exc, context)

    if response is not None:
        error_payload = {
            "status_code": 0,
            "message": "",
        }
        status_code = response.status_code
        errors = []
        for key, val in response.data.items():
            if isinstance(val, str):
                errors.append(val)
            elif isinstance(val, list):
                errors.append(val[0])
        error_payload["message"] = errors
        error_payload["status_code"] = status_code
        response.data = error_payload
    return response
