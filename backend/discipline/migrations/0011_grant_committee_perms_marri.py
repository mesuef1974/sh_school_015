from django.db import migrations


def grant_perms(apps, schema_editor):
    """امنح «النائب الإداري عبدالرحمن المري» صلاحيات لجنة السلوك.

    المستخدم المطلوب: a.al-marri06039

    الأذونات:
      - discipline.incident_committee_view
      - discipline.incident_committee_schedule
      - discipline.incident_committee_decide

    المهاجرة تتحمل غياب المستخدم أو الأذونات بدون فشل.
    """

    User = apps.get_model("auth", "User")
    Permission = apps.get_model("auth", "Permission")

    try:
        user = User.objects.filter(username="a.al-marri06039").first()
        if not user:
            return
        needed = [
            "incident_committee_view",
            "incident_committee_schedule",
            "incident_committee_decide",
        ]
        perms = list(Permission.objects.filter(codename__in=needed))
        for p in perms:
            try:
                user.user_permissions.add(p)
            except Exception:
                pass
        # لا حاجة لاستدعاء save(); إضافة العلاقات تكفي
    except Exception:
        # تجاهل أي خطأ غير متوقع لضمان عدم تعطل الهجرات على بيئات بلا بيانات مطابقة
        pass


def revoke_perms(apps, schema_editor):
    User = apps.get_model("auth", "User")
    Permission = apps.get_model("auth", "Permission")
    try:
        user = User.objects.filter(username="a.al-marri06039").first()
        if not user:
            return
        needed = [
            "incident_committee_view",
            "incident_committee_schedule",
            "incident_committee_decide",
        ]
        perms = list(Permission.objects.filter(codename__in=needed))
        for p in perms:
            try:
                user.user_permissions.remove(p)
            except Exception:
                pass
    except Exception:
        pass


class Migration(migrations.Migration):
    dependencies = [
        ("discipline", "0010_remove_committee_group"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(grant_perms, reverse_code=revoke_perms),
    ]
