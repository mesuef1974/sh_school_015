from django.db import migrations


def backfill_committee(apps, schema_editor):
    Incident = apps.get_model("discipline", "Incident")
    IncidentCommittee = apps.get_model("discipline", "IncidentCommittee")
    IncidentCommitteeMember = apps.get_model("discipline", "IncidentCommitteeMember")
    User = apps.get_model("auth", "User")

    for inc in Incident.objects.all().only("id", "committee_panel", "committee_scheduled_by", "committee_scheduled_at"):
        panel = getattr(inc, "committee_panel", None) or {}
        chair_id = panel.get("chair_id")
        member_ids = panel.get("member_ids") or []
        recorder_id = panel.get("recorder_id")
        if not chair_id or not isinstance(member_ids, list) or len(member_ids) == 0:
            continue
        try:
            chair = User.objects.filter(id=int(chair_id)).first()
            if not chair:
                continue
        except Exception:
            continue
        recorder = None
        if recorder_id:
            recorder = User.objects.filter(id=int(recorder_id)).first()

        # Create/update committee
        committee, _ = IncidentCommittee.objects.update_or_create(
            incident=inc,
            defaults={
                "chair": chair,
                "recorder": recorder,
                "scheduled_by": getattr(inc, "committee_scheduled_by", None),
            },
        )
        # Recreate members
        IncidentCommitteeMember.objects.filter(committee=committee).delete()
        for mid in member_ids:
            try:
                u = User.objects.filter(id=int(mid)).first()
                if u:
                    IncidentCommitteeMember.objects.create(committee=committee, user=u)
            except Exception:
                continue


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("discipline", "0008_incident_committee_models"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(backfill_committee, noop),
    ]
