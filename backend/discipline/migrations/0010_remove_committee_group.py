from django.db import migrations


GROUP_NAME = "اللجنة السلوكية"
PERM_CODES = [
    "incident_committee_view",
    "incident_committee_schedule",
    "incident_committee_decide",
    "incident_review",
    "incident_notify_guardian",
]


def drop_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    grp = Group.objects.filter(name=GROUP_NAME).first()
    if not grp:
        return

    # Detach our permissions if assigned
    try:
        ct = ContentType.objects.get(app_label="discipline", model="incident")
    except ContentType.DoesNotExist:
        ct = None
    if ct is not None:
        perms = list(Permission.objects.filter(content_type=ct, codename__in=PERM_CODES))
        for p in perms:
            grp.permissions.remove(p)

    # Delete the group if empty; otherwise rename to indicate deprecated
    if grp.user_set.count() == 0 and grp.permissions.count() == 0:
        grp.delete()
    else:
        if grp.name == GROUP_NAME:
            grp.name = f"{GROUP_NAME} (deprecated)"
            grp.save(update_fields=["name"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("discipline", "0009_backfill_committee_from_panel"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(drop_group, noop),
    ]
