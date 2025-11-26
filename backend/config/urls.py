from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from apps.accounts.serializers import MyTokenObtainPairView
from rest_framework_simplejwt.views import TokenRefreshView


def livez(request):
    return HttpResponse(status=204)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.api.urls")),
    # JWT token endpoints
    path("api/token/", MyTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # Expose discipline (violations/incidents) APIs under /api/v1/ to match frontend calls
    path("api/v1/", include("discipline.urls")),
    # Health endpoint used by dev scripts
    path("livez", livez, name="livez"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]
