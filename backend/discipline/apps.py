from django.apps import AppConfig


class DisciplineConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "discipline"
    verbose_name = "School Discipline"

    def ready(self):  # pragma: no cover - import side-effects (signals)
        # Import autoload to register post_migrate hook for initial catalog load
        try:
            from . import autoload  # noqa: F401
        except Exception:
            # Do not crash app loading if optional autoload import fails
            pass
