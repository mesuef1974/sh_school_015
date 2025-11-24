from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("discipline", "0018_merge_guardian_and_action_migrations"),
    ]

    operations = [
        migrations.AddField(
            model_name="excuserequest",
            name="due_at",
            field=models.DateField(blank=True, null=True),
        ),
    ]
