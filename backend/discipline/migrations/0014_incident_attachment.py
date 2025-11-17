from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):
    dependencies = [
        ("discipline", "0013_merge_20251115_2320"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="IncidentAttachment",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("kind", models.CharField(default="other", max_length=32)),
                ("file", models.FileField(upload_to="incidents/%Y/%m/")),
                ("mime", models.CharField(blank=True, max_length=64)),
                ("size", models.IntegerField(default=0)),
                ("sha256", models.CharField(blank=True, max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("meta", models.JSONField(blank=True, default=dict)),
                (
                    "incident",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE, related_name="attachments", to="discipline.incident"
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True, null=True, on_delete=models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL
                    ),
                ),
            ],
            options={
                "verbose_name": "مرفق واقعة",
                "verbose_name_plural": "مرفقات الوقائع",
                "ordering": ("-created_at", "-id"),
                "permissions": (
                    ("incident_attachment_view", "Can view incident attachments"),
                    ("incident_attachment_upload", "Can upload incident attachments"),
                ),
            },
        ),
        migrations.AddIndex(
            model_name="incidentattachment",
            index=models.Index(fields=["incident", "created_at"], name="inc_att_inc_dt_idx"),
        ),
        migrations.AddIndex(
            model_name="incidentattachment",
            index=models.Index(fields=["kind"], name="inc_att_kind_idx"),
        ),
    ]
