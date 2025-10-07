from django.db import migrations, models
from django.db.models import Q
from django.db.models.functions import Lower


class Migration(migrations.Migration):

    dependencies = [
        ("school", "0017_fix_timestamps_not_null"),
    ]

    operations = [
        # Safety: keep students_count non-negative at DB level
        migrations.AddConstraint(
            model_name="class",
            constraint=models.CheckConstraint(
                check=Q(students_count__gte=0), name="class_students_count_nonneg"
            ),
        ),
        # Speed up frequent filtering by grade + section together
        migrations.AddIndex(
            model_name="student",
            index=models.Index(
                fields=["grade_label", "section_label"],
                name="student_grade_section_idx",
            ),
        ),
        # Accelerate case-insensitive lookups on emails (non-unique on students)
        migrations.AddIndex(
            model_name="student",
            index=models.Index(Lower("email"), name="student_email_lower_idx"),
        ),
        migrations.AddIndex(
            model_name="student",
            index=models.Index(
                Lower("parent_email"), name="student_parent_email_lower_idx"
            ),
        ),
        # Enforce staff email uniqueness case-insensitively when provided
        migrations.AddConstraint(
            model_name="staff",
            constraint=models.UniqueConstraint(
                Lower("email"),
                condition=Q(email__isnull=False),
                name="staff_email_ci_uniq",
            ),
        ),
    ]
