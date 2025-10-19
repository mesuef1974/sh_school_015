from django.db import migrations


class Migration(migrations.Migration):
    # This merge migration resolves the conflicting leaf nodes in the 'school' app
    # so that Django can proceed with applying migrations (including the new
    # attendance exit fields) without requiring a manual --merge step.

    dependencies = [
        ("school", "0029_attendance_exit_fields"),
        ("school", "0029_student_name_trgm"),
    ]

    operations = [
        # No schema changes; this migration only merges histories.
    ]
