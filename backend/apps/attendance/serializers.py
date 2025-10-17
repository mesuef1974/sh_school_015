from rest_framework import serializers
from school.models import Student  # type: ignore


class StudentBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = [
            "id",
            "sid",
            "full_name",
            "class_fk_id",
        ]
