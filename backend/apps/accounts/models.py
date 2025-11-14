from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLES = (
        ("admin", "أدمن"),
        ("teacher", "معلم"),
        ("student", "طالب"),
        ("parent", "ولي أمر"),
    )

    role = models.CharField(max_length=10, choices=ROLES)
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)

    class Meta:
        # تعريب مسميات نموذج المستخدم في لوحة الإدارة
        verbose_name = "مستخدم"
        verbose_name_plural = "مستخدمون"

    # اعرض اسم الموظف الكامل دائمًا إن توفر، بدل اسم المستخدم
    def __str__(self) -> str:  # pragma: no cover - تمثيل للعرض فقط
        try:
            # إذا كان لهذا المستخدم سجل Staff مرتبط، نُرجع الاسم الكامل للموظف كما هو بدون تقطيع
            staff = getattr(self, "staff", None)
            if staff and getattr(staff, "full_name", None):
                return str(staff.full_name)
        except Exception:
            pass
        # محاولة استخدام الاسم الكامل للمستخدم (first_name + last_name)
        try:
            full = self.get_full_name()
            if full:
                return full
        except Exception:
            pass
        # رجوع إلى اسم المستخدم عند عدم توفر أي من السابق
        return str(getattr(self, "username", ""))
