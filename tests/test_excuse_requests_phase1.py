import pytest
import json
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone


@pytest.mark.django_db
def test_excuse_approve_idempotent_and_updates_absences():
    # Arrange: create user with convert permission
    User = get_user_model()
    reviewer = User.objects.create_user(username="rev", password="x", is_staff=True)

    # Lazy-import models to avoid app-registry issues
    from discipline.models import Absence, ExcuseRequest
    from django.apps import apps

    # Create a minimal student via apps registry (school.Student)
    Student = apps.get_model("school", "Student")
    # Try to satisfy required fields dynamically; skip test if impossible
    student_fields = {f.name for f in Student._meta.get_fields()}
    s_kwargs = {}
    if "full_name" in student_fields:
        s_kwargs["full_name"] = "طالب اختبار"
    try:
        student = Student.objects.create(**s_kwargs)
    except Exception as e:
        pytest.skip(f"تعذر إنشاء Student في بيئة الاختبار: {e}")

    # Create two absences: one UNEXCUSED, one already EXCUSED
    a1 = Absence.objects.create(student=student, date=timezone.now().date(), type="FULL_DAY", status="UNEXCUSED")
    a2 = Absence.objects.create(
        student=student,
        date=timezone.now().date(),
        type="PERIOD",
        period=1,
        status="EXCUSED",
    )
    req = ExcuseRequest.objects.create(submitted_by=reviewer)
    req.absences.set([a1, a2])

    # Act: approve twice (idempotent)
    req.approve(reviewer, reason="مستند طبي")
    status_after_first = req.status
    a1.refresh_from_db()
    a2.refresh_from_db()
    # Approve again should not flip anything or error
    req.approve(reviewer, reason="تكرار")
    a1.refresh_from_db()
    a2.refresh_from_db()

    # Assert
    assert status_after_first == "APPROVED_EXCUSE"
    assert req.status == "APPROVED_EXCUSE"
    assert a1.status == "EXCUSED"  # was UNEXCUSED and converted
    assert a2.status == "EXCUSED"  # remains EXCUSED


@pytest.mark.django_db
def test_attachment_blocked_after_final_decision(client):
    # Arrange: create user and login
    User = get_user_model()
    user = User.objects.create_user(username="u1", password="p1", is_staff=True)
    client.login(username="u1", password="p1")

    from discipline.models import Absence, ExcuseRequest
    from django.apps import apps

    Student = apps.get_model("school", "Student")
    s_kwargs = {}
    if "full_name" in {f.name for f in Student._meta.get_fields()}:
        s_kwargs["full_name"] = "طالب اختبار"
    try:
        student = Student.objects.create(**s_kwargs)
    except Exception as e:
        pytest.skip(f"تعذر إنشاء Student: {e}")

    absn = Absence.objects.create(student=student, date=timezone.now().date(), type="FULL_DAY", status="UNEXCUSED")
    req = ExcuseRequest.objects.create(submitted_by=user, status="UNDER_REVIEW")
    req.absences.set([absn])

    # Approve via model (simulate final decision)
    req.approve(user, reason="ok")

    # Try to add attachment through API should be rejected (400)
    url = f"/api/discipline/attendance/excuses/{req.id}/attachments/"
    resp = client.post(url, data=json.dumps({"url": "https://example.com/doc.pdf"}), content_type="application/json")
    assert resp.status_code == 400
    assert "لا يمكن إضافة مرفقات" in (resp.json().get("detail") or "")


@pytest.mark.django_db
def test_permissions_required_for_review_and_approve(client):
    User = get_user_model()
    normal = User.objects.create_user(username="n1", password="p1")
    reviewer = User.objects.create_user(username="r1", password="p2")

    # Grant reviewer the review and convert permissions

    ct = ContentType.objects.get(app_label="discipline", model="excuserequest")
    perm_review = Permission.objects.get(content_type=ct, codename="can_review_excuse_requests")
    perm_convert = Permission.objects.get(content_type=ct, codename="can_convert_absence_status")
    reviewer.user_permissions.add(perm_review, perm_convert)

    from django.apps import apps

    Student = apps.get_model("school", "Student")
    try:
        s = Student.objects.create(
            **({"full_name": "طالب"} if "full_name" in {f.name for f in Student._meta.get_fields()} else {})
        )
    except Exception as e:
        pytest.skip(f"تعذر إنشاء Student: {e}")

    from discipline.models import Absence

    absn = Absence.objects.create(student=s, date=timezone.now().date(), type="FULL_DAY", status="UNEXCUSED")

    # Create request as normal user
    client.login(username="n1", password="p1")
    # Create via API
    create_resp = client.post(
        "/api/discipline/attendance/excuses/",
        data=json.dumps({"absences": [absn.id], "submitted_by": normal.id}),
        content_type="application/json",
    )
    assert create_resp.status_code in (200, 201), create_resp.content
    req_id = create_resp.json().get("id")
    client.logout()

    # Normal user cannot review/approve
    client.login(username="n1", password="p1")
    resp = client.post(f"/api/discipline/attendance/excuses/{req_id}/review/")
    assert resp.status_code == 403
    resp = client.post(f"/api/discipline/attendance/excuses/{req_id}/approve/")
    assert resp.status_code == 403
    client.logout()

    # Reviewer can review and approve
    client.login(username="r1", password="p2")
    resp = client.post(f"/api/discipline/attendance/excuses/{req_id}/review/")
    assert resp.status_code == 200
    resp = client.post(f"/api/discipline/attendance/excuses/{req_id}/approve/", data={"reason": "ok"})
    assert resp.status_code == 200
