import pytest


@pytest.mark.django_db
def test_teacher_weekly_bounded_queries(client, django_user_model, django_assert_num_queries):
    """
    Guard against N+1 in teacher weekly timetable endpoint by asserting
    a small, bounded number of queries for an empty dataset.
    We authenticate as a superuser to bypass role checks cleanly.
    """
    user = django_user_model.objects.create_superuser(username="admin", email="admin@example.com", password="pass1234")
    client.force_login(user)

    url = "/api/v1/attendance/timetable/teacher/weekly/"
    # Expect a handful of queries: auth/groups + minimal timetable lookups
    with django_assert_num_queries(8, exact=False):
        resp = client.get(url)

    assert resp.status_code == 200, resp.content
    data = resp.json()
    assert isinstance(data, dict)
    # Response should contain 'days' (mapping) and optional 'meta'
    assert "days" in data
    assert isinstance(data["days"], dict)


@pytest.mark.django_db
def test_teacher_classes_bounded_queries(client, django_user_model, django_assert_num_queries):
    """
    Guard against N+1 on teacher classes discovery endpoint for empty assignments.
    """
    user = django_user_model.objects.create_user(username="t1", email="t1@example.com", password="pass1234")
    client.force_login(user)

    url = "/api/v1/attendance/teacher/classes/"
    # Expect minimal queries even when there are no TeachingAssignment rows
    with django_assert_num_queries(8, exact=False):
        resp = client.get(url)

    # Depending on role mapping, may be 403 or 200 with empty classes
    assert resp.status_code in (200, 403), resp.content
    data = resp.json()
    if resp.status_code == 200:
        assert isinstance(data, dict) and "classes" in data
        assert isinstance(data["classes"], list)
