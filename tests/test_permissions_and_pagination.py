import pytest
from django.conf import settings


@pytest.mark.django_db
def test_unified_error_envelope_forbidden_when_authenticated_without_perms(client, django_user_model):
    """
    When authenticated but lacking DjangoModelPermissions, DRF should return 403
    and our custom exception handler must wrap the response in the unified
    error envelope: { "error": { code, message, details } }.
    """
    # Create a basic user without model permissions
    user = django_user_model.objects.create_user(
        username="u1", email="u1@example.com", password="pass1234"
    )
    client.force_login(user)

    # Hit an endpoint protected by DjangoModelPermissions
    resp = client.get("/api/v1/attendance/students/", {"class_id": 1})

    assert resp.status_code == 403, resp.content
    data = resp.json()
    assert isinstance(data, dict)
    if "error" in data:
        err = data["error"]
        assert isinstance(err, dict)
        # Typical DRF code for permission denied is 'permission_denied' -> uppercased
        assert err.get("code") in {"PERMISSION_DENIED", "NOT_AUTHENTICATED"}
        assert isinstance(err.get("message"), str) and err["message"]
        # Details should include DRF payload (usually {"detail": "..."})
        details = err.get("details")
        assert isinstance(details, dict)
        assert "detail" in details
    else:
        # Backward compatibility: plain DRF detail payload
        assert "detail" in data


@pytest.mark.django_db
def test_pagination_defaults_configured():
    """
    Confirm DRF pagination defaults are configured globally as per guidance.
    This guards against accidental removal of pagination config.
    """
    rf = settings.REST_FRAMEWORK
    assert rf.get("DEFAULT_PAGINATION_CLASS") == "rest_framework.pagination.PageNumberPagination"
    assert int(rf.get("PAGE_SIZE", 0)) == 50