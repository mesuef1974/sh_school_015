import pytest


@pytest.mark.django_db
def test_wing_entered_nonempty_shape_and_bounded_queries(client, django_user_model, django_assert_num_queries, minimal_school_data):
    """
    With minimal non-empty data, GET /api/v1/wing/entered/ should return a
    stable structure (either {date, items: []} or DRF pagination) and respect a
    conservative upper bound on queries.
    """
    admin = django_user_model.objects.create_superuser(
        username="admin_we_ne", email="admin_we_ne@example.com", password="pass1234"
    )
    client.force_login(admin)

    classroom = minimal_school_data["classroom"]
    dt = minimal_school_data["date"].isoformat()

    params = {"date": dt}

    with django_assert_num_queries(12, exact=False):
        resp = client.get("/api/v1/wing/entered/", params)

    assert resp.status_code in (200, 204), resp.content
    if resp.status_code == 204:
        return

    data = resp.json()
    # Accept dict with items/results or plain list
    if isinstance(data, dict):
        if "results" in data:
            for k in ("count", "next", "previous", "results"):
                assert k in data, data
            assert isinstance(data["results"], list)
        else:
            assert "items" in data and isinstance(data["items"], list)
    else:
        assert isinstance(data, list)