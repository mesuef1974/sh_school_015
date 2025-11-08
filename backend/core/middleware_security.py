import os
from typing import Callable
from django.http import HttpRequest, HttpResponse


class SecurityHeadersMiddleware:
    """
    Adds basic security headers. CSP is applied in Report-Only mode by default and
    can be enforced via environment variable DJANGO_CSP_ENFORCE=true.

    All headers can be disabled by setting DJANGO_SECURITY_HEADERS=false.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response
        self.enabled = os.getenv("DJANGO_SECURITY_HEADERS", "true").lower() != "false"
        # CSP
        self.csp = os.getenv(
            "DJANGO_CSP",
            "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:; connect-src 'self' https: http:; frame-ancestors 'self'",
        )
        self.csp_enforce = os.getenv("DJANGO_CSP_ENFORCE", "false").lower() == "true"
        # Referrer Policy
        self.referrer = os.getenv("DJANGO_REFERRER_POLICY", "strict-origin-when-cross-origin")
        # X-Frame-Options
        self.xfo = os.getenv("DJANGO_X_FRAME_OPTIONS", "SAMEORIGIN")
        # X-Content-Type-Options
        self.xcto = os.getenv("DJANGO_X_CONTENT_TYPE_OPTIONS", "nosniff")

    def __call__(self, request: HttpRequest) -> HttpResponse:
        resp = self.get_response(request)
        # Re-evaluate the enable flag per-request so tests (and runtime) can toggle via env dynamically
        enabled_now = os.getenv("DJANGO_SECURITY_HEADERS", "true").lower() != "false"
        if not enabled_now:
            # Ensure removal of any security headers possibly set by upstream middleware
            headers = (
                "Referrer-Policy",
                "X-Frame-Options",
                "X-Content-Type-Options",
                "Content-Security-Policy",
                "Content-Security-Policy-Report-Only",
            )
            # Try modern HeadersMapping API first
            try:
                for h in headers:
                    if hasattr(resp, "headers"):
                        try:
                            resp.headers.pop(h, None)  # type: ignore[attr-defined]
                        except Exception:
                            pass
            except Exception:
                pass
            # Fallback to dict-style deletion
            for h in headers:
                try:
                    if h in resp:
                        del resp[h]
                except Exception:
                    try:
                        resp[h] = None  # type: ignore[index]
                    except Exception:
                        pass
            return resp
        # CSP
        if self.csp:
            header = "Content-Security-Policy" if self.csp_enforce else "Content-Security-Policy-Report-Only"
            resp[header] = self.csp
        # Other headers
        if self.referrer:
            resp["Referrer-Policy"] = self.referrer
        if self.xfo:
            resp["X-Frame-Options"] = self.xfo
        if self.xcto:
            resp["X-Content-Type-Options"] = self.xcto
        return resp