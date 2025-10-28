import os

from .settings_base import *  # noqa

# Production overrides
DEBUG = False

# Hosts and CSRF trusted origins from environment
# Expected env:
#   DJANGO_ALLOWED_HOSTS="example.com,.example.org"
#   DJANGO_CSRF_TRUSTED_ORIGINS="https://example.com,https://admin.example.com"
ALLOWED_HOSTS = [h.strip() for h in os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",") if h.strip()]

CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]

# CORS: whitelist origins from env (empty by default)
#   DJANGO_CORS_ALLOWED_ORIGINS="https://app.example.com,https://admin.example.com"
CORS_ALLOWED_ORIGINS = [o.strip() for o in os.getenv("DJANGO_CORS_ALLOWED_ORIGINS", "").split(",") if o.strip()]

# Security hardening
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = int(os.getenv("DJANGO_SECURE_HSTS_SECONDS", "31536000"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Optionally set secure proxy SSL header if behind a reverse proxy that sets X-Forwarded-Proto
# from django.conf import settings as _settings  # noqa: F401
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
