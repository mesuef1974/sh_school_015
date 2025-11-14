from __future__ import annotations

import uuid
from django.conf import settings
from django.db import models


class BehaviorLevel(models.Model):
    code = models.PositiveSmallIntegerField(unique=True)
    name = models.CharField(max_length=64)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "مستوى السلوك"
        verbose_name_plural = "مستويات السلوك"
        ordering = ("code",)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.code} - {self.name}"


class Violation(models.Model):
    level = models.ForeignKey(BehaviorLevel, on_delete=models.PROTECT, related_name="violations")
    code = models.CharField(max_length=16, unique=True)
    category = models.CharField(max_length=256)
    description = models.TextField(blank=True)
    default_actions = models.JSONField(default=list)
    default_sanctions = models.JSONField(default=list)
    severity = models.PositiveSmallIntegerField()
    requires_committee = models.BooleanField(default=False)
    # سياسة الكتالوج (تمكين برمجي): قواعد تكرار/تصعيد/لجنة وإرشادات الإجراءات والعقوبات
    # مخطط مقترح:
    # {
    #   "window_days": 365,
    #   "committee": { "requires_on_severity_gte": 3, "after_repeats": 2 },
    #   "escalation": { "after_repeats": 2 },
    #   "actions_by_repeat": { "0": ["تنبيه شفهي"], "1": ["إنذار خطي"], "2": ["اتصال بولي الأمر"] },
    #   "sanctions_by_repeat": { "2": ["حرمان من نشاط"], "3": ["إحالة للجنة"] },
    #   "points_by_repeat": { "0": 1, "1": 3, "2": 5 }
    # }
    policy = models.JSONField(
        default=dict, blank=True, help_text="سياسة إجرائية مخصّصة للمخالفة: تكرارات/تصعيد/لجنة وإرشادات الإجراءات"
    )

    class Meta:
        verbose_name = "مخالفة"
        verbose_name_plural = "مخالفات"
        ordering = ("severity", "code")
        permissions = (("access", "Can access discipline module"),)

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.code} — {self.category}"


class Incident(models.Model):
    STATUS_CHOICES = (
        ("open", "Open"),
        ("under_review", "Under Review"),
        ("closed", "Closed"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    violation = models.ForeignKey(Violation, on_delete=models.PROTECT, related_name="incidents")
    student = models.ForeignKey("school.Student", on_delete=models.PROTECT, related_name="incidents")
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="reported_incidents")
    occurred_at = models.DateTimeField()
    location = models.CharField(max_length=128, blank=True)
    narrative = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="open")
    severity = models.PositiveSmallIntegerField()
    committee_required = models.BooleanField(default=False)
    # Workflow tracking fields
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_incidents",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="closed_incidents",
    )
    closed_at = models.DateTimeField(null=True, blank=True)
    actions_applied = models.JSONField(default=list, blank=True)
    sanctions_applied = models.JSONField(default=list, blank=True)
    escalated_due_to_repeat = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Committee workflow (stored in backend only)
    committee_panel = models.JSONField(
        default=dict, blank=True, help_text="تشكيلة اللجنة المحفوظة: {chair_id, member_ids[], recorder_id}"
    )
    committee_scheduled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="committee_scheduled_incidents",
    )
    committee_scheduled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "واقعة"
        verbose_name_plural = "وقائع"
        ordering = ("-occurred_at",)
        permissions = (
            ("incident_create", "Can create incident"),
            ("incident_submit", "Can submit incident for review"),
            ("incident_review", "Can review incident (approve/return)"),
            ("incident_escalate", "Can escalate incident"),
            ("incident_notify_guardian", "Can notify guardian for incident"),
            ("incident_close", "Can close incident"),
            # صلاحيات «اللجنة السلوكية» (مخصّصة لمسار اللجنة)
            ("incident_committee_view", "Can view incidents for committee workflow"),
            ("incident_committee_schedule", "Can schedule/route incident to committee"),
            ("incident_committee_decide", "Can record committee decision for incident"),
        )

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.violation.code} @ {self.occurred_at:%Y-%m-%d}"


class IncidentAuditLog(models.Model):
    """Audit trail for incident lifecycle with professional-grade fields.

    Records who did what, when, and how the incident changed, including client IP
    and optional metadata for future extensibility.
    """

    ACTION_CHOICES = (
        ("create", "Create"),
        ("submit", "Submit"),
        ("review", "Review"),
        ("notify_guardian", "Notify Guardian"),
        ("escalate", "Escalate"),
        ("close", "Close"),
        ("appeal", "Appeal"),
        ("reopen", "Reopen"),
        ("update", "Update"),
    )

    id = models.BigAutoField(primary_key=True)
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name="audit_logs")
    action = models.CharField(max_length=32, choices=ACTION_CHOICES)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    at = models.DateTimeField(auto_now_add=True)
    from_status = models.CharField(max_length=16, blank=True)
    to_status = models.CharField(max_length=16, blank=True)
    note = models.TextField(blank=True)
    client_ip = models.CharField(max_length=64, blank=True)
    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "سجل تدقيق الوقائع"
        verbose_name_plural = "سجلات تدقيق الوقائع"
        ordering = ("-at", "-id")
        indexes = [
            models.Index(fields=["incident", "at"], name="incident_audit_idx"),
            models.Index(fields=["action"], name="incident_audit_action_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.incident_id} {self.action} {self.from_status}->{self.to_status} @ {self.at:%Y-%m-%d %H:%M}"


class IncidentCommittee(models.Model):
    """تشكيلة لجنة السلوك المرتبطة بواقعة محددة (جدولة committee)"""

    incident = models.OneToOneField(Incident, on_delete=models.CASCADE, related_name="committee")
    chair = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="chaired_committees",
    )
    recorder = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recorded_committees",
    )
    scheduled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scheduled_committees",
    )
    scheduled_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "لجنة الواقعة"
        verbose_name_plural = "لجان الوقائع"
        indexes = [
            models.Index(fields=["incident"], name="committee_incident_idx"),
            models.Index(fields=["chair"], name="committee_chair_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"Committee for {self.incident_id}"


class IncidentCommitteeMember(models.Model):
    """أعضاء لجنة السلوك (باستثناء الرئيس)"""

    committee = models.ForeignKey(IncidentCommittee, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="incident_committees")

    class Meta:
        unique_together = ("committee", "user")
        indexes = [
            models.Index(fields=["committee"], name="committee_member_idx"),
            models.Index(fields=["user"], name="committee_member_user_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.user_id} in {self.committee_id}"


# ===================== لجنة دائمة (على مستوى النظام) =====================
class StandingCommittee(models.Model):
    """اللجنة السلوكية الدائمة على مستوى المدرسة/النظام.

    ملاحظة: نبدأ بنسخة واحدة فقط (singleton منطقي)، يمكن توسيعها لاحقًا بدعم مدارس متعددة إن لزم.
    """

    chair = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="standing_committee_chair_of",
        null=True,
        blank=True,
    )
    recorder = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="standing_committee_recorder_of",
        null=True,
        blank=True,
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "اللجنة السلوكية الدائمة"
        verbose_name_plural = "اللجان السلوكية الدائمة"

    def __str__(self) -> str:  # pragma: no cover
        return f"StandingCommittee #{self.id or 'new'}"


class StandingCommitteeMember(models.Model):
    """أعضاء اللجنة الدائمة (باستثناء الرئيس)"""

    standing = models.ForeignKey(StandingCommittee, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="standing_committees")

    class Meta:
        unique_together = ("standing", "user")
        indexes = [
            models.Index(fields=["standing"], name="standing_member_idx"),
            models.Index(fields=["user"], name="standing_member_user_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.user_id} in standing {self.standing_id}"
