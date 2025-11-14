from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    # اسم التطبيق كما يظهر في لوحة الإدارة
    verbose_name = "الحسابات"
