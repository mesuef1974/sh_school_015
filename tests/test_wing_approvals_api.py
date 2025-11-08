import pytest


@pytest.mark.django_db
def test_wing_pending_shape_and_bounded_queries(client, django_user_model, django_assert_num_queries):
    """
    GET /api/v1/wing/pending/ should return either 204 (no content) or a stable structure.
    Accept one of:
      - { date, count, items: [] }
      - DRF pagination { count, next, previous, results }
      - (rare) plain list []
    Also guard against N+1 for empty datasets using an upper bound on queries.
    """
    user = django_user_model.objects.create_superuser(
        username="admin_wp", email="admin_wp@example.com", password="pass1234"
    )
    client.force_login(user)

    params = {"date": "2024-01-01"}

    with django_assert_num_queries(8, exact=False):
        resp = client.get("/api/v1/wing/pending/", params)

    assert resp.status_code in (200, 204), resp.content
    if resp.status_code == 204:
        return

    data = resp.json()
    assert isinstance(data, (dict, list))
    if isinstance(data, dict):
        if "results" in data:
            for k in ("count", "next", "previous", "results"):
                assert k in data, data
            assert isinstance(data["results"], list)
        else:
            assert "items" in data, data
            assert isinstance(data["items"], list)
    else:
        assert isinstance(data, list)


@pytest.mark.django_db
def test_wing_decide_and_set_excused_error_envelope_when_unauthorized(client):
    """
    POST /api/v1/wing/decide/ and /api/v1/wing/set-excused/ should return unified error envelope
    when unauthenticated/unauthorized or when payload invalid. We assert 4xx and envelope shape.
    """
    # Unauthenticated by design here
    resp1 = client.post("/api/v1/wing/decide/", data={"action": "approve", "ids": [1, 2]})
    assert 400 <= resp1.status_code < 500, resp1.content
    data1 = resp1.json()
    assert isinstance(data1, dict)
    # Prefer unified envelope but tolerate legacy {detail: ...}
    if "error" in data1:
        err = data1["error"]
        assert isinstance(err, dict)
        assert isinstance(err.get("message", ""), str)
        assert err.get("code")
    else:
        assert "detail" in data1

    resp2 = client.post("/api/v1/wing/set-excused/", data={"ids": [1, 2]})
    assert 400 <= resp2.status_code < 500, resp2.content
    data2 = resp2.json()
    assert isinstance(data2, dict)
    if "error" in data2:
        err = data2["error"]
        assert isinstance(err, dict)
        assert isinstance(err.get("message", ""), str)
        assert err.get("code")
    else:
        assert "detail" in data2
