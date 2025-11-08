import pytest


@pytest.mark.django_db
def test_attendance_submit_forbidden_envelope_when_no_access(client, django_user_model):
    """
    Authenticated basic user should receive 403 for submit without class access,
    with unified error envelope (or legacy {detail}).
    """
    user = django_user_model.objects.create_user(
        username="u_submit_forbid", email="u_submit_forbid@example.com", password="pass1234"
    )
    client.force_login(user)

    resp = client.post("/api/v1/attendance/submit/", data={"class_id": 1, "date": "2024-01-01"})
    assert resp.status_code == 403, resp.content

    data = resp.json()
    assert isinstance(data, dict)
    if "error" in data:
        err = data["error"]
        assert isinstance(err, dict)
        assert isinstance(err.get("message", ""), str)
        assert err.get("code")
        det = err.get("details")
        assert isinstance(det, (dict, type(None)))
    else:
        assert "detail" in data
