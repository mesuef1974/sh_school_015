from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("discipline", "0014_incident_attachment"),
        ("school", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="incident",
            name="subject",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.SET_NULL,
                related_name="incidents",
                to="school.subject",
            ),
        ),
        migrations.AddField(
            model_name="incident",
            name="subject_name_cached",
            field=models.CharField(blank=True, default="", max_length=150),
        ),
    ]
