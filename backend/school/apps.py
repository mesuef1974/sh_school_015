from django.apps import AppConfig


class SchoolConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "school"

    def ready(self):  # noqa: D401
        # Import signal handlers
        try:
            from . import signals  # noqa: F401
        except Exception:
            # Avoid breaking migrations if import errors occur during app loading
            pass
