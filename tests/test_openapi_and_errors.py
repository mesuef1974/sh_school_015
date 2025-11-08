import json
import pytest


@pytest.mark.django_db
def test_openapi_schema_available(client):
    # Request OpenAPI schema JSON
    resp = client.get("/api/schema/", HTTP_ACCEPT="application/json")
    assert resp.status_code == 200, resp.content
    # Should be a JSON object with an 'openapi' top-level key (per OpenAPI 3)
    data = resp.json()
    assert isinstance(data, dict)
    assert "openapi" in data
    assert data["openapi"].startswith("3."), data["openapi"]


@pytest.mark.django_db
def test_unified_error_envelope_for_unauthenticated_request(client):
    # Pick an endpoint that requires authentication (attendance students)
    # Provide a minimal required query param to hit the view logic
    resp = client.get("/api/v1/attendance/students/", {"class_id": 1})
    assert resp.status_code == 401, resp.content
    # Response must follow the unified error envelope
    data = resp.json()
    assert isinstance(data, dict)
    assert "error" in data, data
    err = data["error"]
    assert isinstance(err, dict)
    # Code should be derived from DRF exception default_code (uppercased)
    # For unauthenticated: NOT_AUTHENTICATED
    assert err.get("code") in {"NOT_AUTHENTICATED", "AUTHENTICATION_FAILED"}
    assert isinstance(err.get("message"), str) and err["message"]
    # Details should contain the original DRF payload (e.g., {"detail": "..."})
    details = err.get("details")
    assert isinstance(details, dict)
    assert "detail" in details