import os
from contextlib import contextmanager
import pytest
from django.test import Client


@contextmanager
def env(**kwargs):
    old = {}
    for k, v in kwargs.items():
        old[k] = os.environ.get(k)
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = str(v)
    try:
        yield
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


@pytest.mark.django_db
def test_security_headers_present_on_api_path():
    c = Client()
    # Choose a representative API path that exists without auth requirement in tests; overview is OK for superuser,
    # but here we care only about headers middleware behavior on any path. We use /livez substitute via reverse proxy
    # by hitting an API-style path served by Django (schema endpoint is public).
    resp = c.get("/api/schema/")
    assert resp.status_code in (200, 204), resp.content
    # Basic headers should exist by default
    assert resp["Referrer-Policy"] in ("strict-origin-when-cross-origin", "same-origin")
    assert resp["X-Frame-Options"] in ("SAMEORIGIN", "DENY")
    assert resp["X-Content-Type-Options"] == "nosniff"
    # CSP defaults to Report-Only by default
    csp_ro = resp.get("Content-Security-Policy-Report-Only")
    assert csp_ro is not None and "default-src" in csp_ro


@pytest.mark.django_db
def test_csp_enforce_switch_on_api_path():
    with env(DJANGO_CSP_ENFORCE="true"):
        c = Client()
        resp = c.get("/api/schema/")
        assert resp.status_code in (200, 204), resp.content
        assert "Content-Security-Policy" in resp
        assert "Content-Security-Policy-Report-Only" not in resp


@pytest.mark.django_db
def test_disable_security_headers_flag_on_api_path():
    with env(DJANGO_SECURITY_HEADERS="false"):
        c = Client()
        resp = c.get("/api/schema/")
        assert resp.status_code in (200, 204), resp.content
        # Our middleware should have not enforced these headers
        assert "Referrer-Policy" not in resp or resp["Referrer-Policy"] in (
            "strict-origin-when-cross-origin",
            "same-origin",
        )
        assert "X-Frame-Options" not in resp or resp["X-Frame-Options"] in ("SAMEORIGIN", "DENY")
        assert ("X-Content-Type-Options" not in resp) or (resp["X-Content-Type-Options"] == "nosniff")
        assert "Content-Security-Policy" not in resp
        assert "Content-Security-Policy-Report-Only" not in resp
