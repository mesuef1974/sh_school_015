from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .api import AttendanceViewSetV2 as AttendanceViewSet

router = DefaultRouter()
router.register(r"attendance", AttendanceViewSet, basename="attendance")

urlpatterns = [
    path("", include(router.urls)),
]
