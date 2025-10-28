import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("school", "0032_update_restroom_label_in_notes"),
    ]

    operations = [
        migrations.CreateModel(
            name="ExitEvent",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("date", models.DateField(db_index=True)),
                (
                    "period_number",
                    models.PositiveSmallIntegerField(blank=True, null=True),
                ),
                (
                    "reason",
                    models.CharField(
                        choices=[
                            ("admin", "إدارة"),
                            ("wing", "مشرف الجناح"),
                            ("nurse", "الممرض"),
                            ("restroom", "دورة المياه"),
                        ],
                        max_length=20,
                    ),
                ),
                ("note", models.CharField(blank=True, max_length=300)),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("returned_at", models.DateTimeField(blank=True, null=True)),
                (
                    "duration_seconds",
                    models.PositiveIntegerField(blank=True, null=True),
                ),
                (
                    "attendance_record",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="school.attendancerecord",
                    ),
                ),
                (
                    "classroom",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="school.class",
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="exit_events",
                        to="school.student",
                    ),
                ),
                (
                    "started_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="exits_started",
                        to="auth.User",
                    ),
                ),
                (
                    "returned_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="exits_returned",
                        to="auth.User",
                    ),
                ),
            ],
            options={
                "ordering": ["-started_at"],
                "verbose_name": "جلسة خروج",
                "verbose_name_plural": "جلسات خروج",
            },
        ),
        migrations.AddIndex(
            model_name="exitevent",
            index=models.Index(fields=["student", "date"], name="school_exit_student_date_idx"),
        ),
        migrations.AddIndex(
            model_name="exitevent",
            index=models.Index(fields=["reason"], name="school_exit_reason_idx"),
        ),
        migrations.AddIndex(
            model_name="exitevent",
            index=models.Index(fields=["started_at"], name="school_exit_started_at_idx"),
        ),
    ]
