from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, GradeViewSet, SubjectViewSet, ClassViewSet

router = DefaultRouter()
router.register(r"users", UserViewSet)
router.register(r"grades", GradeViewSet)
router.register(r"subjects", SubjectViewSet)
router.register(r"classes", ClassViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
