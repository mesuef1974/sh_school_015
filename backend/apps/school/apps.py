from django.apps import AppConfig


class SchoolConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.school"
    # اسم التطبيق كما يظهر في لوحة الإدارة
    verbose_name = "المدرسة"
