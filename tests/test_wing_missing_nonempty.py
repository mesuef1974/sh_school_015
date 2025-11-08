import pytest


@pytest.mark.django_db
def test_wing_missing_nonempty_shape_and_bounded_queries(
    client,
    django_user_model,
    django_assert_num_queries,
    minimal_school_data,
):
    """
    With a tiny non-empty dataset, ensure GET /api/v1/wing/missing/
    returns a stable shape (either {date,items:[]} or DRF pagination)
    and performs a small, bounded number of queries.
    """
    admin = django_user_model.objects.create_superuser(
        username="admin_wm_ne", email="admin_wm_ne@example.com", password="pass1234"
    )
    client.force_login(admin)

    dt = minimal_school_data["date"].isoformat()

    params = {"date": dt}

    # Upper bound: be conservative to avoid flakiness across DB backends
    with django_assert_num_queries(12, exact=False):
        resp = client.get("/api/v1/wing/missing/", params)

    assert resp.status_code in (200, 204), resp.content
    if resp.status_code == 204:
        return

    data = resp.json()
    # Accept dict with items[] or paginated results[] or a plain list
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
