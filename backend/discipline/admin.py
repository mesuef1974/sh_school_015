from django.contrib import admin
from .models import BehaviorLevel, Violation, Incident


@admin.register(BehaviorLevel)
class BehaviorLevelAdmin(admin.ModelAdmin):
    list_display = ("code", "name")
    search_fields = ("code", "name")


@admin.register(Violation)
class ViolationAdmin(admin.ModelAdmin):
    list_display = ("code", "category", "severity", "requires_committee")
    list_filter = ("severity", "requires_committee")
    search_fields = ("code", "category", "description")
    autocomplete_fields = ("level",)


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ("id", "violation", "student", "occurred_at", "status")
    list_filter = ("status", "severity", "committee_required")
    search_fields = ("id", "narrative", "location", "violation__code", "violation__category")
    autocomplete_fields = ("violation", "student", "reporter")
    readonly_fields = ("created_at", "updated_at")