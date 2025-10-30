import os
from contextlib import contextmanager
from django.test import Client, override_settings


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


def test_security_headers_present_on_livez(db):
    c = Client()
    resp = c.get("/livez")
    # Basic headers should exist by default
    assert resp["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert resp["X-Frame-Options"] == "SAMEORIGIN"
    assert resp["X-Content-Type-Options"] == "nosniff"
    # CSP defaults to Report-Only by default
    csp_ro = resp.get("Content-Security-Policy-Report-Only")
    assert csp_ro is not None and "default-src" in csp_ro


def test_csp_enforce_switch(db):
    # When DJANGO_CSP_ENFORCE=true, header should be Content-Security-Policy
    with env(DJANGO_CSP_ENFORCE="true"):
        c = Client()
        resp = c.get("/livez")
        assert "Content-Security-Policy" in resp
        assert "Content-Security-Policy-Report-Only" not in resp


def test_disable_security_headers_flag(db):
    # When DJANGO_SECURITY_HEADERS=false, headers should not be set (except those from Django defaults)
    with env(DJANGO_SECURITY_HEADERS="false"):
        c = Client()
        resp = c.get("/livez")
        assert "Referrer-Policy" not in resp
        assert "X-Frame-Options" not in resp or resp["X-Frame-Options"] == "DENY" or resp["X-Frame-Options"] == "SAMEORIGIN"
        assert "X-Content-Type-Options" not in resp
        assert "Content-Security-Policy" not in resp
        assert "Content-Security-Policy-Report-Only" not in resp