from __future__ import annotations

from django.conf import settings
from django.core.checks import CheckMessage, Warning, register


@register()  # default deployment checks
def core_security_env_checks(app_configs=None, **kwargs) -> list[CheckMessage]:
    msgs: list[CheckMessage] = []

    # In production (DEBUG False), ensure security-related settings are not empty.
    if not getattr(settings, "DEBUG", False):
        # ALLOWED_HOSTS should not be empty in production
        if not getattr(settings, "ALLOWED_HOSTS", None):
            msgs.append(
                Warning(
                    "ALLOWED_HOSTS is empty in production",
                    id="core.W001",
                    hint="Set DJANGO_ALLOWED_HOSTS or configure ALLOWED_HOSTS in settings_prod.py",
                )
            )
        # CORS allowed origins recommended to be explicit (may be empty by design)
        cors = getattr(settings, "CORS_ALLOWED_ORIGINS", None)
        if cors is not None and isinstance(cors, (list, tuple)) and len(cors) == 0:
            msgs.append(
                Warning(
                    "CORS_ALLOWED_ORIGINS is empty in production",
                    id="core.W002",
                    hint=(
                        "If the frontend is hosted on a different origin, set DJANGO_CORS_ALLOWED_ORIGINS to an explicit allowlist."
                    ),
                )
            )
        # CSRF trusted origins recommended when using HTTPS and cross-subdomain frontends
        csrf = getattr(settings, "CSRF_TRUSTED_ORIGINS", None)
        if csrf is not None and isinstance(csrf, (list, tuple)) and len(csrf) == 0:
            msgs.append(
                Warning(
                    "CSRF_TRUSTED_ORIGINS is empty in production",
                    id="core.W003",
                    hint="Set DJANGO_CSRF_TRUSTED_ORIGINS to the trusted HTTPS origins (e.g., https://app.example.com)",
                )
            )
    return msgs
