# Recreate TimetableEntry model after prior drop
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("school", "0009_drop_timetable_entry"),
    ]

    operations = [
        migrations.CreateModel(
            name="TimetableEntry",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "classroom",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="timetable_entries",
                        to="school.class",
                    ),
                ),
                (
                    "day",
                    models.CharField(max_length=10, help_text="Sun, Mon, Tue, Wed, Thu"),
                ),
                (
                    "slot",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="timetable_entries",
                        to="school.calendarslot",
                    ),
                ),
                (
                    "subject",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="school.subject"),
                ),
                (
                    "teacher",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="school.staff"),
                ),
            ],
            options={
                "verbose_name": "حصة مجدولة",
                "verbose_name_plural": "حصص مجدولة",
                "indexes": [
                    models.Index(fields=["classroom", "day"], name="tt_class_day_idx"),
                    models.Index(fields=["slot"], name="tt_slot_idx"),
                    models.Index(fields=["teacher"], name="tt_teacher_idx"),
                ],
                "unique_together": {("classroom", "day", "slot")},
            },
        ),
    ]
