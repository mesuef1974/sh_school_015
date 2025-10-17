import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_teacher_classes_requires_auth():
    client = APIClient()
    resp = client.get("/api/v1/attendance/teacher/classes/")
    assert resp.status_code == 401


@pytest.mark.django_db
def test_teacher_classes_requires_teacher_role_or_superuser():
    User = get_user_model()
    User.objects.create_user(username="u1", password="pass123")

    client = APIClient()
    token_resp = client.post(
        "/api/token/", {"username": "u1", "password": "pass123"}, format="json"
    )
    assert token_resp.status_code == 200, token_resp.content
    access = token_resp.json()["access"]

    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    resp = client.get("/api/v1/attendance/teacher/classes/")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_teacher_classes_returns_list_for_teacher():
    User = get_user_model()
    u = User.objects.create_user(username="t1", password="pass123")
    g = Group.objects.create(name="teacher")
    u.groups.add(g)

    client = APIClient()
    token_resp = client.post(
        "/api/token/", {"username": "t1", "password": "pass123"}, format="json"
    )
    assert token_resp.status_code == 200, token_resp.content
    access = token_resp.json()["access"]

    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    resp = client.get("/api/v1/attendance/teacher/classes/")
    assert resp.status_code == 200, resp.content
    data = resp.json()
    assert "classes" in data
    assert isinstance(data["classes"], list)
