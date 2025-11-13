from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):
    dependencies = [
        ("discipline", "0006_cleanup_committee_role_groups"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.AddField(
            model_name="incident",
            name="committee_panel",
            field=models.JSONField(
                blank=True, default=dict, help_text="تشكيلة اللجنة المحفوظة: {chair_id, member_ids[], recorder_id}"
            ),
        ),
        migrations.AddField(
            model_name="incident",
            name="committee_scheduled_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="incident",
            name="committee_scheduled_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="committee_scheduled_incidents",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
