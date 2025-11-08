from typing import Any, Dict, Optional

from rest_framework import status as drf_status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


def _normalize_error_detail(detail: Any) -> Any:
    """
    Normalize DRF error details to plain Python types suitable for JSON.
    Keeps structures (dict/list) but converts ErrorDetail objects to strings.
    """
    try:
        # DRF ErrorDetail behaves like a string
        if isinstance(detail, (str, int, float)) or detail is None:
            return detail
        if isinstance(detail, dict):
            return {k: _normalize_error_detail(v) for k, v in detail.items()}
        if isinstance(detail, list):
            return [_normalize_error_detail(x) for x in detail]
        # Fallback to string representation
        return str(detail)
    except Exception:  # pragma: no cover - defensive
        return str(detail)


def _error_code_from_exception(exc: Exception) -> str:
    # Prefer DRF's default_code when available
    code = getattr(exc, "default_code", None)
    if isinstance(code, str) and code:
        return code.upper()
    # Fallback to class name as code
    return exc.__class__.__name__.upper()


def custom_exception_handler(exc: Exception, context: Dict[str, Any]) -> Optional[Response]:
    """
    Unified API error envelope for DRF views.

    Response format:
      { "error": { "code": "SOME_CODE", "message": "...", "details": {...} } }
    
    - Preserves DRF status codes
    - Preserves DRF's default error details (normalized)
    """
    # First, let DRF generate the standard response (status code + details)
    response = drf_exception_handler(exc, context)

    if response is None:
        # Non-DRF exceptions (500 etc.) — return generic envelope
        payload = {
            "error": {
                "code": _error_code_from_exception(exc),
                "message": str(exc) or "Internal Server Error",
                "details": None,
            }
        }
        return Response(payload, status=drf_status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Build our unified envelope using DRF's generated data/status
    if isinstance(exc, (APIException, ValidationError)):
        message = ""
        if isinstance(getattr(exc, "detail", None), (list, dict)):
            # When detail is a structure, keep message short
            message = getattr(exc, "default_detail", "Validation error")
        else:
            message = str(getattr(exc, "detail", "")) or getattr(exc, "default_detail", "Error")
    else:
        message = str(exc) or "Error"

    details = _normalize_error_detail(response.data)

    payload = {
        "error": {
            "code": _error_code_from_exception(exc),
            "message": message,
            "details": details,
        }
    }

    response.data = payload
    return response