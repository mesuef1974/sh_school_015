from rest_framework import serializers
from school.models import Student, ExitEvent  # type: ignore


class StudentBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = [
            "id",
            "sid",
            "full_name",
            "class_fk_id",
            "active",
        ]


class ExitEventSerializer(serializers.ModelSerializer):
    # Allow both student/student_id and classroom/class_id for frontend flexibility
    student_id = serializers.IntegerField(write_only=True, required=False)
    class_id = serializers.IntegerField(write_only=True, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dynamically set up PrimaryKeyRelatedFields for ForeignKeys
        # This allows accepting integer IDs and converting to model instances
        from school.models import Class

        self.fields["student"] = serializers.PrimaryKeyRelatedField(
            queryset=Student.objects.all(), required=False
        )
        self.fields["classroom"] = serializers.PrimaryKeyRelatedField(
            queryset=Class.objects.all(), required=False, allow_null=True
        )

    class Meta:
        model = ExitEvent
        fields = [
            "id",
            "student",
            "student_id",
            "classroom",
            "class_id",
            "date",
            "period_number",
            "reason",
            "note",
            "started_at",
            "returned_at",
            "duration_seconds",
        ]
        read_only_fields = ["started_at", "returned_at", "duration_seconds"]
        extra_kwargs = {
            "note": {"required": False, "allow_blank": True, "allow_null": True},
        }

    def validate(self, data):
        # Ensure at least one student field is provided
        if "student" not in data and "student_id" not in data:
            raise serializers.ValidationError({"student": "student or student_id is required"})

        # Normalize student_id -> student
        # IMPORTANT: We need to let the PrimaryKeyRelatedField handle the conversion
        # So we run the field's to_internal_value to convert ID to instance
        if "student_id" in data and "student" not in data:
            student_id = data.pop("student_id")
            # Use the student field's to_internal_value to get the instance
            data["student"] = self.fields["student"].to_internal_value(student_id)
        elif "student_id" in data:
            data.pop("student_id")  # Remove duplicate if both present

        # Normalize class_id -> classroom
        if "class_id" in data and "classroom" not in data:
            classroom_id = data.pop("class_id")
            if classroom_id is not None:
                # Use the classroom field's to_internal_value to get the instance
                data["classroom"] = self.fields["classroom"].to_internal_value(classroom_id)
        elif "class_id" in data:
            data.pop("class_id")  # Remove duplicate if both present

        # Convert null note to empty string (model doesn't allow null)
        if data.get("note") is None:
            data["note"] = ""

        return data