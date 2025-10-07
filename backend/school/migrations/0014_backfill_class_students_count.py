from django.db import migrations


def backfill_counts(apps, schema_editor):
    Class = apps.get_model("school", "Class")
    Student = apps.get_model("school", "Student")

    # Reset all to 0 first
    Class.objects.all().update(students_count=0)

    # Aggregate counts per class_fk
    from django.db.models import Count

    counts = (
        Student.objects.values("class_fk")
        .annotate(c=Count("id"))
        .filter(class_fk__isnull=False)
    )
    # Apply in batches
    for row in counts:
        Class.objects.filter(id=row["class_fk"]).update(students_count=row["c"])


def reverse_backfill(apps, schema_editor):
    Class = apps.get_model("school", "Class")
    Class.objects.all().update(students_count=0)


class Migration(migrations.Migration):

    dependencies = [
        ("school", "0013_class_students_count"),
    ]

    operations = [
        migrations.RunPython(backfill_counts, reverse_backfill),
    ]
