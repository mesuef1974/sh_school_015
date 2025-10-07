from django.db import migrations, models
import django.db.models


class Migration(migrations.Migration):

    dependencies = [
        ("school", "0014_backfill_class_students_count"),
    ]

    operations = [
        # Student indexes
        migrations.AddIndex(
            model_name="student",
            index=models.Index(fields=["class_fk"], name="student_class_idx"),
        ),
        migrations.AddIndex(
            model_name="student",
            index=models.Index(fields=["active"], name="student_active_idx"),
        ),
        migrations.AddIndex(
            model_name="student",
            index=models.Index(fields=["needs"], name="student_needs_idx"),
        ),
        migrations.AddIndex(
            model_name="student",
            index=models.Index(fields=["nationality"], name="student_nationality_idx"),
        ),
        migrations.AddIndex(
            model_name="student",
            index=models.Index(fields=["grade_label"], name="student_grade_label_idx"),
        ),
        migrations.AddIndex(
            model_name="student",
            index=models.Index(fields=["section_label"], name="student_section_label_idx"),
        ),
        # Staff indexes
        migrations.AddIndex(
            model_name="staff",
            index=models.Index(fields=["role"], name="staff_role_idx"),
        ),
        migrations.AddIndex(
            model_name="staff",
            index=models.Index(fields=["user"], name="staff_user_idx"),
        ),
        migrations.AddIndex(
            model_name="staff",
            index=models.Index(fields=["email"], name="staff_email_idx"),
        ),
        migrations.AddIndex(
            model_name="staff",
            index=models.Index(fields=["phone_no"], name="staff_phone_idx"),
        ),
        migrations.AddIndex(
            model_name="staff",
            index=models.Index(fields=["national_no"], name="staff_natno_idx"),
        ),
        migrations.AddIndex(
            model_name="staff",
            index=models.Index(fields=["job_no"], name="staff_jobno_idx"),
        ),
        # Subject indexes
        migrations.AddIndex(
            model_name="subject",
            index=models.Index(fields=["is_active"], name="subject_active_idx"),
        ),
        # CalendarSlot constraint (end_time > start_time)
        migrations.AddConstraint(
            model_name="calendarslot",
            constraint=models.CheckConstraint(
                name="calslot_time_order",
                check=models.Q(("end_time__gt", django.db.models.F("start_time"))),
            ),
        ),
    ]
