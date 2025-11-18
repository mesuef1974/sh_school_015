from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("discipline", "0016_alter_behaviorlevel_options_alter_incident_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="incident",
            name="notified_guardian_at",
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name="incident",
            name="guardian_notify_channel",
            field=models.CharField(
                max_length=16,
                blank=True,
                help_text="sms/call/email/in_app/whatsapp",
            ),
        ),
        migrations.AddField(
            model_name="incident",
            name="guardian_notify_sla_met",
            field=models.BooleanField(default=False),
        ),
    ]
