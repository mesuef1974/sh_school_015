from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from school.models import (
    Class,
    Student,
    Staff,
    Subject,
    TeachingAssignment,
    ClassSubject,
)
from school.serializers import (
    ClassSerializer,
    StudentSerializer,
    StaffSerializer,
    SubjectSerializer,
    TeachingAssignmentSerializer,
    ClassSubjectSerializer,
)


class ClassViewSet(ModelViewSet):
    queryset = Class.objects.all()
    serializer_class = ClassSerializer
    permission_classes = [IsAuthenticated]


class StudentViewSet(ModelViewSet):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    permission_classes = [IsAuthenticated]


class StaffViewSet(ModelViewSet):
    queryset = Staff.objects.all()
    serializer_class = StaffSerializer
    permission_classes = [IsAuthenticated]


class SubjectViewSet(ModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    permission_classes = [IsAuthenticated]


class ClassSubjectViewSet(ModelViewSet):
    queryset = ClassSubject.objects.select_related("classroom", "subject").all()
    serializer_class = ClassSubjectSerializer
    permission_classes = [IsAuthenticated]


class TeachingAssignmentViewSet(ModelViewSet):
    queryset = TeachingAssignment.objects.select_related("teacher", "classroom", "subject").all()
    serializer_class = TeachingAssignmentSerializer
    permission_classes = [IsAuthenticated]
