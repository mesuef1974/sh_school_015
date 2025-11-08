import pytest


@pytest.mark.django_db
def test_records_endpoint_bounded_queries_nonempty(
    client, django_user_model, django_assert_num_queries, minimal_school_data
):
    """
    With a tiny non-empty dataset, ensure /api/v1/attendance/records/ performs a
    small, bounded number of queries and returns expected shape with at least one record.
    """
    admin = django_user_model.objects.create_superuser(
        username="admin_ne", email="admin_ne@example.com", password="pass1234"
    )
    client.force_login(admin)

    classroom = minimal_school_data["classroom"]
    dt = minimal_school_data["date"].isoformat()

    url = "/api/v1/attendance/records/"
    params = {"class_id": classroom.id, "date": dt}

    # Upper bound: auth/groups + query + select_related; allow a few extra for ORM differences
    with django_assert_num_queries(10, exact=False):
        resp = client.get(url, params)

    assert resp.status_code == 200, resp.content
    data = resp.json()
    assert isinstance(data, dict)
    assert set(["records", "date", "class_id"]).issubset(set(data.keys()))
    assert isinstance(data["records"], list)
    # Our fixture creates exactly one AttendanceRecord for that class/date
    assert len(data["records"]) >= 1
