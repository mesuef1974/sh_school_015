from rest_framework.routers import DefaultRouter
from .views import ViolationViewSet, IncidentViewSet, BehaviorLevelViewSet

router = DefaultRouter()
router.register(r"discipline/behavior-levels", BehaviorLevelViewSet, basename="behavior-level")
router.register(r"discipline/violations", ViolationViewSet, basename="violation")
router.register(r"discipline/incidents", IncidentViewSet, basename="incident")

urlpatterns = router.urls