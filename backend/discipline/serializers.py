from rest_framework import serializers
from .models import Violation, Incident, BehaviorLevel


class BehaviorLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = BehaviorLevel
        fields = "__all__"


class ViolationSerializer(serializers.ModelSerializer):
    level = BehaviorLevelSerializer(read_only=True)

    class Meta:
        model = Violation
        fields = "__all__"


class IncidentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Incident
        fields = "__all__"
        read_only_fields = (
            "reporter",
            "severity",
            "committee_required",
            "submitted_at",
            "reviewed_by",
            "reviewed_at",
            "closed_by",
            "closed_at",
            "actions_applied",
            "sanctions_applied",
            "escalated_due_to_repeat",
            "status",
        )

    def create(self, validated_data):
        violation = validated_data["violation"]
        validated_data["severity"] = violation.severity
        # committee flag inherited, but may be escalated later on submit
        validated_data["committee_required"] = violation.requires_committee
        return super().create(validated_data)

    # Inject human-friendly display fields without altering DB schema or write contract
    def to_representation(self, instance):
        from django.utils import timezone
        from datetime import timedelta

        data = super().to_representation(instance)
        try:
            data["student_name"] = getattr(getattr(instance, "student", None), "full_name", None)
        except Exception:
            data["student_name"] = None
        try:
            # Use the reporter's real name from Staff table if available; otherwise use user full name.
            reporter = getattr(instance, "reporter", None)
            name = None
            if reporter:
                # 1) Preferred: Staff.full_name linked to this user (Arabic real name used across the app)
                try:
                    from school.models import Staff  # type: ignore

                    staff_name = (
                        Staff.objects.filter(user=reporter)
                        .only("full_name")
                        .values_list("full_name", flat=True)
                        .first()
                    )
                    if staff_name:
                        name = staff_name
                except Exception:
                    pass
                # 2) Fallbacks on the User object
                if not name and hasattr(reporter, "get_full_name"):
                    name = reporter.get_full_name() or None
                if not name:
                    name = getattr(reporter, "full_name", None)
                if not name:
                    # Compose from first/last names if available
                    fn = getattr(reporter, "first_name", None)
                    ln = getattr(reporter, "last_name", None)
                    if fn or ln:
                        name = ((fn or "").strip() + " " + (ln or "").strip()).strip() or None
            data["reporter_name"] = name
        except Exception:
            data["reporter_name"] = None
        try:
            viol = getattr(instance, "violation", None)
            code = getattr(viol, "code", None)
            cat = getattr(viol, "category", None)
            data["violation_code"] = code
            data["violation_category"] = cat
            data["violation_display"] = f"{code} — {cat}" if code or cat else None
        except Exception:
            data["violation_code"] = None
            data["violation_category"] = None
            data["violation_display"] = None
        # Class name (الفصل) derived from student's current class
        try:
            data["class_name"] = getattr(getattr(getattr(instance, "student", None), "class_fk", None), "name", None)
        except Exception:
            data["class_name"] = None
        try:
            actions = getattr(instance, "actions_applied", None) or []
            sanctions = getattr(instance, "sanctions_applied", None) or []
            data["actions_count"] = len(actions)
            data["sanctions_count"] = len(sanctions)
        except Exception:
            data["actions_count"] = 0
            data["sanctions_count"] = 0
        # SLA helper fields
        try:
            from django.conf import settings as dj_settings

            submitted_at = getattr(instance, "submitted_at", None)
            if submitted_at:
                review_due = submitted_at + timedelta(hours=getattr(dj_settings, "DISCIPLINE_REVIEW_SLA_H", 24))
                notify_due = submitted_at + timedelta(hours=getattr(dj_settings, "DISCIPLINE_NOTIFY_SLA_H", 48))
                now = timezone.now()
                data["review_sla_due_at"] = review_due.isoformat()
                data["notify_sla_due_at"] = notify_due.isoformat()
                data["is_overdue_review"] = bool(now > review_due and instance.status == "under_review")
                data["is_overdue_notify"] = bool(now > notify_due and instance.status == "under_review")
            else:
                data["review_sla_due_at"] = None
                data["notify_sla_due_at"] = None
                data["is_overdue_review"] = False
                data["is_overdue_notify"] = False
        except Exception:
            data["review_sla_due_at"] = None
            data["notify_sla_due_at"] = None
            data["is_overdue_review"] = False
            data["is_overdue_notify"] = False
        # Time-only field for convenience (HH:MM)
        try:
            occ = getattr(instance, "occurred_at", None)
            if occ:
                data["occurred_time"] = occ.strftime("%H:%M")
            else:
                data["occurred_time"] = None
        except Exception:
            data["occurred_time"] = None
        # Severity color
        try:
            sev = int(getattr(instance, "severity", 1) or 1)
            color = {1: "#2e7d32", 2: "#f9a825", 3: "#fb8c00", 4: "#c62828"}.get(sev, "#2e7d32")
            data["level_color"] = color
        except Exception:
            data["level_color"] = "#2e7d32"
        return data
