import pytest
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission, ContentType


@pytest.mark.django_db
def test_actions_list_and_create_require_permissions(client):
    User = get_user_model()
    normal = User.objects.create_user(username="u_norm", password="x")
    viewer = User.objects.create_user(username="u_view", password="x")
    creator = User.objects.create_user(username="u_create", password="x")

    # Minimal related setup
    from django.apps import apps

    Student = apps.get_model("school", "Student")
    s_kwargs = {}
    if "full_name" in {f.name for f in Student._meta.get_fields()}:
        s_kwargs["full_name"] = "طالب"
    try:
        student = Student.objects.create(**s_kwargs)
    except Exception as e:
        pytest.skip(f"تعذر إنشاء Student: {e}")

    from backend.discipline.models import BehaviorLevel, Violation, Incident

    lvl, _ = BehaviorLevel.objects.get_or_create(code=1, defaults={"name": "الدرجة الأولى", "description": ""})
    viol, _ = Violation.objects.get_or_create(
        code="PERM-TST-1",
        defaults={
            "level": lvl,
            "category": "اختبار",
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
        reporter=normal,
        occurred_at=timezone.now(),
        location="L1",
        narrative="n",
        status="open",
        severity=viol.severity,
        committee_required=viol.requires_committee,
    )

    # Resolve permissions for Action model
    ct_action = ContentType.objects.get(app_label="discipline", model="action")
    perm_view = Permission.objects.get(content_type=ct_action, codename="action_view")
    perm_create = Permission.objects.get(content_type=ct_action, codename="action_create")
    viewer.user_permissions.add(perm_view)
    creator.user_permissions.add(perm_view, perm_create)

    url = f"/api/discipline/incidents/{inc.id}/actions/"

    # Normal: cannot list or create
    client.login(username="u_norm", password="x")
    resp = client.get(url)
    assert resp.status_code == 403
    resp = client.post(url, data={"type": "WRITTEN_NOTICE"})
    assert resp.status_code == 403
    client.logout()

    # Viewer: can list but cannot create
    client.login(username="u_view", password="x")
    resp = client.get(url)
    assert resp.status_code == 200
    resp = client.post(url, data={"type": "WRITTEN_NOTICE"})
    assert resp.status_code == 403
    client.logout()

    # Creator: can list and create
    client.login(username="u_create", password="x")
    resp = client.get(url)
    assert resp.status_code == 200
    resp = client.post(url, data={"type": "WRITTEN_NOTICE"})
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert data.get("type") == "WRITTEN_NOTICE"
    client.logout()


@pytest.mark.django_db
def test_action_complete_requires_permission(client):
    User = get_user_model()
    reporter = User.objects.create_user(username="rep2", password="x")
    worker = User.objects.create_user(username="worker1", password="x")
    closer = User.objects.create_user(username="closer1", password="x")

    from django.apps import apps

    Student = apps.get_model("school", "Student")
    s_kwargs = {}
    if "full_name" in {f.name for f in Student._meta.get_fields()}:
        s_kwargs["full_name"] = "طالب"
    try:
        student = Student.objects.create(**s_kwargs)
    except Exception as e:
        pytest.skip(f"تعذر إنشاء Student: {e}")

    from backend.discipline.models import BehaviorLevel, Violation, Incident, Action

    lvl, _ = BehaviorLevel.objects.get_or_create(code=2, defaults={"name": "الدرجة الثانية", "description": ""})
    viol, _ = Violation.objects.get_or_create(
        code="PERM-TST-2",
        defaults={
            "level": lvl,
            "category": "اختبار",
            "description": "",
            "default_actions": [],
            "default_sanctions": [],
            "severity": 2,
            "requires_committee": False,
            "policy": {"window_days": 365},
        },
    )
    inc = Incident.objects.create(
        violation=viol,
        student=student,
        reporter=reporter,
        occurred_at=timezone.now(),
        location="L2",
        narrative="n",
        status="open",
        severity=viol.severity,
        committee_required=viol.requires_committee,
    )
    act = Action.objects.create(incident=inc, type="WRITTEN_WARNING")

    url = f"/api/discipline/incidents/{inc.id}/actions/{act.id}/complete/"

    # No permission -> 403
    client.login(username="worker1", password="x")
    resp = client.post(url, data={"doc_received": True, "notes": "done"})
    assert resp.status_code == 403
    client.logout()

    # Grant action_complete to closer
    ct_action = ContentType.objects.get(app_label="discipline", model="action")
    perm_complete = Permission.objects.get(content_type=ct_action, codename="action_complete")
    closer.user_permissions.add(perm_complete)

    client.login(username="closer1", password="x")
    resp = client.post(url, data={"doc_received": True, "notes": "تم"})
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("completed_at") is not None
    assert data.get("doc_pending") in (False, True)  # depends on doc_required
    client.logout()
