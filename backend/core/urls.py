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

from pathlib import Path

from django.conf import settings
from django.db import connection
from django.http import HttpResponse
from django.urls import include, path, re_path
from django.views.generic import RedirectView
from django.views.static import serve as static_serve

# Use restricted admin site that allows only superusers or Staff with role 'admin'
from school.admin_site import restricted_admin_site
from school.api.views import logout as api_logout
from school.auth import CustomTokenObtainPairView, CustomTokenRefreshView
# Explicit import for a stable alias to Wing students DOCX export
from apps.attendance.api import WingSupervisorViewSet

# Paths outside backend/ we might want to expose during development (DEBUG)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOC_DIR = PROJECT_ROOT / "DOC"
BACKEND_DIR = PROJECT_ROOT / "backend"
ASSETS_DIR = PROJECT_ROOT / "assets"
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


# Explicit 404 for removed attendance export endpoints (placed first to mask any router actions)


def _export_removed(request):
    return HttpResponse(status=404)


urlpatterns = [
    re_path(
        r"^api/v1/attendance/history-export/?$",
        _export_removed,
        name="attendance-history-export-removed",
    ),
    re_path(
        r"^api/v1/attendance/history/export/?$",
        _export_removed,
        name="attendance-history-export-removed-compat",
    ),
    path("livez", livez, name="livez"),
    path("healthz", healthz, name="healthz"),
    path("favicon.ico", favicon, name="favicon"),
    path("admin/", restricted_admin_site.urls),
    # API v1 (new apps)
    path("api/v1/", include("apps.attendance.urls")),
    # Stable alias for Wing students DOCX export (works with/without trailing slash)
    path(
        "api/v1/wing/students/export.docx/",
        WingSupervisorViewSet.as_view({"get": "students_export_docx"}),
        name="wing-students-export-docx",
    ),
    path(
        "api/v1/wing/students/export.docx",
        WingSupervisorViewSet.as_view({"get": "students_export_docx"}),
        name="wing-students-export-docx-no-slash",
    ),
    path("", include("school.urls")),
    # Friendly docs endpoints (development only)
    path("index", RedirectView.as_view(url="/docs/", permanent=False)),
]

# Development-only static serving for docs and the top-level index.html
if settings.DEBUG:
    # Diagnostic endpoint to dump URL patterns (helps during routing issues)
    def _dump_urls(request):
        try:
            from django.urls import get_resolver

            resolver = get_resolver()
            patterns = []
            for p in resolver.url_patterns:
                try:
                    patterns.append(str(p.pattern))
                except Exception:
                    patterns.append(repr(p))
            text = "\n".join(patterns)
            return HttpResponse(text, content_type="text/plain")
        except Exception as e:
            return HttpResponse(f"error: {e}", content_type="text/plain", status=500)

    urlpatterns += [
        path("api/v1/__urls__", _dump_urls, name="debug_dump_urls"),
        # Developer-friendly alias without the double underscore
        path("api/v1/urls", _dump_urls, name="debug_dump_urls_alias"),
        # Serve the generated docs landing at /docs/
        path(
            "docs/",
            lambda request: static_serve(request, path="index.html", document_root=str(PROJECT_ROOT_DIR)),
            name="docs_index",
        ),
        # Allow accessing files under DOC/ via /DOC/*
        re_path(
            r"^DOC/(?P<path>.*)$",
            static_serve,
            {"document_root": str(DOC_DIR)},
        ),
        # Serve project assets under /assets/* for local development
        re_path(
            r"^assets/(?P<path>.*)$",
            static_serve,
            {"document_root": str(ASSETS_DIR)},
        ),
        # Serve the OpenAPI YAML from backend/ in development
        path(
            "backend/schema.yaml",
            lambda request: static_serve(request, path="schema.yaml", document_root=str(BACKEND_DIR)),
            name="dev_openapi_yaml",
        ),
        # API and auth endpoints remain available
        path("api/", include("school.api.urls")),
        path("api/", include("apps.attendance.urls")),  # expose attendance APIs under /api/* (in addition to /api/v1/*)
        path("api-auth/", include("rest_framework.urls")),
        # SimpleJWT default endpoints (pair/refresh)
        path("api/token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
        path("api/token/refresh/", CustomTokenRefreshView.as_view(), name="token_refresh"),
        # New unified auth endpoints under /api/v1/auth/* for the frontend
        path("api/v1/auth/login/", CustomTokenObtainPairView.as_view(), name="api_v1_auth_login"),
        path("api/v1/auth/refresh/", CustomTokenRefreshView.as_view(), name="api_v1_auth_refresh"),
        path("api/v1/auth/logout/", api_logout, name="api_v1_auth_logout"),
    ]
    # Serve Font Awesome webfonts at /webfonts/* from the installed package during DEBUG
    try:
        import fontawesomefree as _fa  # type: ignore

        FA_WEBFONTS_DIR = Path(_fa.__file__).resolve().parent / "static" / "fontawesomefree" / "webfonts"
    except Exception:
        FA_WEBFONTS_DIR = None
    if "FA_WEBFONTS_DIR" in locals() and FA_WEBFONTS_DIR and FA_WEBFONTS_DIR.exists():
        urlpatterns += [
            re_path(
                r"^webfonts/(?P<path>.*)$",
                static_serve,
                {"document_root": str(FA_WEBFONTS_DIR)},
            ),
        ]
else:
    urlpatterns += [
        path("api/", include("school.api.urls")),
        path("api/", include("apps.attendance.urls")),  # expose attendance APIs under /api/* in production too
        # SimpleJWT default endpoints (pair/refresh)
        path("api/token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
        path("api/token/refresh/", CustomTokenRefreshView.as_view(), name="token_refresh"),
        # New unified auth endpoints under /api/v1/auth/* for the frontend
        path("api/v1/auth/login/", CustomTokenObtainPairView.as_view(), name="api_v1_auth_login"),
        path("api/v1/auth/refresh/", CustomTokenRefreshView.as_view(), name="api_v1_auth_refresh"),
        path("api/v1/auth/logout/", api_logout, name="api_v1_auth_logout"),
    ]

# django-rq dashboard (development only for now)
if settings.DEBUG:
    urlpatterns += [
        path("django-rq/", include("django_rq.urls")),
    ]