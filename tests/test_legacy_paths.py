import pytest


@pytest.mark.django_db
def test_removed_attendance_history_exports_return_404(client):
    # Legacy paths that were explicitly removed should return 404
    resp1 = client.get("/api/v1/attendance/history-export/")
    resp2 = client.get("/api/v1/attendance/history/export/")
    assert resp1.status_code == 404
    assert resp2.status_code == 404
