from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("school", "0012_student_parent_national_no"),
    ]

    operations = [
        migrations.AddField(
            model_name="class",
            name="students_count",
            field=models.PositiveIntegerField(default=0, db_index=True),
        ),
    ]
