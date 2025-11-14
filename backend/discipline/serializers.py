from rest_framework import serializers
from .models import Violation, Incident, BehaviorLevel
from typing import Any, Dict


class BehaviorLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = BehaviorLevel
        fields = "__all__"


class ViolationSerializer(serializers.ModelSerializer):
    level = BehaviorLevelSerializer(read_only=True)

    class Meta:
        model = Violation
        # Exclude 'policy' for backward compatibility with databases that
        # haven't added the column yet. Frontend dropdowns and listings only
        # require these core fields.
        fields = (
            "id",
            "level",
            "code",
            "category",
            "description",
            "default_actions",
            "default_sanctions",
            "severity",
            "requires_committee",
        )


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
        # أسماء المراجِع والمغلق (إن وُجدا) باعتماد Staff.full_name إن توفر
        try:
            reviewer = getattr(instance, "reviewed_by", None)
            r_name = None
            if reviewer:
                try:
                    from school.models import Staff  # type: ignore

                    r_name = (
                        Staff.objects.filter(user=reviewer)
                        .only("full_name")
                        .values_list("full_name", flat=True)
                        .first()
                    ) or None
                except Exception:
                    r_name = None
                if not r_name and hasattr(reviewer, "get_full_name"):
                    r_name = reviewer.get_full_name() or None
            data["reviewed_by_name"] = r_name
        except Exception:
            data["reviewed_by_name"] = None
        try:
            closer = getattr(instance, "closed_by", None)
            c_name = None
            if closer:
                try:
                    from school.models import Staff  # type: ignore

                    c_name = (
                        Staff.objects.filter(user=closer).only("full_name").values_list("full_name", flat=True).first()
                    ) or None
                except Exception:
                    c_name = None
                if not c_name and hasattr(closer, "get_full_name"):
                    c_name = closer.get_full_name() or None
            data["closed_by_name"] = c_name
        except Exception:
            data["closed_by_name"] = None
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


class IncidentFullSerializer(IncidentSerializer):
    """تمثيل "كامل" للواقعة مع إغناء شامل من قواعد البيانات ذات الصلة.

    يحافظ على عقد الكتابة نفسه، لكنه عند القراءة يضيف:
    - violation_obj: الكائن الكامل للمخالفة (باستخدام ViolationSerializer)
    - reporter_obj: بيانات أساسية عن المستخدم المُبلِّغ
    - student_obj: بيانات الطالب مع معلومات الصف والجناح المرتبطين
    - class_obj: ملخص الصف المرتبط (إن وُجد)
    - wing_obj: ملخص الجناح المرتبط (إن وُجد)
    """

    def to_representation(self, instance: Incident) -> Dict[str, Any]:
        base = super().to_representation(instance)
        # violation full
        try:
            base["violation_obj"] = (
                ViolationSerializer(getattr(instance, "violation", None)).data
                if getattr(instance, "violation", None)
                else None
            )
        except Exception:
            base["violation_obj"] = None
        # reporter basic
        try:
            u = getattr(instance, "reporter", None)
            if u is not None:
                full_name = None
                staff_full_name = None
                try:
                    full_name = u.get_full_name() or None
                except Exception:
                    full_name = None
                # حاول جلب اسم الموظف من جدول Staff المرتبط بهذا المستخدم
                try:
                    from school.models import Staff  # type: ignore

                    staff_full_name = (
                        Staff.objects.filter(user=u).only("full_name").values_list("full_name", flat=True).first()
                    ) or None
                except Exception:
                    staff_full_name = None
                base["reporter_obj"] = {
                    "id": getattr(u, "id", None),
                    "username": getattr(u, "username", None),
                    "full_name": full_name or getattr(u, "first_name", None) or getattr(u, "last_name", None),
                    "is_staff": bool(getattr(u, "is_staff", False)),
                    "staff_full_name": staff_full_name,
                }
            else:
                base["reporter_obj"] = None
        except Exception:
            base["reporter_obj"] = None
        # student and class/wing
        try:
            student = getattr(instance, "student", None)
            if student is not None:
                cls = getattr(student, "class_fk", None)
                wing = getattr(cls, "wing", None) if cls is not None else None
                base["student_obj"] = {
                    "id": getattr(student, "id", None),
                    "sid": getattr(student, "sid", None),
                    "full_name": getattr(student, "full_name", None),
                    "class_id": getattr(cls, "id", None) if cls is not None else None,
                    "class_name": getattr(cls, "name", None) if cls is not None else None,
                    "wing_id": (
                        getattr(wing, "id", None)
                        if wing is not None
                        else getattr(getattr(cls, "wing", None), "id", None)
                    ),
                }
                base["class_obj"] = (
                    {
                        "id": getattr(cls, "id", None),
                        "name": getattr(cls, "name", None),
                        "grade": getattr(cls, "grade", None),
                        "section": getattr(cls, "section", None),
                        "wing_id": getattr(getattr(cls, "wing", None), "id", None),
                    }
                    if cls is not None
                    else None
                )
                base["wing_obj"] = (
                    {
                        "id": getattr(getattr(cls, "wing", None), "id", None),
                        "name": getattr(getattr(cls, "wing", None), "name", None),
                    }
                    if cls is not None and getattr(cls, "wing", None) is not None
                    else None
                )
            else:
                base["student_obj"] = None
                base["class_obj"] = None
                base["wing_obj"] = None
        except Exception:
            base["student_obj"] = None
            base["class_obj"] = None
            base["wing_obj"] = None
        # أضف حقلًا مقروءًا مشتقًا من جداول اللجنة الجديدة (أو JSON كاحتياط)
        try:
            base["committee_panel_obj"] = self.get_committee_panel_obj(instance)
        except Exception:
            base["committee_panel_obj"] = None
        # أضف كائنات المراجع والمغلق مع اسم الموظف إن وُجد
        try:
            reviewer = getattr(instance, "reviewed_by", None)
            if reviewer is not None:
                rv_full = None
                try:
                    rv_full = reviewer.get_full_name() or None
                except Exception:
                    rv_full = None
                # Staff full name
                rv_staff = None
                try:
                    from school.models import Staff  # type: ignore

                    rv_staff = (
                        Staff.objects.filter(user=reviewer)
                        .only("full_name")
                        .values_list("full_name", flat=True)
                        .first()
                    ) or None
                except Exception:
                    rv_staff = None
                base["reviewer_obj"] = {
                    "id": getattr(reviewer, "id", None),
                    "username": getattr(reviewer, "username", None),
                    "full_name": rv_full,
                    "staff_full_name": rv_staff,
                }
            else:
                base["reviewer_obj"] = None
        except Exception:
            base["reviewer_obj"] = None
        try:
            closer = getattr(instance, "closed_by", None)
            if closer is not None:
                cl_full = None
                try:
                    cl_full = closer.get_full_name() or None
                except Exception:
                    cl_full = None
                cl_staff = None
                try:
                    from school.models import Staff  # type: ignore

                    cl_staff = (
                        Staff.objects.filter(user=closer).only("full_name").values_list("full_name", flat=True).first()
                    ) or None
                except Exception:
                    cl_staff = None
                base["closed_by_obj"] = {
                    "id": getattr(closer, "id", None),
                    "username": getattr(closer, "username", None),
                    "full_name": cl_full,
                    "staff_full_name": cl_staff,
                }
            else:
                base["closed_by_obj"] = None
        except Exception:
            base["closed_by_obj"] = None
        return base

    # إرجاع تشكيل اللجنة من الجداول الجديدة إن توفّر (قراءة فقط)
    def get_committee_panel_obj(self, instance: Incident) -> Dict[str, Any]:  # pragma: no cover - helper
        try:
            committee = getattr(instance, "committee", None)
            if not committee:
                # Fallback إلى JSON المخزن إن وجد
                panel = getattr(instance, "committee_panel", None) or {}
                return {
                    "chair_id": panel.get("chair_id"),
                    "member_ids": panel.get("member_ids") or [],
                    "recorder_id": panel.get("recorder_id"),
                }
            # من الجداول
            members_qs = committee.members.select_related("user").all()
            member_ids = [m.user_id for m in members_qs]
            return {
                "chair_id": getattr(committee, "chair_id", None),
                "member_ids": member_ids,
                "recorder_id": getattr(committee, "recorder_id", None),
            }
        except Exception:
            panel = getattr(instance, "committee_panel", None) or {}
            return {
                "chair_id": panel.get("chair_id"),
                "member_ids": panel.get("member_ids") or [],
                "recorder_id": panel.get("recorder_id"),
            }

    # ملاحظة: تم دمج إرجاع committee_panel_obj ضمن to_representation أعلاه.
