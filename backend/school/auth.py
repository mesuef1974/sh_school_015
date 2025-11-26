from datetime import timedelta
from typing import Any, Dict

from django.conf import settings
from django.db import DatabaseError
from rest_framework import status
from rest_framework.response import Response
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

REFRESH_COOKIE_NAME = getattr(settings, "SIMPLE_JWT_REFRESH_COOKIE_NAME", "refresh_token")
REFRESH_COOKIE_SAMESITE = getattr(settings, "SIMPLE_JWT_REFRESH_COOKIE_SAMESITE", "Lax")
REFRESH_COOKIE_SECURE = getattr(settings, "SIMPLE_JWT_REFRESH_COOKIE_SECURE", True)


def _cookie_max_age() -> int:
    """Return max-age for refresh cookie, tolerating missing SIMPLE_JWT settings.

    Falls back to 14 days when REFRESH_TOKEN_LIFETIME is not configured.
    """
    try:
        sj = getattr(settings, "SIMPLE_JWT", {}) or {}
        lt = sj.get("REFRESH_TOKEN_LIFETIME")
        if isinstance(lt, timedelta):
            return int(lt.total_seconds())
    except Exception:
        pass
    # Fallback: 14 days
    return 14 * 24 * 60 * 60


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        groups = list(user.groups.values_list("name", flat=True))
        token["groups"] = groups
        token["is_staff"] = user.is_staff
        return token


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    # Avoid global DRF throttling (which may hit Redis-backed cache) on auth endpoints.
    # This prevents 500 errors when Redis/cache is down by skipping throttle cache access.
    throttle_classes: list = []

    def post(self, request, *args, **kwargs):
        try:
            response: Response = super().post(request, *args, **kwargs)
            # Move refresh to HttpOnly cookie, but KEEP it in JSON for API clients/tests
            refresh = response.data.get("refresh") if isinstance(response.data, dict) else None
            if refresh:
                response.set_cookie(
                    key=REFRESH_COOKIE_NAME,
                    value=refresh,
                    httponly=True,
                    secure=REFRESH_COOKIE_SECURE,
                    samesite=REFRESH_COOKIE_SAMESITE,
                    max_age=_cookie_max_age(),
                )
            return response
        except DatabaseError as e:
            # Map DB connectivity issues to a 503 so the frontend can show a clear message
            payload: Dict[str, Any] = {
                "error": {
                    "code": "DB_UNAVAILABLE",
                    "message": "الخادم غير متاح الآن. تأكد من تشغيل الباك-إند ثم أعد المحاولة.",
                    "details": str(e),
                }
            }
            return Response(payload, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as e:
            # Avoid leaking 500s for expected validation paths; SimpleJWT will normally return 401
            payload: Dict[str, Any] = {
                "error": {
                    "code": "AUTH_FAILED",
                    "message": "تعذر إتمام عملية الدخول.",
                    "details": str(e),
                }
            }
            # 400 is safer here; invalid credentials will still be 401 from parent view normally
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)


class CustomTokenRefreshView(TokenRefreshView):
    # Skip throttling here as well to avoid hitting unavailable cache/Redis
    throttle_classes: list = []

    def post(self, request, *args, **kwargs):
        try:
            # Accept refresh from cookie if not provided in body
            data = request.data.copy() if isinstance(request.data, dict) else {}
            if not data.get("refresh"):
                cookie_val = request.COOKIES.get(REFRESH_COOKIE_NAME)
                if cookie_val:
                    data["refresh"] = cookie_val
                    request._full_data = data  # type: ignore[attr-defined]
            response: Response = super().post(request, *args, **kwargs)
            # Rotate/set cookie if new refresh was issued; keep it in JSON as well
            new_refresh = response.data.get("refresh") if isinstance(response.data, dict) else None
            if new_refresh:
                response.set_cookie(
                    key=REFRESH_COOKIE_NAME,
                    value=new_refresh,
                    httponly=True,
                    secure=REFRESH_COOKIE_SECURE,
                    samesite=REFRESH_COOKIE_SAMESITE,
                    max_age=_cookie_max_age(),
                )
            return response
        except DatabaseError as e:
            payload: Dict[str, Any] = {
                "error": {
                    "code": "DB_UNAVAILABLE",
                    "message": "الخادم غير متاح الآن. تأكد من تشغيل الباك-إند ثم أعد المحاولة.",
                    "details": str(e),
                }
            }
            return Response(payload, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as e:
            payload: Dict[str, Any] = {
                "error": {
                    "code": "REFRESH_FAILED",
                    "message": "تعذر تحديث الجلسة.",
                    "details": str(e),
                }
            }
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
