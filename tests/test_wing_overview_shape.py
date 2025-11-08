import pytest


@pytest.mark.django_db
def test_wing_overview_shape(client, django_user_model):
    """
    Wing overview should return a stable shape even with empty data:
      {date, scope, kpis{present_pct, absent, late, excused, runaway, present, total,
       exit_events_total, exit_events_open}, top_classes[], worst_classes[]}
    We authenticate as superuser to bypass any role filtering.
    """
    user = django_user_model.objects.create_superuser(
        username="admin_overview", email="admin_overview@example.com", password="pass1234"
    )
    client.force_login(user)

    resp = client.get("/api/v1/wing/overview/")
    assert resp.status_code == 200, resp.content

    data = resp.json()
    assert isinstance(data, dict), data
    # Required top-level keys
    for k in ("date", "scope", "kpis", "top_classes", "worst_classes"):
        assert k in data, data.keys()

    assert isinstance(data["date"], str)
    assert isinstance(data["scope"], str)
    assert isinstance(data["kpis"], dict)
    assert isinstance(data["top_classes"], list)
    assert isinstance(data["worst_classes"], list)

    # KPIs required keys
    kpis = data["kpis"]
    expected_kpi_keys = {
        "present_pct",
        "absent",
        "late",
        "excused",
        "runaway",
        "present",
        "total",
        "exit_events_total",
        "exit_events_open",
    }
    assert expected_kpi_keys.issubset(set(kpis.keys())), kpis.keys()


@pytest.mark.django_db
def test_wing_overview_bounded_queries(client, django_user_model, django_assert_num_queries):
    """
    Guard against excessive queries on /api/v1/wing/overview/ for an empty dataset.
    """
    user = django_user_model.objects.create_superuser(
        username="admin_overview2", email="admin_overview2@example.com", password="pass1234"
    )
    client.force_login(user)

    with django_assert_num_queries(10, exact=False):
        resp = client.get("/api/v1/wing/overview/")

    assert resp.status_code == 200, resp.content