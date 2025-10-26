from django.db import migrations, connection


def _ensure_pg_trgm(apps, schema_editor):
    # Skip on SQLite (tests) and any non-Postgres DB
    if connection.vendor != "postgresql":
        return
    with connection.cursor() as cursor:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")


def _create_trgm_index(apps, schema_editor):
    if connection.vendor != "postgresql":
        return
    with connection.cursor() as cursor:
        cursor.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS student_name_trgm ON school_student USING GIN (full_name gin_trgm_ops);"
        )


class Migration(migrations.Migration):
    # Creating trigram extension and index requires non-atomic (for CONCURRENTLY)
    atomic = False

    dependencies = [
        ("school", "0028_readd_best_practices"),
    ]

    operations = [
        migrations.RunPython(_ensure_pg_trgm, reverse_code=migrations.RunPython.noop),
        migrations.RunPython(_create_trgm_index, reverse_code=migrations.RunPython.noop),
    ]
