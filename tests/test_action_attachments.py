import pytest
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile


@pytest.mark.django_db
def test_action_attachment_upload_updates_doc_received_and_enforces_perms(client):
    from django.contrib.auth import get_user_model

    User = get_user_model()

    # Reporter (normal user, no special perms)
    reporter = User.objects.create_user(username="rep", password="x")
    # Uploader with staff privileges (allowed)
    staff = User.objects.create_user(username="staff", password="y", is_staff=True)

    # Minimal related setup: Student, BehaviorLevel, Violation, Incident, Action
    from django.apps import apps

    Student = apps.get_model("school", "Student")
    # try minimal fields
    s_kwargs = {}
    if "full_name" in {f.name for f in Student._meta.get_fields()}:
        s_kwargs["full_name"] = "طالب اختبار"
    try:
        student = Student.objects.create(**s_kwargs)
    except Exception as e:
        pytest.skip(f"تعذر إنشاء Student: {e}")

    from backend.discipline.models import BehaviorLevel, Violation, Incident, Action

    lvl, _ = BehaviorLevel.objects.get_or_create(code=2, defaults={"name": "الدرجة الثانية", "description": ""})
    viol, _ = Violation.objects.get_or_create(
        code="T-TEST",
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
        location="A1",
        narrative="n",
        status="open",
        severity=viol.severity,
        committee_required=viol.requires_committee,
    )
    action = Action.objects.create(
        incident=inc,
        type="WRITTEN_WARNING",
        doc_required=True,
        requires_guardian_signature=True,
    )

    # 1) Normal user cannot upload (403)
    client.login(username="rep", password="x")
    url = f"/api/discipline/incidents/{inc.id}/actions/{action.id}/attachments/"
    resp = client.post(url)
    assert resp.status_code == 403
    client.logout()

    # 2) Staff can upload; send a small file
    client.login(username="staff", password="y")
    upload = SimpleUploadedFile("signed.pdf", b"%PDF-1.4 test pdf bytes", content_type="application/pdf")
    resp = client.post(url, data={"file": upload, "kind": "pledge_signed"})
    assert resp.status_code == 201, resp.content
    data = resp.json()
    # doc_pending should be False because doc_required=True and upload marks doc_received_at
    assert data.get("doc_pending") is False
    # Ensure attachment is linked to the specific Action (FK present and correct)
    assert str(data.get("action")) == str(action.id)

    # Ensure Action updated
    action.refresh_from_db()
    assert action.doc_received_at is not None
