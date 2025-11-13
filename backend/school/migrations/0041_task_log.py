from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):
    dependencies = [
        ("school", "0040_approval_request"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="TaskLog",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("resource_type", models.CharField(db_index=True, max_length=50)),
                ("resource_id", models.CharField(db_index=True, max_length=64)),
                ("action", models.CharField(max_length=50)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("open", "مفتوحة"),
                            ("in_progress", "قيد التنفيذ"),
                            ("done", "منجزة"),
                            ("canceled", "ملغاة"),
                        ],
                        db_index=True,
                        default="open",
                        max_length=20,
                    ),
                ),
                ("actor_role", models.CharField(blank=True, default="", max_length=50)),
                ("message", models.CharField(blank=True, default="", max_length=300)),
                ("payload", models.JSONField(blank=True, null=True)),
                ("due_at", models.DateTimeField(blank=True, null=True)),
                ("trace_id", models.CharField(blank=True, default="", max_length=64)),
                ("request_id", models.CharField(blank=True, default="", max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.SET_NULL,
                        related_name="tasklog_actor",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "assignee",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.SET_NULL,
                        related_name="tasklog_assignee",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "سجل مهمة",
                "verbose_name_plural": "سجلات المهام",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="tasklog",
            index=models.Index(fields=["resource_type", "resource_id"], name="task_resource_idx"),
        ),
        migrations.AddIndex(
            model_name="tasklog",
            index=models.Index(fields=["assignee", "status"], name="task_assignee_status_idx"),
        ),
        migrations.AddIndex(
            model_name="tasklog",
            index=models.Index(fields=["status", "created_at"], name="task_status_created_idx"),
        ),
        migrations.AddIndex(
            model_name="tasklog",
            index=models.Index(fields=["actor", "created_at"], name="task_actor_created_idx"),
        ),
    ]
