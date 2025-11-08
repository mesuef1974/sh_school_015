import pytest


@pytest.mark.django_db
def test_wing_overview_nonempty_bounded_queries(client, django_user_model, django_assert_num_queries, minimal_school_data):
    """
    Ensure /api/v1/wing/overview/ behaves well with a tiny non-empty dataset.
    We assert a conservative upper bound on queries and basic response shape.
    """
    user = django_user_model.objects.create_superuser(
        username="admin_overview_ne", email="admin_overview_ne@example.com", password="pass1234"
    )
    client.force_login(user)

    wing = minimal_school_data["wing"]
    dt = minimal_school_data["date"].isoformat()

    with django_assert_num_queries(14, exact=False):
        resp = client.get("/api/v1/wing/overview/", {"wing_id": wing.id, "date": dt})

    assert resp.status_code == 200, resp.content
    data = resp.json()
    # Required top-level keys
    for k in ("date", "scope", "kpis", "top_classes", "worst_classes"):
        assert k in data, data.keys()
    assert isinstance(data["kpis"], dict)
    # KPI keys expected
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
    assert expected_kpi_keys.issubset(set(data["kpis"].keys()))
    # Types sanity
    assert isinstance(data["top_classes"], list)
    assert isinstance(data["worst_classes"], list)