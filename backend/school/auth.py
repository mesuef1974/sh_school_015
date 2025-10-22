from datetime import timedelta
from django.conf import settings
from rest_framework.response import Response
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


REFRESH_COOKIE_NAME = getattr(settings, "SIMPLE_JWT_REFRESH_COOKIE_NAME", "refresh_token")
REFRESH_COOKIE_SAMESITE = getattr(settings, "SIMPLE_JWT_REFRESH_COOKIE_SAMESITE", "Lax")
REFRESH_COOKIE_SECURE = getattr(settings, "SIMPLE_JWT_REFRESH_COOKIE_SECURE", True)


def _cookie_max_age() -> int:
    lt: timedelta = settings.SIMPLE_JWT.get("REFRESH_TOKEN_LIFETIME")  # type: ignore
    return int(lt.total_seconds()) if lt else 86400


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

    def post(self, request, *args, **kwargs):
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


class CustomTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
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