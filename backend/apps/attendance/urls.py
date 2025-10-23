from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .api import AttendanceViewSetV2 as AttendanceViewSet
from .api import ExitEventViewSet

router = DefaultRouter()
router.register(r"attendance", AttendanceViewSet, basename="attendance")
router.register(r"attendance/exit-events", ExitEventViewSet, basename="exit-events")
from .api import WingSupervisorViewSet
router.register(r"wing", WingSupervisorViewSet, basename="wing")

urlpatterns = [
    path("", include(router.urls)),
]