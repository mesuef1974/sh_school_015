import pytest


@pytest.mark.django_db
def test_history_strict_has_stable_keys_and_types(client, django_user_model):
    """
    The history-strict endpoint must keep a stable, explicit contract:
      {count, page, page_size, from, to, class_id, results}
    This test guards against accidental changes (e.g., switching to DRF default
    pagination keys next/previous) and validates basic types.
    """
    # Superuser should bypass class access checks
    user = django_user_model.objects.create_superuser(
        username="admin_hist", email="admin_hist@example.com", password="pass1234"
    )
    client.force_login(user)

    params = {"class_id": 1, "from": "2024-01-01", "to": "2024-01-07"}
    resp = client.get("/api/v1/attendance/history-strict/", params)

    # Endpoint should exist and respond OK (even if dataset is empty)
    assert resp.status_code == 200, resp.content

    data = resp.json()
    assert isinstance(data, dict)

    # Required keys (allow extra keys but these must exist)
    required = {"count", "page", "page_size", "from", "to", "class_id", "results"}
    assert required.issubset(set(data.keys())), data.keys()

    # Basic types
    assert isinstance(data["count"], int)
    assert isinstance(data["page"], int) and data["page"] >= 1
    assert isinstance(data["page_size"], int) and data["page_size"] >= 1
    assert isinstance(data["from"], str) and len(data["from"]) >= 10
    assert isinstance(data["to"], str) and len(data["to"]) >= 10
    # class_id may be coerced to int or string by some DB adapters; accept both but prefer int
    assert isinstance(data["class_id"], (int, str))
    assert isinstance(data["results"], list)

    # Results (if any) should have the documented minimal fields
    if data["results"]:
        item = data["results"][0]
        assert isinstance(item, dict)
        # Minimal shape used by frontend (client.ts:getAttendanceHistory)
        expected_item_keys = {"date", "student_id", "status"}
        assert expected_item_keys.issubset(set(item.keys()))