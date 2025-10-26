from django.db import migrations, models, connection
from django.db.models import Q
from django.db.models.functions import Lower


def _allow_null_staff_email(apps, schema_editor):
    # Skip on SQLite (used in tests) where ALTER COLUMN ... DROP NOT NULL is not supported
    if connection.vendor == "sqlite":
        return
    with connection.cursor() as cursor:
        cursor.execute("ALTER TABLE school_staff ALTER COLUMN email DROP NOT NULL;")


def _normalize_staff_emails(apps, schema_editor):
    # Skip heavy normalization on SQLite during tests; production/Postgres only
    if connection.vendor == "sqlite":
        return
    statements = [
        "UPDATE school_staff SET email = NULL WHERE email = '';",
        "UPDATE school_staff SET email = lower(email) WHERE email IS NOT NULL;",
        (
            "WITH d AS ("
            "  SELECT lower(email) AS le, MIN(id) AS keep_id"
            "  FROM school_staff"
            "  WHERE email IS NOT NULL"
            "  GROUP BY lower(email)"
            "  HAVING COUNT(*) > 1"
            ")"
            "UPDATE school_staff s"
            " SET email = NULL"
            " FROM d"
            " WHERE s.email IS NOT NULL AND lower(s.email) = d.le AND s.id <> d.keep_id;"
        ),
    ]
    with connection.cursor() as cursor:
        for sql in statements:
            cursor.execute(sql)


class Migration(migrations.Migration):
    # Run this migration non-atomically so the data cleanup commits
    # before creating indexes/constraints, avoiding "pending trigger events".
    atomic = False

    dependencies = [
        ("school", "0017_fix_timestamps_not_null"),
    ]

    operations = [
        # Safety: keep students_count non-negative at DB level
        migrations.AddConstraint(
            model_name="class",
            constraint=models.CheckConstraint(check=Q(students_count__gte=0), name="class_students_count_nonneg"),
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
            index=models.Index(Lower("parent_email"), name="student_parent_email_lower_idx"),
        ),
        # Allow NULLs on staff.email to safely normalize values (some rows need to be nullified)
        migrations.RunPython(_allow_null_staff_email, reverse_code=migrations.RunPython.noop),
        # Normalize staff emails: trim/lowercase; convert empty strings to NULL and nullify duplicates
        migrations.RunPython(_normalize_staff_emails, reverse_code=migrations.RunPython.noop),
        # Enforce staff email uniqueness case-insensitively when provided and non-empty
        migrations.AddConstraint(
            model_name="staff",
            constraint=models.UniqueConstraint(
                Lower("email"),
                condition=Q(email__isnull=False) & ~Q(email=""),
                name="staff_email_ci_uniq",
            ),
        ),
    ]
