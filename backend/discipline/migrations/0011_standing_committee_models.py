from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):
    dependencies = [
        ("discipline", "0010_remove_committee_group"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="StandingCommittee",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "chair",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="standing_committee_chair_of",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "recorder",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="standing_committee_recorder_of",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Standing Committee",
                "verbose_name_plural": "Standing Committees",
            },
        ),
        migrations.CreateModel(
            name="StandingCommitteeMember",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                (
                    "standing",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="members",
                        to="discipline.standingcommittee",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="standing_committees",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="standingcommitteemember",
            index=models.Index(fields=["standing"], name="standing_member_idx"),
        ),
        migrations.AddIndex(
            model_name="standingcommitteemember",
            index=models.Index(fields=["user"], name="standing_member_user_idx"),
        ),
        migrations.AlterUniqueTogether(
            name="standingcommitteemember",
            unique_together={("standing", "user")},
        ),
    ]
