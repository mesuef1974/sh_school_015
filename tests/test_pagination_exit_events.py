import pytest


@pytest.mark.django_db
def test_exit_events_list_pagination_or_list_shape(client, django_user_model):
    """
    Document current behavior of the exit-events list endpoint.
    Preferably it should be paginated (dict with count/next/previous/results),
    but if it currently returns a plain list we only assert that it's a list.

    We authenticate as superuser to bypass permission issues and focus on shape.
    """
    user = django_user_model.objects.create_superuser(
        username="admin_evt", email="admin_evt@example.com", password="pass1234"
    )
    client.force_login(user)

    resp = client.get("/api/v1/attendance/exit-events/")
    assert resp.status_code in (200, 204), resp.content
    if resp.status_code == 204:
        return

    data = resp.json()
    # If DRF pagination is enabled, we expect standard keys.
    if isinstance(data, dict):
        for k in ("count", "next", "previous", "results"):
            assert k in data, data
        assert isinstance(data["results"], list)
    else:
        # Otherwise, current implementation may return a plain list
        assert isinstance(data, list)


@pytest.mark.django_db
def test_exit_events_bounded_queries(client, django_user_model, django_assert_num_queries):
    """
    Guard against excessive queries on /api/v1/attendance/exit-events/ for an empty dataset.
    """
    user = django_user_model.objects.create_superuser(
        username="admin_evt2", email="admin_evt2@example.com", password="pass1234"
    )
    client.force_login(user)

    with django_assert_num_queries(8, exact=False):
        resp = client.get("/api/v1/attendance/exit-events/")

    assert resp.status_code in (200, 204), resp.content
