"""
Base Django settings for core project.
Common settings shared by all environments. Do not run this file directly;
use settings_dev.py or settings_prod.py which import from here.
"""

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env in backend directory (allow opting out)
if os.getenv("DJANGO_READ_DOTENV", "1").lower() in {"1", "true", "yes", "on"}:
    load_dotenv(os.path.join(BASE_DIR, ".env"))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret-change-me")

# SECURITY WARNING: don't run with debug turned on in production!
# DEBUG will typically be overridden in environment-specific files.
DEBUG = os.getenv("DJANGO_DEBUG", "False").lower() == "true"

# In dev allow all; in prod read comma-separated list (may be overridden per env)
ALLOWED_HOSTS = ["*"] if DEBUG else [h.strip() for h in os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",") if h.strip()]

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "drf_spectacular",
    "corsheaders",
    "django_rq",
    "rest_framework_simplejwt.token_blacklist",
    # Local apps
    "school",
    "apps.attendance",
    "discipline",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    # Serve static files efficiently in development ASGI (and prod if desired)
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    # LocaleMiddleware must be after SessionMiddleware and before CommonMiddleware
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Ensure DRF error responses are wrapped in the unified envelope even when views return Response({...}, status=403)
    "core.middleware_errors.DRFErrorEnvelopeMiddleware",
    "core.middleware_security.SecurityHeadersMiddleware",
]

# CORS settings
# Allow credentials by default so HttpOnly refresh tokens can be used across same-site or whitelisted origins.
CORS_ALLOW_CREDENTIALS = True
# Origins are defined per-environment:
# - In development: see settings_dev.py (explicit localhost:5173 etc.)
# - In production: see settings_prod.py (DJANGO_CORS_ALLOWED_ORIGINS)

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            # Project-level templates (e.g., admin overrides)
            (BASE_DIR / "templates").as_posix(),
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"

# Optional Sentry integration (no-op if SENTRY_DSN is not set or package missing)
_SENTRY_DSN = os.getenv("SENTRY_DSN", "").strip()
if _SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration

        sentry_sdk.init(
            dsn=_SENTRY_DSN,
            integrations=[DjangoIntegration()],
            environment=os.getenv("SENTRY_ENV", "production" if not DEBUG else "development"),
            traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.0")),
            send_default_pii=False,
        )
    except Exception:
        # Silently ignore if Sentry isn't available in this environment
        pass

# Database
# Support DATABASE_URL, or fall back to PG_* variables, then DB_* variables, then sane local defaults.
from urllib.parse import urlparse


def _db_from_env() -> dict:
    """
    Build DATABASES["default"] from environment variables.
    Priority:
      1) DATABASE_URL (supports postgres[ql] and sqlite schemes)
      2) PG_* or DB_* variables (Postgres)
      3) Sensible defaults: in DEBUG -> SQLite (backend/db.sqlite3), else Postgres.
    """
    url = os.getenv("DATABASE_URL", "").strip()
    if url:
        u = urlparse(url)
        scheme = (u.scheme or "").lower()
        if scheme in {"sqlite", "sqlite3"}:
            # Examples:
            #   sqlite:///:memory:
            #   sqlite:///relative/path.db
            #   sqlite:////absolute/path.db
            path = u.path or ""
            if path in {"", "/"}:
                name = ":memory:"
            else:
                # urlparse adds a leading '/'; remove only one for relative paths
                if path.startswith("///"):
                    # sqlite:////C:/path -> urlparse path '///C:/path'
                    name = path.lstrip("/")
                else:
                    name = path[1:] if path.startswith("/") else path
            return {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": name,
            }
        # Treat any other/unknown scheme as Postgres-compatible
        engine = "django.db.backends.postgresql"
        name = u.path.lstrip("/") or os.getenv("DB_NAME") or os.getenv("PG_DB") or "sh_school"
        user = u.username or os.getenv("DB_USER") or os.getenv("PG_USER") or "postgres"
        password = u.password or os.getenv("DB_PASSWORD") or os.getenv("PG_PASSWORD") or "postgres"
        host = u.hostname or os.getenv("DB_HOST") or os.getenv("PG_HOST") or "127.0.0.1"
        port_val = u.port or os.getenv("DB_PORT") or os.getenv("PG_PORT") or "5432"
        port = str(port_val)
        return {
            "ENGINE": engine,
            "NAME": name,
            "USER": user,
            "PASSWORD": password,
            "HOST": host,
            "PORT": port,
        }

    # No DATABASE_URL -> use PG_* then DB_* if provided; otherwise default
    pg_db = os.getenv("PG_DB") or os.getenv("DB_NAME")
    pg_user = os.getenv("PG_USER") or os.getenv("DB_USER")
    pg_password = os.getenv("PG_PASSWORD") or os.getenv("DB_PASSWORD")
    pg_host = os.getenv("PG_HOST") or os.getenv("DB_HOST")
    pg_port = os.getenv("PG_PORT") or os.getenv("DB_PORT")

    if any([pg_db, pg_user, pg_password, pg_host, pg_port]):
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": pg_db or "sh_school",
            "USER": pg_user or "postgres",
            "PASSWORD": pg_password or "postgres",
            "HOST": pg_host or "127.0.0.1",
            "PORT": str(pg_port or "5432"),
        }

    # Sensible default: use PostgreSQL unless explicitly overridden via DJANGO_DEFAULT_DB or DATABASE_URL.
    default_engine = os.getenv("DJANGO_DEFAULT_DB", "postgres").lower()
    if default_engine in {"sqlite", "sqlite3"}:
        name = os.getenv("SQLITE_NAME") or str(BASE_DIR / "db.sqlite3")
        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": name,
        }
    # Default to Postgres
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "sh_school",
        "USER": "postgres",
        "PASSWORD": "postgres",
        "HOST": "127.0.0.1",
        "PORT": "5432",
    }


DATABASES = {"default": _db_from_env()}


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
# Default UI language: Arabic (RTL). English remains available via language switcher.
LANGUAGE_CODE = "ar"
LANGUAGES = (
    ("ar", "Arabic"),
    ("en", "English"),
)
# Custom project translation files location (for any strings we mark with gettext)
LOCALE_PATHS = [
    (BASE_DIR / "locale").as_posix(),
]
# Use local timezone for Saudi Arabia so admin and API-localized outputs reflect correct local time
TIME_ZONE = "Asia/Riyadh"
USE_I18N = True
# Keep timezone-aware datetimes; DB stores UTC while Django converts to TIME_ZONE for display
USE_TZ = True

# Static files
STATIC_URL = "static/"
# Include the top-level 'assets' directory so we can reference branding files via {% static %}
STATICFILES_DIRS = [
    # BASE_DIR points to backend/, so assets live one level up
    (BASE_DIR.parent / "assets").as_posix(),
]

# WhiteNoise: In development, use staticfiles finders (no collectstatic needed)
if DEBUG:
    WHITENOISE_USE_FINDERS = True

# Unified auth URLs
# Redirect login_required to the unified login page
LOGIN_URL = "/accounts/login/"
# After successful login, redirect users to the role-based portal home ("/") unless ?next= is provided
LOGIN_REDIRECT_URL = "/"

# REST Framework & JWT
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        # Always support JWT
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        # In development, also enable SessionAuthentication so the DRF browsable API can be used via login
        *(() if not DEBUG else ("rest_framework.authentication.SessionAuthentication",)),
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.DjangoModelPermissions",),
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.AnonRateThrottle",
    ),
    # In DEBUG we relax throttle rates drastically to avoid developer lockouts
    # because throttle state is stored in Redis and persists across restarts.
    "DEFAULT_THROTTLE_RATES": {
        "user": ("1000/second" if DEBUG else "2000/hour"),
        "anon": ("1000/second" if DEBUG else "50/hour"),
    },
    # Pagination defaults for stable list responses
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    # OpenAPI schema generation
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # Unified error responses
    "EXCEPTION_HANDLER": "core.exceptions.custom_exception_handler",
    # DRF DateField output format: Always ISO for API stability
    # Accept inputs from UI (DD/MM/YYYY) and ISO (YYYY-MM-DD)
    "DATE_FORMAT": "%Y-%m-%d",
    "DATE_INPUT_FORMATS": [
        "%Y-%m-%d",  # ISO date
        "%d/%m/%Y",  # UI format
    ],
}

# Global human-facing date/time formats for Django templates/admin (not affecting DRF JSON)
# This ensures dates render as DD/MM/YYYY in server-rendered pages and admin.
DATE_FORMAT = "d/m/Y"
SHORT_DATE_FORMAT = "d/m/Y"
DATETIME_FORMAT = "d/m/Y H:i"
SHORT_DATETIME_FORMAT = "d/m/Y H:i"

# OpenAPI/Swagger (drf-spectacular)
SPECTACULAR_SETTINGS = {
    "TITLE": os.getenv("OPENAPI_TITLE", "School API"),
    "DESCRIPTION": os.getenv("OPENAPI_DESCRIPTION", "School management API documentation"),
    "VERSION": os.getenv("OPENAPI_VERSION", "1.0.0"),
    # Do not include the schema JSON inside the Swagger served view
    "SERVE_INCLUDE_SCHEMA": False,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": False,
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# Refresh cookie settings (used by school.auth views)
SIMPLE_JWT_REFRESH_COOKIE_NAME = os.getenv("SIMPLE_JWT_REFRESH_COOKIE_NAME", "refresh_token")
SIMPLE_JWT_REFRESH_COOKIE_SAMESITE = os.getenv("SIMPLE_JWT_REFRESH_COOKIE_SAMESITE", "Lax")
SIMPLE_JWT_REFRESH_COOKIE_SECURE = os.getenv("SIMPLE_JWT_REFRESH_COOKIE_SECURE", "True").lower() == "true"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Feature flags / toggles
# Hide/disable Excel imports in UI and views when True
DISABLE_IMPORTS = os.getenv("DISABLE_IMPORTS", "False").lower() == "true"
# Enable serving/redirecting to the new SPA frontend when ready (kept False by default for safety)
FRONTEND_SPA_ENABLED = os.getenv("FRONTEND_SPA_ENABLED", "False").lower() == "true"

# RQ (Redis Queue) configuration for background jobs
REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
RQ_QUEUES = {
    "default": {
        "URL": REDIS_URL,
        "DEFAULT_TIMEOUT": 600,  # 10 minutes
    }
}

# Django Cache Configuration (using Redis)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "db": "1",  # Use DB 1 for cache (DB 0 is for RQ)
        },
        "KEY_PREFIX": "sh_school",
        "TIMEOUT": 300,  # 5 minutes default
        "VERSION": 1,
    },
    # Separate cache for long-lived data (classes, subjects, terms)
    "long_term": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "db": "2",
        },
        "KEY_PREFIX": "sh_school_lt",
        "TIMEOUT": 3600,  # 1 hour
    },
    # Cache for attendance data (medium duration)
    "attendance": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "db": "3",
        },
        "KEY_PREFIX": "sh_school_att",
        "TIMEOUT": 600,  # 10 minutes
    },
}

# --- Discipline module configurable policies (can be overridden via environment) ---
# Review SLA in hours (time allowed for wing supervisor review after submit)
DISCIPLINE_REVIEW_SLA_H = int(os.getenv("DISCIPLINE_REVIEW_SLA_H", "24"))
# Guardian notification SLA in hours (time allowed to notify guardians after submit)
DISCIPLINE_NOTIFY_SLA_H = int(os.getenv("DISCIPLINE_NOTIFY_SLA_H", "48"))
# Repeat policy window in days (look-back window for counting repeats of the same violation by the same student)
DISCIPLINE_REPEAT_WINDOW_D = int(os.getenv("DISCIPLINE_REPEAT_WINDOW_D", "30"))
# Number of prior incidents within the window that should trigger automatic escalation
DISCIPLINE_REPEAT_THRESHOLD = int(os.getenv("DISCIPLINE_REPEAT_THRESHOLD", "2"))
# When repeat threshold is met on submit, automatically bump severity by 1 (max 4)
DISCIPLINE_AUTO_ESCALATE_SEVERITY = os.getenv("DISCIPLINE_AUTO_ESCALATE_SEVERITY", "true").lower() == "true"
# In some imported dev databases, the user id that created incidents may differ from the
# current user's id although the username matches. Enable a safe dev-mode fallback to
# match "my incidents" by username as well.
DISCIPLINE_MATCH_MINE_BY_USERNAME = os.getenv("DISCIPLINE_MATCH_MINE_BY_USERNAME", str(DEBUG).lower()).lower() in {
    "1",
    "true",
    "yes",
    "on",
}
