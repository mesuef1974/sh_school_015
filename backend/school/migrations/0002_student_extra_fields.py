from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("school", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="student",
            name="nationality",
            field=models.CharField(max_length=100, blank=True, default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="student",
            name="age",
            field=models.PositiveSmallIntegerField(null=True, blank=True),
        ),
    ]
