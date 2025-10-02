from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("school", "0002_student_extra_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="staff",
            name="national_no",
            field=models.CharField(max_length=30, blank=True),
        ),
        migrations.AddField(
            model_name="staff",
            name="job_title",
            field=models.CharField(max_length=100, blank=True),
        ),
        migrations.AddField(
            model_name="staff",
            name="job_no",
            field=models.CharField(max_length=50, blank=True),
        ),
        migrations.AddField(
            model_name="staff",
            name="email",
            field=models.EmailField(max_length=254, blank=True),
        ),
        migrations.AddField(
            model_name="staff",
            name="phone_no",
            field=models.CharField(max_length=30, blank=True),
        ),
    ]
