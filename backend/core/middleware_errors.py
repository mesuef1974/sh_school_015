from typing import Callable

from django.http import HttpRequest, HttpResponse

try:
    from rest_framework.response import Response as DRFResponse  # type: ignore
except Exception:  # pragma: no cover
    DRFResponse = None  # type: ignore


class DRFErrorEnvelopeMiddleware:
    """
    Ensures all DRF error responses (4xx/5xx) follow the unified envelope
      { "error": { code, message, details } }
    even when views return Response(...) directly instead of raising exceptions.

    This complements core.exceptions.custom_exception_handler which handles
    exception-driven responses; this middleware handles plain Response objects
    with {"detail": "..."} payloads.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        resp = self.get_response(request)
        try:
            status_code = int(getattr(resp, "status_code", 0) or 0)
            # Case 1: DRF Response (has .data)
            if DRFResponse is not None and isinstance(resp, DRFResponse):
                data = getattr(resp, "data", None)
                if status_code >= 400 and isinstance(data, dict) and "error" not in data:
                    # Derive a code from HTTP status when no exception context exists
                    if status_code == 401:
                        code = "NOT_AUTHENTICATED"
                    elif status_code == 403:
                        code = "PERMISSION_DENIED"
                    elif 400 <= status_code < 500:
                        code = "BAD_REQUEST"
                    else:
                        code = "ERROR"
                    message = str(data.get("detail") or data.get("message") or "Error")
                    resp.data = {
                        "error": {
                            "code": code,
                            "message": message,
                            "details": data,
                        }
                    }
                    try:
                        # Re-render the DRF Response so content reflects updated data
                        resp.render()
                    except Exception:
                        pass
                    return resp
            # Case 2: Plain Django HttpResponse with JSON body {"detail": ...}
            if status_code >= 400:
                ctype = (resp.headers.get("Content-Type") or resp.get("Content-Type") or "").lower()
                if "application/json" in ctype:
                    import json

                    try:
                        raw = resp.content.decode("utf-8") if hasattr(resp, "content") else None
                        data = json.loads(raw) if raw else None
                    except Exception:
                        data = None
                    if isinstance(data, dict) and ("error" not in data) and ("detail" in data or "message" in data):
                        if status_code == 401:
                            code = "NOT_AUTHENTICATED"
                        elif status_code == 403:
                            code = "PERMISSION_DENIED"
                        elif 400 <= status_code < 500:
                            code = "BAD_REQUEST"
                        else:
                            code = "ERROR"
                        message = str(data.get("detail") or data.get("message") or "Error")
                        payload = {
                            "error": {
                                "code": code,
                                "message": message,
                                "details": data,
                            }
                        }
                        resp.content = json.dumps(payload).encode("utf-8")
                        resp.headers["Content-Type"] = "application/json"
                        return resp
        except Exception:
            # Be permissive: never break the response pipeline
            return resp
        return resp
