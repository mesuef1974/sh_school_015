from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api import AttendanceViewSetBase
from .api import AttendanceViewSetV2 as AttendanceViewSet
from .api import ExitEventViewSet, WingSupervisorViewSet
from .api_alerts import AbsenceAlertViewSet, AbsenceComputeViewSet

router = DefaultRouter()
router.register(r"attendance", AttendanceViewSet, basename="attendance")
router.register(r"attendance/exit-events", ExitEventViewSet, basename="exit-events")
router.register(r"wing", WingSupervisorViewSet, basename="wing")
router.register(r"absence-alerts", AbsenceAlertViewSet, basename="absence-alerts")
router.register(r"attendance/absence", AbsenceComputeViewSet, basename="attendance-absence")

# Compatibility alias for teacher submit endpoint not present on V2 ViewSet
attendance_submit = AttendanceViewSetBase.as_view({"post": "submit_for_review"})

urlpatterns = [
    path("", include(router.urls)),
    # Expose POST /api/v1/attendance/submit/ to match frontend expectation
    path("attendance/submit/", attendance_submit),
]
