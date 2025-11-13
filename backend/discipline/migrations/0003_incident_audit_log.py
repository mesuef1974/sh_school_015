from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("discipline", "0002_pad_violation_codes"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="IncidentAuditLog",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                (
                    "incident",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="audit_logs",
                        to="discipline.incident",
                    ),
                ),
                ("action", models.CharField(max_length=32)),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                ("at", models.DateTimeField(auto_now_add=True)),
                ("from_status", models.CharField(blank=True, max_length=16)),
                ("to_status", models.CharField(blank=True, max_length=16)),
                ("note", models.TextField(blank=True)),
                ("client_ip", models.CharField(blank=True, max_length=64)),
                ("meta", models.JSONField(blank=True, default=dict)),
            ],
            options={
                "verbose_name": "Incident Audit Log",
                "verbose_name_plural": "Incident Audit Logs",
                "ordering": ("-at", "-id"),
            },
        ),
        migrations.AddIndex(
            model_name="incidentauditlog",
            index=models.Index(fields=["incident", "at"], name="incident_audit_idx"),
        ),
        migrations.AddIndex(
            model_name="incidentauditlog",
            index=models.Index(fields=["action"], name="incident_audit_action_idx"),
        ),
    ]
