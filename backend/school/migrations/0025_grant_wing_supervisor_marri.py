from django.db import migrations


def grant_supervisor(apps, schema_editor):
    """امنح المستخدم a.al-marri06039 عضوية مجموعة wing_supervisor.

    تتحمل المهاجرة غياب المستخدم/المجموعة بدون فشل، وتقوم بإنشاء المجموعة
    إن لم تكن موجودة.
    """

    User = apps.get_model("auth", "User")
    Group = apps.get_model("auth", "Group")

    try:
        user = User.objects.filter(username="a.al-marri06039").first()
        if not user:
            return
        group, _ = Group.objects.get_or_create(name="wing_supervisor")
        try:
            user.groups.add(group)
        except Exception:
            pass
    except Exception:
        # لا تفشل الهجرة في بيئات بلا بيانات مطابقة
        pass


def revoke_supervisor(apps, schema_editor):
    User = apps.get_model("auth", "User")
    Group = apps.get_model("auth", "Group")
    try:
        user = User.objects.filter(username="a.al-marri06039").first()
        if not user:
            return
        group = Group.objects.filter(name="wing_supervisor").first()
        if not group:
            return
        try:
            user.groups.remove(group)
        except Exception:
            pass
    except Exception:
        pass


class Migration(migrations.Migration):
    dependencies = [
        ("school", "0024_db_best_practices"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(grant_supervisor, reverse_code=revoke_supervisor),
    ]
