from django.db import migrations


class Migration(migrations.Migration):
    # Creating trigram extension and index requires non-atomic (for CONCURRENTLY)
    atomic = False

    dependencies = [
        ("school", "0028_readd_best_practices"),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                # Ensure pg_trgm extension exists (PostgreSQL)
                "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
            ),
            reverse_sql=(
                # Do not drop extension automatically; it may be used elsewhere
                "-- noop: keep pg_trgm extension"
            ),
        ),
        migrations.RunSQL(
            sql=(
                # Create trigram index on student full_name for fast Arabic fuzzy search
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS student_name_trgm\n"
                "  ON school_student USING GIN (full_name gin_trgm_ops);"
            ),
            reverse_sql=("DROP INDEX CONCURRENTLY IF EXISTS student_name_trgm;"),
        ),
    ]
