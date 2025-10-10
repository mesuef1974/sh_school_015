"""
Base Django settings for core project.
Common settings shared by all environments. Do not run this file directly;
use settings_dev.py or settings_prod.py which import from here.
"""

from pathlib import Path
import os
from datetime import timedelta
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env in backend directory
load_dotenv(os.path.join(BASE_DIR, ".env"))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret-change-me")

# SECURITY WARNING: don't run with debug turned on in production!
# DEBUG will typically be overridden in environment-specific files.
DEBUG = os.getenv("DJANGO_DEBUG", "False").lower() == "true"

# In dev allow all; in prod read comma-separated list (may be overridden per env)
ALLOWED_HOSTS = (
    ["*"]
    if DEBUG
    else [h.strip() for h in os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",") if h.strip()]
)

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
    "corsheaders",
    "django_rq",
    # Local app
    "school",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    # Serve static files efficiently in development ASGI (and prod if desired)
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# CORS settings will be defined in environment files (dev/prod)

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("PG_DB", "sh_school"),
        "USER": os.getenv("PG_USER", "postgres"),
        "PASSWORD": os.getenv("PG_PASSWORD", "postgres"),
        "HOST": os.getenv("PG_HOST", "127.0.0.1"),
        "PORT": os.getenv("PG_PORT", "5432"),
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
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

# Redirect login_required to the admin login page (we don't have /accounts/login/)
LOGIN_URL = "/admin/login/"

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
    "DEFAULT_THROTTLE_RATES": {
        "user": "2000/hour",
        "anon": "50/hour",
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Feature flags / toggles
# Hide/disable Excel imports in UI and views when True
DISABLE_IMPORTS = os.getenv("DISABLE_IMPORTS", "False").lower() == "true"

# RQ (Redis Queue) configuration for background jobs
REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
RQ_QUEUES = {
    "default": {
        "URL": REDIS_URL,
        "DEFAULT_TIMEOUT": 600,  # 10 minutes
    }
}
