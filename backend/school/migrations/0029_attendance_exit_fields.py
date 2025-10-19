from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("school", "0028_readd_best_practices"),
    ]

    operations = [
        migrations.AddField(
            model_name="attendancerecord",
            name="exit_reasons",
            field=models.CharField(max_length=200, blank=True, default=""),
        ),
        migrations.AddField(
            model_name="attendancerecord",
            name="exit_left_at",
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name="attendancerecord",
            name="exit_returned_at",
            field=models.DateTimeField(null=True, blank=True),
        ),
    ]
