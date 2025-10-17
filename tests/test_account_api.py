import pytest
from django.contrib.auth import get_user_model


@pytest.mark.django_db
def test_change_password_and_login(client):
    User = get_user_model()
    User.objects.create_user(username="alice", password="OldPass!234")

    # Obtain JWT token
    resp = client.post(
        "/api/token/",
        {"username": "alice", "password": "OldPass!234"},
        content_type="application/json",
    )
    assert resp.status_code == 200, resp.content
    access = resp.json()["access"]

    # Change password
    headers = {"HTTP_AUTHORIZATION": f"Bearer {access}"}
    payload = {
        "current_password": "OldPass!234",
        "new_password1": "NewPass!234",
        "new_password2": "NewPass!234",
    }
    resp2 = client.post(
        "/api/change_password/", payload, content_type="application/json", **headers
    )
    assert resp2.status_code == 200, resp2.content

    # Old password should fail now
    resp3 = client.post(
        "/api/token/",
        {"username": "alice", "password": "OldPass!234"},
        content_type="application/json",
    )
    assert resp3.status_code == 401

    # New password should work
    resp4 = client.post(
        "/api/token/",
        {"username": "alice", "password": "NewPass!234"},
        content_type="application/json",
    )
    assert resp4.status_code == 200


@pytest.mark.django_db
def test_logout_blacklists_refresh_token(client):
    User = get_user_model()
    User.objects.create_user(username="bob", password="Secr3t!234")

    # Token pair
    resp = client.post(
        "/api/token/",
        {"username": "bob", "password": "Secr3t!234"},
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = resp.json()
    access = data["access"]
    refresh = data["refresh"]

    # Logout with refresh token
    headers = {"HTTP_AUTHORIZATION": f"Bearer {access}"}
    resp2 = client.post(
        "/api/logout/", {"refresh": refresh}, content_type="application/json", **headers
    )
    assert resp2.status_code == 200

    # Refresh should now be rejected
    resp3 = client.post(
        "/api/token/refresh/", {"refresh": refresh}, content_type="application/json"
    )
    assert resp3.status_code in (401, 400)
