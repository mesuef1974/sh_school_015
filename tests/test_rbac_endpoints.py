import pytest


def _assert_envelope_or_detail(resp):
    data = resp.json()
    assert isinstance(data, dict)
    if "error" in data:
        err = data["error"]
        assert isinstance(err, dict)
        # Code/message should be present and human-readable
        assert isinstance(err.get("message", ""), str)
        assert err.get("code")
        # Details usually include {detail: ...}
        det = err.get("details")
        assert isinstance(det, (dict, type(None)))
    else:
        # Backward-compat: plain DRF payload
        assert "detail" in data


@pytest.mark.django_db
def test_students_endpoint_forbidden_envelope_when_no_access(client, django_user_model):
    """
    Authenticated user without permissions should get 403 with unified envelope (or legacy detail).
    """
    user = django_user_model.objects.create_user(username="u_rbac1", email="u_rbac1@example.com", password="pass1234")
    client.force_login(user)

    resp = client.get("/api/v1/attendance/students/", {"class_id": 1})
    assert resp.status_code == 403, resp.content
    _assert_envelope_or_detail(resp)


@pytest.mark.django_db
def test_records_endpoint_forbidden_envelope_when_no_access(client, django_user_model):
    user = django_user_model.objects.create_user(username="u_rbac2", email="u_rbac2@example.com", password="pass1234")
    client.force_login(user)

    resp = client.get("/api/v1/attendance/records/", {"class_id": 1, "date": "2024-01-01"})
    assert resp.status_code == 403, resp.content
    _assert_envelope_or_detail(resp)


@pytest.mark.django_db
def test_wing_decide_forbidden_for_basic_user(client, django_user_model):
    user = django_user_model.objects.create_user(username="u_rbac3", email="u_rbac3@example.com", password="pass1234")
    client.force_login(user)

    resp = client.post("/api/v1/wing/decide/", data={"action": "approve", "ids": [1]})
    assert 400 <= resp.status_code < 500, resp.content
    _assert_envelope_or_detail(resp)


@pytest.mark.django_db
def test_wing_set_excused_forbidden_for_basic_user(client, django_user_model):
    user = django_user_model.objects.create_user(username="u_rbac4", email="u_rbac4@example.com", password="pass1234")
    client.force_login(user)

    resp = client.post("/api/v1/wing/set-excused/", data={"ids": [1, 2], "comment": "t"})
    assert 400 <= resp.status_code < 500, resp.content
    _assert_envelope_or_detail(resp)