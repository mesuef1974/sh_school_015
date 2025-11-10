from rest_framework import serializers
from apps.accounts.models import User
from apps.school.models import Grade, Subject, Class


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "role", "phone", "address"]
        extra_kwargs = {"password": {"write_only": True}}


class GradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Grade
        fields = "__all__"


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = "__all__"


class ClassSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source="teacher.get_full_name", read_only=True)

    class Meta:
        model = Class
        fields = ["id", "name", "grade", "subjects", "teacher", "teacher_name"]
