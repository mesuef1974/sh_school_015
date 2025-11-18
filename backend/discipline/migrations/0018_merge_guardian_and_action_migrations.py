from django.db import migrations


class Migration(migrations.Migration):
    # This merge resolves parallel 0017 migrations that were introduced
    # independently: one that adds guardian notify fields on Incident, and
    # another that introduced action/attachment changes. No schema changes
    # are needed here; we only unify the graph so Django can proceed.

    dependencies = [
        ("discipline", "0017_incident_guardian_notify_fields"),
        ("discipline", "0017_incidentattachment_action_and_more"),
    ]

    operations = []
