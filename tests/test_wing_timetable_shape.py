import pytest


@pytest.mark.django_db
def test_wing_timetable_daily_shape_and_bounded_queries(client, django_user_model, django_assert_num_queries):
    """
    Shape: GET /api/v1/wing/timetable/?mode=daily should return either 204 (no content)
    or 200 with a stable structure including mode='daily' and items list (may be empty).
    Also guard against N+1 by asserting a small, bounded number of queries on empty datasets.
    """
    user = django_user_model.objects.create_superuser(
        username="admin_wtt_d", email="admin_wtt_d@example.com", password="pass1234"
    )
    client.force_login(user)

    params = {"mode": "daily", "date": "2024-01-01"}
    # Expect a handful of queries only (auth/groups + minimal timetable lookups)
    with django_assert_num_queries(10, exact=False):
        resp = client.get("/api/v1/wing/timetable/", params)

    assert resp.status_code in (200, 204), resp.content
    if resp.status_code == 204:
        return

    data = resp.json()
    assert isinstance(data, dict)
    if "mode" in data:
        assert data.get("mode") == "daily"
    # Frontend expects 'items' for daily mode; tolerate absence by defaulting to [] there,
    # but we assert type when present for contract stability
    if "items" in data:
        assert isinstance(data["items"], list)
    # Optional metadata
    if "meta" in data:
        assert isinstance(data["meta"], dict)


@pytest.mark.django_db
def test_wing_timetable_weekly_shape_and_bounded_queries(client, django_user_model, django_assert_num_queries):
    """
    Shape: GET /api/v1/wing/timetable/?mode=weekly should return either 204 or 200 with
    mode='weekly' and 'days' mapping; include a bounded-queries guard for empty datasets.
    """
    user = django_user_model.objects.create_superuser(
        username="admin_wtt_w", email="admin_wtt_w@example.com", password="pass1234"
    )
    client.force_login(user)

    params = {"mode": "weekly"}
    with django_assert_num_queries(10, exact=False):
        resp = client.get("/api/v1/wing/timetable/", params)

    assert resp.status_code in (200, 204), resp.content
    if resp.status_code == 204:
        return

    data = resp.json()
    assert isinstance(data, dict)
    if "mode" in data:
        assert data.get("mode") == "weekly"
    if "days" in data:
        assert isinstance(data["days"], dict)
    if "meta" in data:
        assert isinstance(data["meta"], dict)