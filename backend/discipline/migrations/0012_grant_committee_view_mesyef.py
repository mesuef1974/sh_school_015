from django.db import migrations


def grant_perm(apps, schema_editor):
    """امنح المستخدم s.mesyef0904 صلاحية عرض مسار لجنة السلوك.

    تمنح الإذن التالي إن وُجد المستخدم:
      - discipline.incident_committee_view

    المهاجرة تتحمل غياب المستخدم/الإذن بدون فشل.
    """

    User = apps.get_model("auth", "User")
    Permission = apps.get_model("auth", "Permission")

    try:
        user = User.objects.filter(username="s.mesyef0904").first()
        if not user:
            return
        perm = Permission.objects.filter(codename="incident_committee_view").first()
        if not perm:
            return
        try:
            user.user_permissions.add(perm)
        except Exception:
            pass
    except Exception:
        # لا تفشل الهجرة في بيئات بلا بيانات مطابقة
        pass


def revoke_perm(apps, schema_editor):
    User = apps.get_model("auth", "User")
    Permission = apps.get_model("auth", "Permission")
    try:
        user = User.objects.filter(username="s.mesyef0904").first()
        if not user:
            return
        perm = Permission.objects.filter(codename="incident_committee_view").first()
        if not perm:
            return
        try:
            user.user_permissions.remove(perm)
        except Exception:
            pass
    except Exception:
        pass


class Migration(migrations.Migration):
    dependencies = [
        ("discipline", "0011_grant_committee_perms_marri"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(grant_perm, reverse_code=revoke_perm),
    ]
