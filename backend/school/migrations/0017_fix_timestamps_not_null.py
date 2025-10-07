from django.db import migrations, models
from django.utils import timezone


def populate_timestamps(apps, schema_editor):
    now = timezone.now()
    # List of (app_model_name, fields)
    targets = [
        ("Class", ["created_at", "updated_at"]),
        ("Student", ["created_at", "updated_at"]),
        ("Staff", ["created_at", "updated_at"]),
        ("Subject", ["created_at", "updated_at"]),
    ]
    for model_name, fields in targets:
        Model = apps.get_model("school", model_name)
        qs = Model.objects
        # Build filter for any NULL timestamp field
        null_filter = None
        from django.db.models import Q

        for f in fields:
            cond = Q(**{f + "__isnull": True})
            null_filter = cond if null_filter is None else (null_filter | cond)
        if null_filter is not None:
            # Use update() to avoid triggering auto_now/auto_now_add
            qs.filter(null_filter).update(**{f: now for f in fields})


class Migration(migrations.Migration):

    dependencies = [
        ("school", "0016_add_timestamps"),
    ]

    operations = [
        migrations.RunPython(populate_timestamps, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="class",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, null=False),
        ),
        migrations.AlterField(
            model_name="class",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, null=False),
        ),
        migrations.AlterField(
            model_name="student",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, null=False),
        ),
        migrations.AlterField(
            model_name="student",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, null=False),
        ),
        migrations.AlterField(
            model_name="staff",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, null=False),
        ),
        migrations.AlterField(
            model_name="staff",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, null=False),
        ),
        migrations.AlterField(
            model_name="subject",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, null=False),
        ),
        migrations.AlterField(
            model_name="subject",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, null=False),
        ),
    ]
