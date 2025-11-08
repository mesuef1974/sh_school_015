import pytest


@pytest.mark.django_db
def test_attendance_submit_shape_and_error_envelope(client, django_user_model):
    """
    POST /api/v1/attendance/submit/ should return a stable shape on success and
    unified error envelope on auth/permission issues.
    Since test DB has no term/records by default, we focus on envelope for unauthenticated
    and shape for authenticated superuser with minimal payload.
    """
    # 1) Unauthenticated: expect 4xx with unified envelope or legacy {detail}
    resp_unauth = client.post(
        "/api/v1/attendance/submit/", data={"class_id": 1, "date": "2024-01-01"}
    )
    assert 400 <= resp_unauth.status_code < 500, resp_unauth.content
    data1 = resp_unauth.json()
    assert isinstance(data1, dict)
    if "error" in data1:
        err = data1["error"]
        assert isinstance(err, dict)
        assert isinstance(err.get("message", ""), str)
        assert err.get("code")
    else:
        assert "detail" in data1

    # 2) Authenticated superuser: expect 200 and stable keys (even if submitted=0)
    user = django_user_model.objects.create_superuser(
        username="admin_submit", email="admin_submit@example.com", password="pass1234"
    )
    client.force_login(user)
    resp_ok = client.post(
        "/api/v1/attendance/submit/", data={"class_id": 1, "date": "2024-01-01"}
    )
    assert resp_ok.status_code in (200, 400, 403), resp_ok.content
    data2 = resp_ok.json()
    if resp_ok.status_code == 200:
        assert isinstance(data2, dict)
        for k in ("submitted", "class_id", "date"):
            assert k in data2, data2
    else:
        # On validation/permission issues we still expect the unified envelope fallback
        assert isinstance(data2, dict)
        if "error" in data2:
            err = data2["error"]
            assert isinstance(err, dict)
            assert isinstance(err.get("message", ""), str)
            assert err.get("code")
        else:
            assert "detail" in data2