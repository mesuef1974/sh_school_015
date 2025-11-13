from django.db import migrations


def create_committee_group(apps, schema_editor):
    """
    إنشاء مجموعة باسم "اللجنة السلوكية" ومنحها صلاحيات مخصّصة لمسار اللجنة.

    الصلاحيات:
      - incident_committee_view: الاطلاع على القضايا ضمن مسار اللجنة
      - incident_committee_schedule: جدولة/إحالة الواقعة إلى اللجنة
      - incident_committee_decide: تسجيل قرار اللجنة
    كما تُمنح صلاحيات مساندة:
      - incident_review, incident_notify_guardian
    """
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    # حدد نوع المحتوى لنموذج Incident في تطبيق discipline
    try:
        ct = ContentType.objects.get(app_label="discipline", model="incident")
    except ContentType.DoesNotExist:
        return  # في حالات نادرة جدًا، نتخطى بهدوء

    wanted = [
        "incident_committee_view",
        "incident_committee_schedule",
        "incident_committee_decide",
        # صلاحيات مساندة (قد تكون مفيدة لعمل اللجنة)
        "incident_review",
        "incident_notify_guardian",
    ]
    # تأكد من وجود صلاحيات codenames، وإن لم توجد قم بإنشائها الآن (أسماء ودية بالعربية/الإنجليزية)
    name_map = {
        "incident_committee_view": "Can view incidents for committee workflow",
        "incident_committee_schedule": "Can schedule/route incident to committee",
        "incident_committee_decide": "Can record committee decision for incident",
        "incident_review": "Can review incident (approve/return)",
        "incident_notify_guardian": "Can notify guardian for incident",
    }
    perms = []
    for code in wanted:
        p = Permission.objects.filter(content_type=ct, codename=code).first()
        if not p:
            p = Permission.objects.create(content_type=ct, codename=code, name=name_map.get(code, code))
        perms.append(p)

    grp, _ = Group.objects.get_or_create(name="اللجنة السلوكية")
    for p in perms:
        if not grp.permissions.filter(id=p.id).exists():
            grp.permissions.add(p)


def drop_committee_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    grp = Group.objects.filter(name="اللجنة السلوكية").first()
    if grp:
        # إزالة الصلاحيات المضافة فقط وترك البقية إن أضيفت يدويًا لاحقًا
        Permission = apps.get_model("auth", "Permission")
        ContentType = apps.get_model("contenttypes", "ContentType")
        try:
            ct = ContentType.objects.get(app_label="discipline", model="incident")
        except ContentType.DoesNotExist:
            ct = None
        wanted = [
            "incident_committee_view",
            "incident_committee_schedule",
            "incident_committee_decide",
            "incident_review",
            "incident_notify_guardian",
        ]
        if ct is not None:
            perms = list(Permission.objects.filter(content_type=ct, codename__in=wanted))
            for p in perms:
                grp.permissions.remove(p)
        # لا نحذف المجموعة إن كانت مستخدمة؛ نحاول حذفها فقط إذا أصبحت بلا صلاحيات وبلا أعضاء
        if grp.user_set.count() == 0 and grp.permissions.count() == 0:
            grp.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("discipline", "0003_incident_audit_log"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(create_committee_group, drop_committee_group),
    ]
