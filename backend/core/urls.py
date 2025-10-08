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
from rest_framework.routers import DefaultRouter
from school.views import (
    ClassViewSet,
    StudentViewSet,
    StaffViewSet,
    SubjectViewSet,
    TeachingAssignmentViewSet,
    ClassSubjectViewSet,
    CalendarTemplateViewSet,
    CalendarSlotViewSet,
)
from rest_framework_simplejwt.views import TokenRefreshView
from school.auth import CustomTokenObtainPairView
from pathlib import Path

# Paths outside backend/ we might want to expose during development (DEBUG)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOC_DIR = PROJECT_ROOT / "DOC"
BACKEND_DIR = PROJECT_ROOT / "backend"
PROJECT_ROOT_DIR = PROJECT_ROOT  # for serving index.html

router = DefaultRouter()
router.register(r"classes", ClassViewSet)
router.register(r"students", StudentViewSet)
router.register(r"staff", StaffViewSet)
router.register(r"subjects", SubjectViewSet)
router.register(r"class-subjects", ClassSubjectViewSet)
router.register(r"teaching-assignments", TeachingAssignmentViewSet)
router.register(r"calendar-templates", CalendarTemplateViewSet)
router.register(r"calendar-slots", CalendarSlotViewSet)

urlpatterns = [
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
        path("api/", include(router.urls)),
        path("api-auth/", include("rest_framework.urls")),
        path("api/token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
        path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    ]
else:
    urlpatterns += [
        path("api/", include(router.urls)),
        path("api/token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
        path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    ]
