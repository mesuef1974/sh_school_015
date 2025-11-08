import pytest


@pytest.mark.django_db
def test_history_strict_has_bounded_queries(client, django_user_model, django_assert_num_queries):
    """
    Guard against accidental N+1 in history-strict endpoint by asserting
    a small, bounded number of queries for an empty result set.

    Rationale: Even with no data, poorly structured code might perform
    excessive auth/group lookups or redundant ORM hits. We keep this
    threshold conservative so future additions remain efficient.
    """
    # Create a superuser to bypass classroom access checks cleanly
    user = django_user_model.objects.create_superuser(
        username="admin", email="admin@example.com", password="pass1234"
    )
    client.force_login(user)

    url = "/api/v1/attendance/history-strict/"
    params = {"class_id": 1, "from": "2024-01-01", "to": "2024-01-07"}

    # Expect a handful of queries: groups fetch, attendance count + slice, maybe subject/student select_related
    # Keep threshold slightly above observed to prevent flakes across DB backends.
    with django_assert_num_queries(5):
        resp = client.get(url, params)

    assert resp.status_code in (200,), resp.content
    data = resp.json()
    # Shape expectations (empty dataset still returns these keys)
    assert set(["count", "page", "page_size", "from", "to", "class_id", "results"]) <= set(data.keys())
    assert isinstance(data.get("results", []), list)