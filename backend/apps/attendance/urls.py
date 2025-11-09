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

# Explicit alias for students DOCX export to avoid router regex quirks
students_export_docx = WingSupervisorViewSet.as_view({"get": "students_export_docx"})

urlpatterns = [
    path("", include(router.urls)),
    # Expose GET /api/v1/attendance/class/students/ expected by frontend IncidentForm
    path("attendance/class/students/", AttendanceViewSetBase.as_view({"get": "list_students"})),
    path(
        "attendance/class/students", AttendanceViewSetBase.as_view({"get": "list_students"})
    ),  # alias without trailing slash
    # Expose POST /api/v1/attendance/submit/ to match frontend expectation
    path("attendance/submit/", attendance_submit),
    # Stable endpoint for Word export of wing students (matches frontend href)
    path("wing/students/export.docx/", students_export_docx),
    # Tolerant alias without trailing slash to avoid 404s in case of mismatched client URLs
    path("wing/students/export.docx", students_export_docx),
    # Additional alias without dot to avoid any reverse-proxy or router quirks
    path("wing/students/export-docx/", students_export_docx),
    path("wing/students/export-docx", students_export_docx),
    # Weekly summary (DOCX) stable endpoint (router action with regex path)
    path(
        "wing/weekly-summary/export.docx/",
        WingSupervisorViewSet.as_view({"get": "weekly_summary_export_docx"}),
    ),
    path(
        "wing/weekly-summary/export.docx",
        WingSupervisorViewSet.as_view({"get": "weekly_summary_export_docx"}),
    ),
]
