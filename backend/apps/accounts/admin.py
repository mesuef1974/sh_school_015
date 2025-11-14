from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.admin.sites import AlreadyRegistered
from .models import User


class UserAdmin(DjangoUserAdmin):
    # أضف عمودًا يظهر الاسم الكامل دائمًا (موظف/مستخدم)
    list_display = (
        "id",
        "username",
        "full_name_display",
        "email",
        "role",
        "is_staff",
        "is_active",
    )
    list_filter = ("is_staff", "is_superuser", "is_active", "role")
    search_fields = ("username", "first_name", "last_name", "email")

    def full_name_display(self, obj: User) -> str:
        try:
            staff = getattr(obj, "staff", None)
            if staff and getattr(staff, "full_name", None):
                return str(staff.full_name)
        except Exception:
            pass
        fn = obj.get_full_name() or ""
        return fn if fn else obj.username

    full_name_display.short_description = "الاسم الكامل"


# سجّل لوحة المستخدم فقط إذا لم تكن مُسجّلة مسبقًا (لتجنب التعارض مع تسجيلات أخرى مثل school.admin)
try:
    if not admin.site.is_registered(User):
        admin.site.register(User, UserAdmin)
except AlreadyRegistered:
    # في حال قام تطبيق آخر بالتسجيل، نتجاهل التسجيل هنا
    pass
