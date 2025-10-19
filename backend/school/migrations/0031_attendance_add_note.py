from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("school", "0030_merge_20251019_1604"),
    ]

    operations = [
        migrations.AddField(
            model_name="attendancerecord",
            name="note",
            field=models.CharField(max_length=300, blank=True),
        ),
    ]
