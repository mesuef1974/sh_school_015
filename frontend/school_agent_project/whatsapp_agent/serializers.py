from rest_framework import serializers
from .models import Person, MessageLog, ReplyTemplate


class PersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Person
        fields = "__all__"


class MessageLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageLog
        fields = "__all__"


class ReplyTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReplyTemplate
        fields = "__all__"
