from django.db import migrations


ROLE_GROUPS = [
    "رئيس اللجنة السلوكية",
    "أعضاء اللجنة السلوكية",
    "مقرر اللجنة السلوكية",
]


def drop_extra_role_groups(apps, schema_editor):
    """Remove separate role groups in favor of a single main group "اللجنة السلوكية".

    This migration keeps database clean if 0005 created those groups previously.
    We do not delete the main group nor any permissions.
    """
    Group = apps.get_model("auth", "Group")
    for name in ROLE_GROUPS:
        grp = Group.objects.filter(name=name).first()
        if grp:
            # Detach permissions that were auto-granted by previous migration
            grp.permissions.clear()
            # Delete the group only if no users are attached to avoid breaking expectations
            if grp.user_set.count() == 0:
                grp.delete()


def noop_reverse(apps, schema_editor):
    # No-op; we don't want to recreate those groups.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("discipline", "0005_committee_role_groups"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(drop_extra_role_groups, noop_reverse),
    ]
