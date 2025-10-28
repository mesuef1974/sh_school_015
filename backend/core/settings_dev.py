from . import settings_base as base
from .settings_base import *  # noqa: F401,F403

# Development overrides
DEBUG = True

# Allow all hosts for local development
ALLOWED_HOSTS = ["*"]

# CSRF trusted origins to support local HTTPS/HTTP on common ports
CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    # Common HTTPS dev ports (auto-selected by serve_https.ps1)
    "https://127.0.0.1:8443",
    "https://localhost:8443",
    "https://127.0.0.1:8444",
    "https://localhost:8444",
    "https://127.0.0.1:8445",
    "https://localhost:8445",
    "https://127.0.0.1:8446",
    "https://localhost:8446",
    "https://127.0.0.1:8447",
    "https://localhost:8447",
    "https://127.0.0.1:8448",
    "https://localhost:8448",
    "https://127.0.0.1:8449",
    "https://localhost:8449",
    "https://127.0.0.1:8450",
    "https://localhost:8450",
]

# Enable developer helpers (avoid duplicates and preserve order)
_base_apps = list(getattr(base, "INSTALLED_APPS", ()))
if "django_extensions" not in _base_apps:
    _base_apps.append("django_extensions")
INSTALLED_APPS = _base_apps

# CORS: allow all origins in development for simplicity
CORS_ALLOW_ALL_ORIGINS = True

# Dev-only logging: suppress benign Windows disconnect noise (WinError 10054) in Uvicorn/Django logs
# Uses Django's CallbackFilter to drop records whose exception/message mentions WinError 10054
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "ignore_winerr_10054": {
            "()": "django.utils.log.CallbackFilter",
            "callback": lambda record: not (
                (getattr(record, "exc_info", None) and record.exc_info[1] and "10054" in str(record.exc_info[1]))
                or ("10054" in record.getMessage() if hasattr(record, "getMessage") else False)
                or ("An existing connection was forcibly closed by the remote host" in record.getMessage())
            ),
        }
    },
    "formatters": {
        "simple": {"format": "%(levelname)s %(name)s: %(message)s"},
    },
    "handlers": {
        "console_win": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
            "filters": ["ignore_winerr_10054"],
        }
    },
    "loggers": {
        # Uvicorn runtime and server logs
        "uvicorn.error": {
            "handlers": ["console_win"],
            "level": "INFO",
            "propagate": False,
        },
        "uvicorn": {"handlers": ["console_win"], "level": "INFO", "propagate": False},
        # Django runserver and request logs
        "django.server": {
            "handlers": ["console_win"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console_win"],
            "level": "WARNING",
            "propagate": False,
        },
        # AsyncIO event loop warnings (Windows Proactor 10054 etc.)
        "asyncio": {
            "handlers": ["console_win"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}
