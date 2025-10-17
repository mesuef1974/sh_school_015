import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_summary_requires_auth():
    client = APIClient()
    resp = client.get("/api/v1/attendance/summary/")
    assert resp.status_code == 401


@pytest.mark.django_db
def test_summary_empty_data_returns_zeros():
    User = get_user_model()
    User.objects.create_user(username="t1", password="pass123")

    client = APIClient()
    token_resp = client.post(
        "/api/token/", {"username": "t1", "password": "pass123"}, format="json"
    )
    assert token_resp.status_code == 200, token_resp.content
    access = token_resp.json()["access"]

    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    resp = client.get("/api/v1/attendance/summary/", {"scope": "school", "date": "2025-01-01"})
    assert resp.status_code == 200, resp.content
    data = resp.json()
    assert data["kpis"]["present_pct"] == 0.0
    assert data["kpis"]["absent"] == 0
    assert data["top_classes"] == []
    assert data["worst_classes"] == []


@pytest.mark.django_db
def test_summary_invalid_date_returns_400():
    User = get_user_model()
    User.objects.create_user(username="t2", password="pass123")

    client = APIClient()
    token_resp = client.post(
        "/api/token/", {"username": "t2", "password": "pass123"}, format="json"
    )
    assert token_resp.status_code == 200, token_resp.content
    access = token_resp.json()["access"]

    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    resp = client.get("/api/v1/attendance/summary/", {"date": "2025-13-40"})
    assert resp.status_code == 400
    body = resp.json()
    assert "date" in body.get("detail", "date must be YYYY-MM-DD")
