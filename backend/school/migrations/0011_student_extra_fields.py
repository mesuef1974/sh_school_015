from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("school", "0010_timetable_entry_v2"),
    ]

    operations = [
        migrations.AddField(
            model_name="student",
            name="english_name",
            field=models.CharField(max_length=200, blank=True),
        ),
        migrations.AddField(
            model_name="student",
            name="national_no",
            field=models.CharField(max_length=30, unique=True, null=True, blank=True),
        ),
        migrations.AddField(
            model_name="student",
            name="needs",
            field=models.BooleanField(default=False, help_text="احتياجات خاصة"),
        ),
        migrations.AddField(
            model_name="student",
            name="grade_label",
            field=models.CharField(max_length=50, blank=True, help_text="مثل 12-Science"),
        ),
        migrations.AddField(
            model_name="student",
            name="section_label",
            field=models.CharField(max_length=50, blank=True, help_text="مثل 12/1"),
        ),
        migrations.AddField(
            model_name="student",
            name="phone_no",
            field=models.CharField(max_length=200, blank=True),
        ),
        migrations.AddField(
            model_name="student",
            name="email",
            field=models.EmailField(max_length=254, blank=True),
        ),
        migrations.AddField(
            model_name="student",
            name="parent_name",
            field=models.CharField(max_length=200, blank=True),
        ),
        migrations.AddField(
            model_name="student",
            name="parent_relation",
            field=models.CharField(max_length=50, blank=True),
        ),
        migrations.AddField(
            model_name="student",
            name="parent_phone",
            field=models.CharField(max_length=200, blank=True),
        ),
        migrations.AddField(
            model_name="student",
            name="extra_phone_no",
            field=models.CharField(max_length=200, blank=True),
        ),
        migrations.AddField(
            model_name="student",
            name="parent_email",
            field=models.EmailField(max_length=254, blank=True),
        ),
        migrations.AddIndex(
            model_name="student",
            index=models.Index(fields=["national_no"], name="student_natno_idx"),
        ),
    ]
