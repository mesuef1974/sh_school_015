import pytest


@pytest.mark.django_db
def test_records_endpoint_has_bounded_queries(client, django_user_model, django_assert_num_queries):
    """
    Guard against accidental N+1 in /api/v1/attendance/records/ by asserting a
    small, bounded number of queries for an empty result set.

    We authenticate as superuser to bypass access checks cleanly. Even with no
    data in DB, the view should not perform excessive queries.
    """
    user = django_user_model.objects.create_superuser(
        username="admin2", email="admin2@example.com", password="pass1234"
    )
    client.force_login(user)

    url = "/api/v1/attendance/records/"
    params = {"class_id": 1, "date": "2024-01-01"}

    # Expected queries: auth/groups, attendance count/select, maybe select_related
    # Use an upper bound (or less) to avoid flakiness across ORM/DB backends.
    with django_assert_num_queries(5, exact=False):
        resp = client.get(url, params)

    # Endpoint is implemented and should return 200 with a stable shape
    assert resp.status_code == 200, resp.content
    data = resp.json()
    assert isinstance(data, dict)
    assert set(["records", "date", "class_id"]).issubset(set(data.keys()))
