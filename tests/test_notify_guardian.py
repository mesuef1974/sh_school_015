import pytest
from django.utils import timezone


@pytest.mark.django_db
def test_notify_guardian_requires_permission(client, settings):
    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import Permission, ContentType

    User = get_user_model()

    # Reporter (no special perms)
    reporter = User.objects.create_user(username="rep_ng", password="x")
    # Caller (will gain permission)
    caller = User.objects.create_user(username="caller_ng", password="y")

    # Make student
    from django.apps import apps

    Student = apps.get_model("school", "Student")
    s_kwargs = {}
    if "full_name" in {f.name for f in Student._meta.get_fields()}:
        s_kwargs["full_name"] = "طالب اختبار"
    try:
        student = Student.objects.create(**s_kwargs)
    except Exception as e:
        pytest.skip(f"تعذر إنشاء Student: {e}")

    # Minimal violation degree 1
    from backend.discipline.models import BehaviorLevel, Violation, Incident

    lvl, _ = BehaviorLevel.objects.get_or_create(code=1, defaults={"name": "الدرجة الأولى", "description": ""})
    viol, _ = Violation.objects.get_or_create(
        code="NG-TST-1",
        defaults={
            "level": lvl,
            "category": "اختبار إشعار",
            "description": "",
            "default_actions": [],
            "default_sanctions": [],
            "severity": 1,
            "requires_committee": False,
            "policy": {"window_days": 365},
        },
    )

    inc = Incident.objects.create(
        violation=viol,
        student=student,
        reporter=reporter,
        occurred_at=timezone.now() - timezone.timedelta(hours=1),
        location="L",
        narrative="n",
        status="open",
        severity=viol.severity,
        committee_required=viol.requires_committee,
    )

    url = f"/api/discipline/incidents/{inc.id}/notify-guardian/"

    # 1) Without login -> 403
    resp = client.post(url, data={"channel": "sms"})
    assert resp.status_code in (401, 403)

    # 2) Logged in but without permission -> 403
    client.login(username="caller_ng", password="y")
    resp2 = client.post(url, data={"channel": "sms"})
    assert resp2.status_code == 403
    client.logout()

    # 3) Grant permission and retry -> 200
    ct_incident = ContentType.objects.get(app_label="discipline", model="incident")
    perm = Permission.objects.get(content_type=ct_incident, codename="incident_notify_guardian")
    caller.user_permissions.add(perm)
    client.login(username="caller_ng", password="y")
    resp3 = client.post(url, data={"channel": "sms", "message_preview": "تم إشعار ولي الأمر"})
    assert resp3.status_code == 200, resp3.content
    data = resp3.json()
    assert data.get("ok") is True
    assert data.get("channel") == "sms"
    assert data.get("sla_met") in (True, False)
    client.logout()


@pytest.mark.django_db
def test_notify_guardian_sla_met_and_unmet(client, settings):
    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import Permission, ContentType

    User = get_user_model()
    caller = User.objects.create_user(username="caller_sla", password="y")

    # Grant permission
    from backend.discipline.models import Incident

    ct_incident = ContentType.objects.get(app_label="discipline", model="incident")
    perm = Permission.objects.get(content_type=ct_incident, codename="incident_notify_guardian")
    caller.user_permissions.add(perm)

    # Student
    from django.apps import apps

    Student = apps.get_model("school", "Student")
    s_kwargs = {}
    if "full_name" in {f.name for f in Student._meta.get_fields()}:
        s_kwargs["full_name"] = "طالب اختبار"
    try:
        student = Student.objects.create(**s_kwargs)
    except Exception as e:
        pytest.skip(f"تعذر إنشاء Student: {e}")

    # Reporter and violation
    reporter = User.objects.create_user(username="rep_sla", password="x")
    from backend.discipline.models import BehaviorLevel, Violation

    lvl, _ = BehaviorLevel.objects.get_or_create(code=1, defaults={"name": "الدرجة الأولى", "description": ""})
    viol, _ = Violation.objects.get_or_create(
        code="NG-TST-2",
        defaults={
            "level": lvl,
            "category": "اختبار SLA",
            "description": "",
            "default_actions": [],
            "default_sanctions": [],
            "severity": 1,
            "requires_committee": False,
            "policy": {"window_days": 365},
        },
    )

    # Case A: occurred_at 1h ago -> sla_met True (24h window)
    inc_ok = Incident.objects.create(
        violation=viol,
        student=student,
        reporter=reporter,
        occurred_at=timezone.now() - timezone.timedelta(hours=1),
        status="open",
        location="L",
        narrative="n",
        severity=viol.severity,
        committee_required=viol.requires_committee,
    )
    client.login(username="caller_sla", password="y")
    url_ok = f"/api/discipline/incidents/{inc_ok.id}/notify-guardian/"
    r_ok = client.post(url_ok, data={"channel": "email"})
    assert r_ok.status_code == 200
    assert r_ok.json().get("sla_met") is True
    client.logout()

    # Case B: occurred_at 30h ago -> sla_met False
    inc_late = Incident.objects.create(
        violation=viol,
        student=student,
        reporter=reporter,
        occurred_at=timezone.now() - timezone.timedelta(hours=30),
        status="open",
        location="L",
        narrative="n",
        severity=viol.severity,
        committee_required=viol.requires_committee,
    )
    client.login(username="caller_sla", password="y")
    url_late = f"/api/discipline/incidents/{inc_late.id}/notify-guardian/"
    r_late = client.post(url_late, data={"channel": "whatsapp"})
    assert r_late.status_code == 200
    assert r_late.json().get("sla_met") is False
    client.logout()


@pytest.mark.django_db
def test_notify_guardian_degree_3_4_no_sla_enforcement(client, settings):
    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import Permission, ContentType

    User = get_user_model()
    caller = User.objects.create_user(username="caller_high", password="y")

    ct_incident = ContentType.objects.get(app_label="discipline", model="incident")
    perm = Permission.objects.get(content_type=ct_incident, codename="incident_notify_guardian")
    caller.user_permissions.add(perm)

    # Student
    from django.apps import apps

    Student = apps.get_model("school", "Student")
    s_kwargs = {}
    if "full_name" in {f.name for f in Student._meta.get_fields()}:
        s_kwargs["full_name"] = "طالب اختبار"
    try:
        student = Student.objects.create(**s_kwargs)
    except Exception as e:
        pytest.skip(f"تعذر إنشاء Student: {e}")

    # Reporter and violation severity 3
    reporter = User.objects.create_user(username="rep_high", password="x")
    from backend.discipline.models import BehaviorLevel, Violation, Incident

    lvl, _ = BehaviorLevel.objects.get_or_create(code=3, defaults={"name": "الدرجة الثالثة", "description": ""})
    viol, _ = Violation.objects.get_or_create(
        code="NG-TST-3",
        defaults={
            "level": lvl,
            "category": "اختبار عالي",
            "description": "",
            "default_actions": [],
            "default_sanctions": [],
            "severity": 3,
            "requires_committee": True,
            "policy": {"window_days": 365},
        },
    )

    inc = Incident.objects.create(
        violation=viol,
        student=student,
        reporter=reporter,
        occurred_at=timezone.now() - timezone.timedelta(hours=50),
        status="open",
        location="L",
        narrative="n",
        severity=viol.severity,
        committee_required=viol.requires_committee,
    )

    client.login(username="caller_high", password="y")
    url = f"/api/discipline/incidents/{inc.id}/notify-guardian/"
    r = client.post(url, data={"channel": "call"})
    assert r.status_code == 200
    # For degree 3, sla_met is not enforced; implementation leaves it False
    assert r.json().get("sla_met") in (False, None)
    client.logout()
