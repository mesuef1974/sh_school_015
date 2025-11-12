from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):
    dependencies = [
        ("school", "0039_periodtemplate_classes"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ApprovalRequest",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("resource_type", models.CharField(db_index=True, max_length=50)),
                ("resource_id", models.CharField(db_index=True, max_length=64)),
                ("action", models.CharField(help_text="نوع الإجراء المطلوب", max_length=50)),
                ("irreversible", models.BooleanField(default=False)),
                (
                    "impact",
                    models.CharField(blank=True, default="", help_text="low|medium|high|critical", max_length=20),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "قيد الانتظار"),
                            ("approved", "مقبول"),
                            ("rejected", "مرفوض"),
                            ("executed", "تم التنفيذ"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("justification", models.CharField(blank=True, default="", max_length=500)),
                ("payload", models.JSONField(blank=True, help_text="بيانات إضافية لازمة للتنفيذ", null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "approved_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.SET_NULL,
                        related_name="approvals_approved",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "executed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.SET_NULL,
                        related_name="approvals_executed",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "proposed_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=models.SET_NULL,
                        related_name="approvals_proposed",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "طلب موافقة",
                "verbose_name_plural": "طلبات الموافقة",
            },
        ),
        migrations.AddIndex(
            model_name="approvalrequest",
            index=models.Index(fields=["resource_type", "resource_id"], name="school_appr_resource_idx"),
        ),
        migrations.AddIndex(
            model_name="approvalrequest",
            index=models.Index(fields=["status", "created_at"], name="school_appr_status_created_idx"),
        ),
    ]
