from django.contrib import admin
from .models import Person, MessageLog, ReplyTemplate, EscalationTicket


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "role", "student_id", "is_active")
    search_fields = ("name", "phone", "student_id")


@admin.register(ReplyTemplate)
class ReplyTemplateAdmin(admin.ModelAdmin):
    list_display = ("intent", "text_template", "is_active", "created_at")
    search_fields = ("intent", "text_template")


@admin.register(MessageLog)
class MessageLogAdmin(admin.ModelAdmin):
    list_display = ("phone", "direction", "intent", "created_at")
    search_fields = ("phone", "content")


@admin.register(EscalationTicket)
class EscalationAdmin(admin.ModelAdmin):
    list_display = ("original_message", "assigned_to", "status", "created_at")
    search_fields = ("assigned_to", "status")
