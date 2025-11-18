from rest_framework.routers import DefaultRouter
from .views import (
    ViolationViewSet,
    IncidentViewSet,
    BehaviorLevelViewSet,
    AbsenceViewSet,
    ExcuseRequestViewSet,
)

router = DefaultRouter()
router.register(r"discipline/behavior-levels", BehaviorLevelViewSet, basename="behavior-level")
router.register(r"discipline/violations", ViolationViewSet, basename="violation")
router.register(r"discipline/incidents", IncidentViewSet, basename="incident")
router.register(r"discipline/attendance/absences", AbsenceViewSet, basename="absence")
router.register(r"discipline/attendance/excuses", ExcuseRequestViewSet, basename="excuse-request")

urlpatterns = router.urls
