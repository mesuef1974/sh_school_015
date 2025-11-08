import pytest


@pytest.mark.django_db
def test_wing_missing_shape_and_bounded_queries(client, django_user_model, django_assert_num_queries):
    """
    Shape: GET /api/v1/wing/missing/ should return either
      - { date, items: [...] }
      - or DRF pagination shape {count,next,previous,results}
    Also guard against N+1 for empty datasets with a conservative upper bound on queries.
    """
    user = django_user_model.objects.create_superuser(
        username="admin_wm", email="admin_wm@example.com", password="pass1234"
    )
    client.force_login(user)

    params = {"date": "2024-01-01"}

    with django_assert_num_queries(8, exact=False):
        resp = client.get("/api/v1/wing/missing/", params)

    assert resp.status_code in (200, 204), resp.content
    if resp.status_code == 204:
        return

    data = resp.json()
    assert isinstance(data, (dict, list))
    if isinstance(data, dict):
        # Accept either items[] or DRF pagination results[]
        if "results" in data:
            assert all(k in data for k in ("count", "next", "previous", "results")), data
            assert isinstance(data["results"], list)
        else:
            assert "date" in data and "items" in data, data
            assert isinstance(data["items"], list)
            # If items exist, validate a minimal item shape used in UI
            if data["items"]:
                it = data["items"][0]
                assert isinstance(it, dict)
                for k in ("class_id", "period_number", "subject_id", "teacher_id"):
                    assert k in it
    else:
        # Rare case: plain list
        assert isinstance(data, list)


@pytest.mark.django_db
def test_wing_entered_shape_and_bounded_queries(client, django_user_model, django_assert_num_queries):
    """
    Shape: GET /api/v1/wing/entered/ should return either
      - { date, items: [...] }
      - or DRF pagination shape {count,next,previous,results}
    Also guard against N+1 for empty datasets with a conservative upper bound on queries.
    """
    user = django_user_model.objects.create_superuser(
        username="admin_we", email="admin_we@example.com", password="pass1234"
    )
    client.force_login(user)

    params = {"date": "2024-01-01"}

    with django_assert_num_queries(8, exact=False):
        resp = client.get("/api/v1/wing/entered/", params)

    assert resp.status_code in (200, 204), resp.content
    if resp.status_code == 204:
        return

    data = resp.json()
    assert isinstance(data, (dict, list))
    if isinstance(data, dict):
        # Accept either items[] or DRF pagination results[]
        if "results" in data:
            assert all(k in data for k in ("count", "next", "previous", "results")), data
            assert isinstance(data["results"], list)
        else:
            assert "date" in data and "items" in data, data
            assert isinstance(data["items"], list)
            if data["items"]:
                it = data["items"][0]
                assert isinstance(it, dict)
                for k in ("class_id", "period_number", "subject_id", "teacher_id"):
                    assert k in it
    else:
        # Rare case: plain list
        assert isinstance(data, list)
