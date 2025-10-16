# Re-add DB best-practices constraints and indexes that were removed in 0025
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        ("school", "0025_remove_attendancerecord_att_day_between_1_7_and_more"),
    ]

    operations = [
        # --- Term: one current term per academic year ---
        migrations.AddConstraint(
            model_name="term",
            constraint=models.UniqueConstraint(
                fields=["academic_year", "is_current"],
                condition=Q(is_current=True),
                name="one_current_term_per_year",
            ),
        ),
        # --- TimetableEntry: quality constraints ---
        migrations.AddConstraint(
            model_name="timetableentry",
            constraint=models.CheckConstraint(
                condition=Q(day_of_week__gte=1) & Q(day_of_week__lte=5),
                name="tt_day_between_1_5",
            ),
        ),
        migrations.AddConstraint(
            model_name="timetableentry",
            constraint=models.CheckConstraint(
                condition=Q(period_number__gte=1) & Q(period_number__lte=7),
                name="tt_period_between_1_7",
            ),
        ),
        # --- TimetableEntry: composite indexes for common lookups ---
        migrations.AddIndex(
            model_name="timetableentry",
            index=models.Index(
                fields=["term", "teacher", "day_of_week", "period_number"],
                name="tt_term_teacher_day_period_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="timetableentry",
            index=models.Index(
                fields=["term", "classroom", "day_of_week", "period_number"],
                name="tt_term_class_day_period_idx",
            ),
        ),
        # --- AttendanceRecord: quality constraints ---
        migrations.AddConstraint(
            model_name="attendancerecord",
            constraint=models.CheckConstraint(
                condition=Q(day_of_week__gte=1) & Q(day_of_week__lte=7),
                name="att_day_between_1_7",
            ),
        ),
        migrations.AddConstraint(
            model_name="attendancerecord",
            constraint=models.CheckConstraint(
                condition=Q(period_number__gte=1) & Q(period_number__lte=7),
                name="att_period_between_1_7",
            ),
        ),
        # --- AttendanceRecord: composite indexes ---
        migrations.AddIndex(
            model_name="attendancerecord",
            index=models.Index(
                fields=["classroom", "date", "period_number", "term"],
                name="attrec_class_date_period_term_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="attendancerecord",
            index=models.Index(
                fields=["student", "date", "term"],
                name="attrec_student_date_term_idx",
            ),
        ),
        # --- TeachingAssignment: optional composite index to aid frequent joins ---
        migrations.AddIndex(
            model_name="teachingassignment",
            index=models.Index(
                fields=["teacher", "classroom"],
                name="ta_teacher_class_idx",
            ),
        ),
    ]
