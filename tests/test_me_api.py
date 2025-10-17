import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_me_requires_auth():
    client = APIClient()
    resp = client.get("/api/me/")
    assert resp.status_code == 401


@pytest.mark.django_db
def test_me_returns_roles_when_authenticated():
    User = get_user_model()
    u = User.objects.create_user(username="t1", password="pass123")
    g = Group.objects.create(name="teacher")
    u.groups.add(g)

    client = APIClient()
    # Obtain JWT token
    token_resp = client.post(
        "/api/token/", {"username": "t1", "password": "pass123"}, format="json"
    )
    assert token_resp.status_code == 200, token_resp.content
    access = token_resp.json()["access"]

    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    resp = client.get("/api/me/")
    assert resp.status_code == 200
    data = resp.json()
    assert "teacher" in data.get("roles", [])
