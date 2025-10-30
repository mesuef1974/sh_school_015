from __future__ import annotations
from rest_framework import serializers

from school.models import Student  # type: ignore
from .models_alerts import AbsenceAlert


class AbsenceAlertSerializer(serializers.ModelSerializer):
    student_id = serializers.IntegerField(required=False)
    student_name = serializers.CharField(source="student.full_name", read_only=True)

    class Meta:
        model = AbsenceAlert
        fields = [
            "id",
            "number",
            "academic_year",
            "student",
            "student_id",
            "student_name",
            "class_name",
            "parent_name",
            "parent_mobile",
            "period_start",
            "period_end",
            "excused_days",
            "unexcused_days",
            "notes",
            "status",
            "wing",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "number",
            "academic_year",
            "excused_days",
            "unexcused_days",
            "wing",
            "created_at",
            "updated_at",
        ]

    def validate(self, data):
        if "student" not in data and "student_id" not in data:
            raise serializers.ValidationError({"student": "student or student_id is required"})
        if "student_id" in data and "student" not in data:
            sid = data.pop("student_id")
            data["student"] = Student.objects.get(pk=sid)
        elif "student_id" in data:
            data.pop("student_id")
        return data
