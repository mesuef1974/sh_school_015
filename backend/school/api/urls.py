from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .viewsets import (
    ClassViewSet,
    StudentViewSet,
    StaffViewSet,
    SubjectViewSet,
    TeachingAssignmentViewSet,
    ClassSubjectViewSet,
)

router = DefaultRouter()
router.register(r"classes", ClassViewSet)
router.register(r"students", StudentViewSet)
router.register(r"staff", StaffViewSet)
router.register(r"subjects", SubjectViewSet)
router.register(r"class-subjects", ClassSubjectViewSet)
router.register(r"teaching-assignments", TeachingAssignmentViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
