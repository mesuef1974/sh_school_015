from django.apps import AppConfig


class DisciplineConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    # Use the full dotted path so Django can locate the app when modules are imported as
    # "backend.discipline.*" (pytest adds the backend directory to sys.path).
    # The app label remains "discipline" (last component), which keeps permissions and
    # ContentType names stable.
    name = "backend.discipline"
    # اسم التطبيق كما يظهر في لوحة الإدارة
    verbose_name = "الانضباط المدرسي"

    def ready(self):  # pragma: no cover - import side-effects (signals)
        # Import autoload to register post_migrate hook for initial catalog load
        try:
            from . import autoload  # noqa: F401
        except Exception:
            # Do not crash app loading if optional autoload import fails
            pass
