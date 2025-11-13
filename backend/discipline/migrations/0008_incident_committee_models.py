from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):
    dependencies = [
        ("discipline", "0007_incident_committee_fields"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="IncidentCommittee",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("scheduled_at", models.DateTimeField(auto_now_add=True)),
                ("notes", models.TextField(blank=True)),
                (
                    "incident",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE, related_name="committee", to="discipline.incident"
                    ),
                ),
                (
                    "chair",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="chaired_committees",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "recorder",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="recorded_committees",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "scheduled_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="scheduled_committees",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Incident Committee",
                "verbose_name_plural": "Incident Committees",
            },
        ),
        migrations.CreateModel(
            name="IncidentCommitteeMember",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                (
                    "committee",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="members",
                        to="discipline.incidentcommittee",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="incident_committees",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="incidentcommittee",
            index=models.Index(fields=["incident"], name="committee_incident_idx"),
        ),
        migrations.AddIndex(
            model_name="incidentcommittee",
            index=models.Index(fields=["chair"], name="committee_chair_idx"),
        ),
        migrations.AddIndex(
            model_name="incidentcommitteemember",
            index=models.Index(fields=["committee"], name="committee_member_idx"),
        ),
        migrations.AddIndex(
            model_name="incidentcommitteemember",
            index=models.Index(fields=["user"], name="committee_member_user_idx"),
        ),
        migrations.AlterUniqueTogether(
            name="incidentcommitteemember",
            unique_together={("committee", "user")},
        ),
    ]
