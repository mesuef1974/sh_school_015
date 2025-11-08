import pytest


@pytest.mark.django_db
def test_absence_alerts_list_is_paginated(client, django_user_model):
    """
    The AbsenceAlert list endpoint should use DRF pagination and return
    {count, next, previous, results}.
    We authenticate as superuser to bypass wing filtering for simplicity.
    """
    user = django_user_model.objects.create_superuser(
        username="admin_pag", email="admin_pag@example.com", password="pass1234"
    )
    client.force_login(user)

    resp = client.get("/api/v1/absence-alerts/")
    assert resp.status_code == 200, resp.content
    data = resp.json()
    assert isinstance(data, dict)
    # DRF PageNumberPagination keys
    assert set(["count", "next", "previous", "results"]).issubset(set(data.keys()))
    assert isinstance(data["results"], list)