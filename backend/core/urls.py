"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.generic import RedirectView
from django.views.static import serve as static_serve
from django.http import HttpResponse
from django.db import connection
from rest_framework_simplejwt.views import TokenRefreshView
from school.auth import CustomTokenObtainPairView
from pathlib import Path

# Paths outside backend/ we might want to expose during development (DEBUG)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOC_DIR = PROJECT_ROOT / "DOC"
BACKEND_DIR = PROJECT_ROOT / "backend"
PROJECT_ROOT_DIR = PROJECT_ROOT  # for serving index.html

# --- Health endpoints ---


def livez(request):
    """Liveness probe: returns 204 if process is up."""
    return HttpResponse(status=204)


def healthz(request):
    """Readiness/health probe: checks DB connectivity and returns 200/500."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return HttpResponse("ok", status=200, content_type="text/plain")
    except Exception as e:
        return HttpResponse(f"db: {e}", status=500, content_type="text/plain")


def favicon(request):
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'>"
        "<rect width='16' height='16' fill='%230d6efd'/><text x='8' y='12' text-anchor='middle' font-size='10' fill='white'>S</text>"
        "</svg>"
    )
    return HttpResponse(svg, content_type="image/svg+xml")


urlpatterns = [
    path("livez", livez, name="livez"),
    path("healthz", healthz, name="healthz"),
    path("favicon.ico", favicon, name="favicon"),
    path("admin/", admin.site.urls),
    path("", include("school.urls")),
    # Friendly docs endpoints (development only)
    path("index", RedirectView.as_view(url="/docs/", permanent=False)),
]

# Development-only static serving for docs and the top-level index.html
if settings.DEBUG:
    urlpatterns += [
        # Serve the generated docs landing at /docs/
        path(
            "docs/",
            lambda request: static_serve(
                request, path="index.html", document_root=str(PROJECT_ROOT_DIR)
            ),
            name="docs_index",
        ),
        # Allow accessing files under DOC/ via /DOC/*
        re_path(
            r"^DOC/(?P<path>.*)$",
            static_serve,
            {"document_root": str(DOC_DIR)},
        ),
        # Serve the OpenAPI YAML from backend/ in development
        path(
            "backend/schema.yaml",
            lambda request: static_serve(
                request, path="schema.yaml", document_root=str(BACKEND_DIR)
            ),
            name="dev_openapi_yaml",
        ),
        # API and auth endpoints remain available
        path("api/", include("school.api.urls")),
        path("api-auth/", include("rest_framework.urls")),
        path("api/token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
        path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    ]
else:
    urlpatterns += [
        path("api/", include("school.api.urls")),
        path("api/token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
        path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    ]

# django-rq dashboard (development only for now)
if settings.DEBUG:
    urlpatterns += [
        path("django-rq/", include("django_rq.urls")),
    ]
