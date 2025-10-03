from rest_framework import serializers
from .models import Class, Student, Staff, Subject, TeachingAssignment, ClassSubject


class ClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = Class
        fields = "__all__"


class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = "__all__"


class StaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = Staff
        fields = "__all__"


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = "__all__"


class TeachingAssignmentSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source="teacher.full_name", read_only=True)
    class_name = serializers.CharField(source="classroom.name", read_only=True)
    subject_name = serializers.CharField(source="subject.name_ar", read_only=True)

    class Meta:
        model = TeachingAssignment
        fields = [
            "id",
            "teacher",
            "teacher_name",
            "classroom",
            "class_name",
            "subject",
            "subject_name",
            "no_classes_weekly",
            "notes",
            "created_at",
            "updated_at",
        ]


class ClassSubjectSerializer(serializers.ModelSerializer):
    class_name = serializers.CharField(source="classroom.name", read_only=True)
    subject_name = serializers.CharField(source="subject.name_ar", read_only=True)

    class Meta:
        model = ClassSubject
        fields = [
            "id",
            "classroom",
            "class_name",
            "subject",
            "subject_name",
            "weekly_default",
        ]


# --- Calendar serializers ---
from .models import CalendarTemplate, CalendarSlot  # noqa: E402


class CalendarSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalendarSlot
        fields = [
            "id",
            "day",
            "period_index",
            "start_time",
            "end_time",
            "block",
            "order",
        ]


class CalendarTemplateSerializer(serializers.ModelSerializer):
    slots = CalendarSlotSerializer(many=True, read_only=True)

    class Meta:
        model = CalendarTemplate
        fields = ["id", "name", "scope", "days", "slots"]
