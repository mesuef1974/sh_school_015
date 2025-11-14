from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.api"
    # اسم التطبيق كما يظهر في لوحة الإدارة
    verbose_name = "واجهات برمجة التطبيقات"
