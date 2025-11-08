import pytest


@pytest.mark.django_db
def test_teacher_weekly_nonempty_shape_and_bounded_queries(
    client,
    django_user_model,
    django_assert_num_queries,
    minimal_school_data,
):
    """
    With minimal non-empty data, GET /api/v1/attendance/timetable/teacher/weekly/
    should return a stable structure (days mapping; optional meta) and keep
    queries within a conservative upper bound.
    """
    # Log in as the teacher from the fixture where possible; otherwise a superuser
    teacher = minimal_school_data.get("teacher_user")
    if teacher:
        client.force_login(teacher)
    else:
        admin = django_user_model.objects.create_superuser(
            username="admin_tw_ne", email="admin_tw_ne@example.com", password="pass1234"
        )
        client.force_login(admin)

    with django_assert_num_queries(20, exact=False):
        resp = client.get("/api/v1/attendance/timetable/teacher/weekly/")

    assert resp.status_code in (200, 204), resp.content
    if resp.status_code == 204:
        return

    data = resp.json()
    assert isinstance(data, dict)
    assert "days" in data, data
    assert isinstance(data["days"], dict)
    # meta is optional but if present should be an object
    if "meta" in data:
        assert isinstance(data["meta"], dict)
