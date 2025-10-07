from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("school", "0011_student_extra_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="student",
            name="parent_national_no",
            field=models.CharField(max_length=30, blank=True, help_text="الرقم الوطني لولي الأمر"),
        ),
    ]
