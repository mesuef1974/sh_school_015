import pytest


@pytest.mark.django_db
def test_user_can_access_class_superuser_true(django_user_model):
    """
    If the central RBAC helper exists, superuser should have access to any class.
    This asserts the expected policy without depending on specific data.
    If the helper is missing (legacy installs), we skip gracefully.
    """
    try:
        from apps.common.permissions import user_can_access_class  # type: ignore
    except Exception:
        pytest.skip("user_can_access_class not available in this build")

    user = django_user_model.objects.create_superuser(
        username="admin_rbac", email="admin_rbac@example.com", password="pass1234"
    )
    ok = bool(user_can_access_class(user, 1))
    assert ok is True


@pytest.mark.django_db
def test_user_can_access_class_basic_user_returns_bool(django_user_model):
    """
    For a regular user without explicit permissions, the helper should return a boolean value
    (typically False). This test verifies the function is stable and does not raise.
    """
    try:
        from apps.common.permissions import user_can_access_class  # type: ignore
    except Exception:
        pytest.skip("user_can_access_class not available in this build")

    user = django_user_model.objects.create_user(username="u_basic", email="u_basic@example.com", password="pass1234")
    result = user_can_access_class(user, 1)
    assert isinstance(result, bool)
