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
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from school.views import (
    ClassViewSet,
    StudentViewSet,
    StaffViewSet,
    SubjectViewSet,
    TeachingAssignmentViewSet,
    ClassSubjectViewSet,
)
from rest_framework_simplejwt.views import TokenRefreshView
from school.auth import CustomTokenObtainPairView

router = DefaultRouter()
router.register(r"classes", ClassViewSet)
router.register(r"students", StudentViewSet)
router.register(r"staff", StaffViewSet)
router.register(r"subjects", SubjectViewSet)
router.register(r"class-subjects", ClassSubjectViewSet)
router.register(r"teaching-assignments", TeachingAssignmentViewSet)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("school.urls")),
    path("api/", include(router.urls)),
    path("api/token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]
