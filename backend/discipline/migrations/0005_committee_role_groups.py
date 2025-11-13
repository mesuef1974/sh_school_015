from django.db import migrations


CHAIR_GROUP = "رئيس اللجنة السلوكية"
MEMBER_GROUP = "أعضاء اللجنة السلوكية"
RECORDER_GROUP = "مقرر اللجنة السلوكية"
MAIN_GROUP = "اللجنة السلوكية"


def create_role_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    # Ensure main committee group exists (created in 0004), but re-create if missing.
    main_grp, _ = Group.objects.get_or_create(name=MAIN_GROUP)

    # Content type for discipline.Incident
    try:
        ct = ContentType.objects.get(app_label="discipline", model="incident")
    except ContentType.DoesNotExist:
        ct = None

    # Required permissions (create if missing)
    wanted = [
        ("incident_committee_view", "Can view incidents for committee workflow"),
        ("incident_committee_schedule", "Can schedule/route incident to committee"),
        ("incident_committee_decide", "Can record committee decision for incident"),
    ]
    extra = [
        ("incident_review", "Can review incident (approve/return)"),
        ("incident_notify_guardian", "Can notify guardian for incident"),
    ]

    created_perms = {}
    if ct is not None:
        for code, name in wanted + extra:
            p = Permission.objects.filter(content_type=ct, codename=code).first()
            if not p:
                p = Permission.objects.create(content_type=ct, codename=code, name=name)
            created_perms[code] = p
            # Ensure main group has the core perms
            if not main_grp.permissions.filter(id=p.id).exists():
                main_grp.permissions.add(p)

    # Create role groups
    chair_grp, _ = Group.objects.get_or_create(name=CHAIR_GROUP)
    member_grp, _ = Group.objects.get_or_create(name=MEMBER_GROUP)
    recorder_grp, _ = Group.objects.get_or_create(name=RECORDER_GROUP)

    # Assign permissions to role groups (least privilege)
    if created_perms:
        # Chair: view + schedule + decide
        for code in ["incident_committee_view", "incident_committee_schedule", "incident_committee_decide"]:
            p = created_perms.get(code)
            if p and not chair_grp.permissions.filter(id=p.id).exists():
                chair_grp.permissions.add(p)
        # Member: view only
        p = created_perms.get("incident_committee_view")
        if p and not member_grp.permissions.filter(id=p.id).exists():
            member_grp.permissions.add(p)
        # Recorder: view only
        p = created_perms.get("incident_committee_view")
        if p and not recorder_grp.permissions.filter(id=p.id).exists():
            recorder_grp.permissions.add(p)


def drop_role_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for name in [CHAIR_GROUP, MEMBER_GROUP, RECORDER_GROUP]:
        grp = Group.objects.filter(name=name).first()
        if grp:
            # Do not delete if has users; just remove autogranted perms
            grp.permissions.clear()
            if grp.user_set.count() == 0:
                grp.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("discipline", "0004_committee_group"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(create_role_groups, drop_role_groups),
    ]
