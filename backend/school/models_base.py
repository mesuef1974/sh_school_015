"""
Base models and mixins for the school application
Contains: BaseModel, SoftDeleteManager, TimestampMixin
"""

from django.db import models
from django.utils import timezone


class SoftDeleteManager(models.Manager):
    """Manager that filters out soft-deleted objects"""

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class BaseModel(models.Model):
    """
    Base model for all models in the system
    Provides: timestamps, soft delete, and common functionality
    """

    created_at = models.DateTimeField(
        auto_now_add=True, db_index=True, verbose_name="تاريخ الإنشاء"
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ آخر تحديث")
    deleted_at = models.DateTimeField(
        null=True, blank=True, db_index=True, verbose_name="تاريخ الحذف"
    )

    # Default manager shows only non-deleted
    objects = SoftDeleteManager()
    # Manager that shows all including deleted
    all_objects = models.Manager()

    class Meta:
        abstract = True
        ordering = ["-created_at"]

    def delete(self, using=None, keep_parents=False, hard=False):
        """
        Soft delete by default, use hard=True for permanent deletion
        """
        if hard:
            return super().delete(using=using, keep_parents=keep_parents)
        else:
            self.deleted_at = timezone.now()
            self.save(update_fields=["deleted_at"])

    def hard_delete(self):
        """Permanently delete the object"""
        super().delete()

    def restore(self):
        """Restore a soft-deleted object"""
        self.deleted_at = None
        self.save(update_fields=["deleted_at"])

    @property
    def is_deleted(self):
        """Check if object is soft-deleted"""
        return self.deleted_at is not None


class AuditLog(models.Model):
    """
    Comprehensive audit trail for tracking all changes
    Records: who, what, when, where, and how
    """

    ACTION_CHOICES = [
        ("create", "إنشاء"),
        ("update", "تحديث"),
        ("delete", "حذف"),
        ("restore", "استعادة"),
        ("login", "تسجيل دخول"),
        ("logout", "تسجيل خروج"),
        ("export", "تصدير"),
        ("import", "استيراد"),
    ]

    user = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        verbose_name="المستخدم",
    )
    action = models.CharField(
        max_length=20, choices=ACTION_CHOICES, db_index=True, verbose_name="الإجراء"
    )
    model_name = models.CharField(max_length=100, db_index=True, verbose_name="اسم النموذج")
    object_id = models.PositiveIntegerField(null=True, blank=True, verbose_name="معرف الكائن")
    object_repr = models.CharField(max_length=200, blank=True, verbose_name="تمثيل الكائن")

    # Change details
    changes = models.JSONField(default=dict, blank=True, verbose_name="التغييرات")
    old_values = models.JSONField(default=dict, blank=True, verbose_name="القيم القديمة")
    new_values = models.JSONField(default=dict, blank=True, verbose_name="القيم الجديدة")

    # Request metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="عنوان IP")
    user_agent = models.TextField(blank=True, verbose_name="معلومات المتصفح")
    request_path = models.CharField(max_length=500, blank=True, verbose_name="مسار الطلب")
    request_method = models.CharField(max_length=10, blank=True, verbose_name="نوع الطلب")

    # Additional context
    description = models.TextField(blank=True, verbose_name="الوصف")
    extra_data = models.JSONField(default=dict, blank=True, verbose_name="بيانات إضافية")

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="الوقت")

    class Meta:
        verbose_name = "سجل تدقيق"
        verbose_name_plural = "سجلات التدقيق"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["user", "timestamp"]),
            models.Index(fields=["model_name", "object_id"]),
            models.Index(fields=["action", "timestamp"]),
            models.Index(fields=["timestamp"]),
            models.Index(fields=["ip_address", "timestamp"]),
        ]

    def __str__(self):
        user_str = self.user.username if self.user else "نظام"
        return f"{user_str} - {self.get_action_display()} - {self.model_name} - {self.timestamp}"


class DataValidationError(models.Model):
    """
    Track data validation errors for monitoring and improvement
    """

    model_name = models.CharField(max_length=100, db_index=True)
    field_name = models.CharField(max_length=100, db_index=True)
    invalid_value = models.TextField()
    error_message = models.TextField()
    user = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    resolved = models.BooleanField(default=False, db_index=True)

    class Meta:
        verbose_name = "خطأ التحقق من البيانات"
        verbose_name_plural = "أخطاء التحقق من البيانات"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["model_name", "resolved"]),
            models.Index(fields=["timestamp", "resolved"]),
        ]

    def __str__(self):
        return f"{self.model_name}.{self.field_name} - {self.timestamp}"
