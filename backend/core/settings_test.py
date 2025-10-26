from .settings import *  # noqa

# Use fast, in-memory SQLite database for CI tests (no external Postgres required)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Speed up password hashing in tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Ensure test client hosts are accepted
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]

# Use local-memory cache to avoid external services
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "test-locmem",
    }
}

# Emails are not actually sent during tests
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
