from django.contrib import admin
from django import forms
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
    class ViolationPolicyForm(forms.ModelForm):
        """تحقق من صحة حقل السياسة policy ضمن نموذج Violation في لوحة الإدارة."""

        class Meta:
            model = Violation
            fields = "__all__"

        def clean_policy(self):
            import numbers

            policy = self.cleaned_data.get("policy")
            if policy in (None, ""):
                return {}
            if not isinstance(policy, dict):
                raise forms.ValidationError("يجب أن تكون السياسة كائن JSON (قاموس)")

            allowed_keys = {
                "window_days",
                "committee",
                "escalation",
                "actions_by_repeat",
                "sanctions_by_repeat",
                "points_by_repeat",
            }
            for k in policy.keys():
                if k not in allowed_keys:
                    raise forms.ValidationError(f"مفتاح غير معروف في السياسة: {k}")

            # window_days
            if "window_days" in policy and policy["window_days"] is not None:
                wd = policy["window_days"]
                if not isinstance(wd, numbers.Integral) or int(wd) <= 0:
                    raise forms.ValidationError("window_days يجب أن يكون عددًا صحيحًا موجبًا")

            # committee
            committee = policy.get("committee")
            if committee is not None:
                if not isinstance(committee, dict):
                    raise forms.ValidationError("committee يجب أن يكون كائن JSON")
                rsev = committee.get("requires_on_severity_gte")
                if rsev is not None:
                    if not isinstance(rsev, numbers.Integral) or not (1 <= int(rsev) <= 4):
                        raise forms.ValidationError("committee.requires_on_severity_gte يجب أن يكون رقمًا بين 1 و4")
                arep = committee.get("after_repeats")
                if arep is not None:
                    if not isinstance(arep, numbers.Integral) or int(arep) < 1:
                        raise forms.ValidationError("committee.after_repeats يجب أن يكون عددًا صحيحًا ≥ 1")

            # escalation
            esc = policy.get("escalation")
            if esc is not None:
                if not isinstance(esc, dict):
                    raise forms.ValidationError("escalation يجب أن يكون كائن JSON")
                arep = esc.get("after_repeats")
                if arep is not None:
                    if not isinstance(arep, numbers.Integral) or int(arep) < 1:
                        raise forms.ValidationError("escalation.after_repeats يجب أن يكون عددًا صحيحًا ≥ 1")

            # actions_by_repeat / sanctions_by_repeat: {"0": ["action1", ...]}
            def validate_repeat_map(name: str):
                m = policy.get(name)
                if m is None:
                    return
                if not isinstance(m, dict):
                    raise forms.ValidationError(f"{name} يجب أن يكون كائنًا (قاموس)")
                for sk, arr in m.items():
                    # keys can be strings or ints convertible to int ≥ 0
                    try:
                        rk = int(sk)
                    except Exception:
                        raise forms.ValidationError(f"مفتاح غير صالح في {name}: {sk}")
                    if rk < 0:
                        raise forms.ValidationError(f"مفتاح {rk} في {name} يجب أن يكون ≥ 0")
                    if not isinstance(arr, (list, tuple)):
                        raise forms.ValidationError(f"قيمة {name}[{rk}] يجب أن تكون قائمة")
                    for i, v in enumerate(arr):
                        if not isinstance(v, str) or not v.strip():
                            raise forms.ValidationError(f"العنصر رقم {i} في {name}[{rk}] يجب أن يكون نصًا غير فارغ")

            validate_repeat_map("actions_by_repeat")
            validate_repeat_map("sanctions_by_repeat")

            # points_by_repeat: {"0": 1, "1": 3}
            pmap = policy.get("points_by_repeat")
            if pmap is not None:
                if not isinstance(pmap, dict):
                    raise forms.ValidationError("points_by_repeat يجب أن يكون كائنًا (قاموس)")
                for sk, val in pmap.items():
                    try:
                        rk = int(sk)
                    except Exception:
                        raise forms.ValidationError(f"مفتاح غير صالح في points_by_repeat: {sk}")
                    if rk < 0:
                        raise forms.ValidationError(f"مفتاح {rk} في points_by_repeat يجب أن يكون ≥ 0")
                    import numbers as _n

                    if not isinstance(val, _n.Integral) or int(val) < 0:
                        raise forms.ValidationError(f"القيمة في points_by_repeat[{rk}] يجب أن تكون رقمًا صحيحًا ≥ 0")

            return policy

    form = ViolationPolicyForm
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
    search_fields = ("incident__id", "actor__username", "actor__staff__full_name", "note")
    autocomplete_fields = ("incident", "actor")


@admin.register(IncidentCommittee)
class IncidentCommitteeAdmin(admin.ModelAdmin):
    list_display = ("incident", "chair", "scheduled_by", "scheduled_at")
    search_fields = (
        "incident__id",
        "chair__username",
        "chair__staff__full_name",
        "recorder__username",
        "recorder__staff__full_name",
    )
    autocomplete_fields = ("incident", "chair", "recorder", "scheduled_by")


@admin.register(IncidentCommitteeMember)
class IncidentCommitteeMemberAdmin(admin.ModelAdmin):
    list_display = ("committee", "user")
    search_fields = (
        "committee__incident__id",
        "user__username",
        "user__staff__full_name",
    )
    autocomplete_fields = ("committee", "user")


@admin.register(StandingCommittee)
class StandingCommitteeAdmin(admin.ModelAdmin):
    list_display = ("id", "chair", "recorder", "updated_at")
    search_fields = (
        "chair__username",
        "chair__staff__full_name",
        "recorder__username",
        "recorder__staff__full_name",
    )
    autocomplete_fields = ("chair", "recorder")


@admin.register(StandingCommitteeMember)
class StandingCommitteeMemberAdmin(admin.ModelAdmin):
    list_display = ("standing", "user")
    search_fields = ("standing__id", "user__username")
    autocomplete_fields = ("standing", "user")
