from django.contrib import admin
from .models import (
    BehaviorLevel,
    Violation,
    Incident,
    IncidentAuditLog,
    IncidentCommittee,
    IncidentCommitteeMember,
    StandingCommittee,
    StandingCommitteeMember,
)


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
    list_display = (
        "id",
        "violation",
        "student",
        "reporter",
        "occurred_at",
        "status",
        "committee_required",
    )
    list_filter = ("status", "severity", "committee_required")
    search_fields = (
        "id",
        "narrative",
        "location",
        "violation__code",
        "violation__category",
        "reporter__username",
        "reporter__first_name",
        "reporter__last_name",
    )
    autocomplete_fields = ("violation", "student", "reporter")
    readonly_fields = (
        "created_at",
        "updated_at",
        "committee_required",
        "committee_scheduled_by",
        "committee_scheduled_at",
        "committee_panel_pretty",
    )
    list_select_related = ("violation", "student", "reporter")

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "violation",
                    "student",
                    "reporter",
                    "occurred_at",
                    "location",
                    "narrative",
                    "status",
                    "severity",
                    "created_at",
                    "updated_at",
                )
            },
        ),
        (
            "مسار اللجنة السلوكية",
            {
                "classes": ("collapse",),
                "fields": (
                    "committee_required",
                    "committee_scheduled_by",
                    "committee_scheduled_at",
                    "committee_panel_pretty",
                ),
                "description": "عرض للحقول المتعلقة باللجنة. يتم تشكيل اللجنة وحفظها عبر واجهة الويب أو واجهات API الخاصة بالباكند (schedule-committee).",
            },
        ),
    )

    def committee_panel_pretty(self, obj):  # pragma: no cover - admin UI only
        import json

        try:
            panel = getattr(obj, "committee_panel", None) or {}
            return json.dumps(panel, ensure_ascii=False, indent=2)
        except Exception:
            return "{}"

    committee_panel_pretty.short_description = "تشكيلة اللجنة (JSON)"


class IncidentAuditInline(admin.TabularInline):
    model = IncidentAuditLog
    extra = 0
    fields = ("action", "actor", "at", "from_status", "to_status", "note")
    readonly_fields = ("action", "actor", "at", "from_status", "to_status", "note")
    can_delete = False


class IncidentCommitteeInline(admin.StackedInline):
    model = IncidentCommittee
    extra = 0
    can_delete = False
    autocomplete_fields = ("chair", "recorder", "scheduled_by")


IncidentAdmin.inlines = [IncidentCommitteeInline, IncidentAuditInline]


@admin.register(IncidentAuditLog)
class IncidentAuditLogAdmin(admin.ModelAdmin):
    list_display = ("id", "incident", "action", "actor", "at", "from_status", "to_status")
    list_filter = ("action", "from_status", "to_status")
    search_fields = ("incident__id", "actor__username", "note")
    autocomplete_fields = ("incident", "actor")


@admin.register(IncidentCommittee)
class IncidentCommitteeAdmin(admin.ModelAdmin):
    list_display = ("incident", "chair", "scheduled_by", "scheduled_at")
    search_fields = ("incident__id", "chair__username")
    autocomplete_fields = ("incident", "chair", "recorder", "scheduled_by")


@admin.register(IncidentCommitteeMember)
class IncidentCommitteeMemberAdmin(admin.ModelAdmin):
    list_display = ("committee", "user")
    search_fields = ("committee__incident__id", "user__username")
    autocomplete_fields = ("committee", "user")


@admin.register(StandingCommittee)
class StandingCommitteeAdmin(admin.ModelAdmin):
    list_display = ("id", "chair", "recorder", "updated_at")
    search_fields = ("chair__username", "recorder__username")
    autocomplete_fields = ("chair", "recorder")


@admin.register(StandingCommitteeMember)
class StandingCommitteeMemberAdmin(admin.ModelAdmin):
    list_display = ("standing", "user")
    search_fields = ("standing__id", "user__username")
    autocomplete_fields = ("standing", "user")
