from __future__ import annotations

import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone


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
    # توسيع حالات سير العمل لتتوافق مع الخارطة: DRAFT → SUBMITTED → REVIEW → ACTION_REQUIRED → IN_COMMITTEE → RESOLVED → CLOSED
    # مع الحفاظ على القيم القديمة (open/under_review/closed) لأغراض التوافق الخلفي.
    STATUS_CHOICES = (
        # قيَم قديمة (للخلفية)
        ("open", "Open"),
        ("under_review", "Under Review"),
        ("closed", "Closed"),
        # القيَم الموسّعة
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("review", "In Review"),
        ("action_required", "Action Required"),
        ("in_committee", "In Committee"),
        ("resolved", "Resolved"),
        ("closed", "Closed"),  # مكرر عمدًا ضمن التوسعة للتوافق مع المصطلح الجديد
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
    # تثبيت المادة لحظة إنشاء الواقعة لضمان دقة سياسة التكرار حسب المادة/الفصل
    subject = models.ForeignKey(
        "school.Subject", on_delete=models.SET_NULL, null=True, blank=True, related_name="incidents"
    )
    subject_name_cached = models.CharField(max_length=150, blank=True, default="")
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
    # إشعار ولي الأمر + SLA
    notified_guardian_at = models.DateTimeField(null=True, blank=True)
    guardian_notify_channel = models.CharField(max_length=16, blank=True, help_text="sms/call/email/in_app/whatsapp")
    guardian_notify_sla_met = models.BooleanField(default=False)

    # ملاحظة: لم نضف repeat_index و suggested_actions كحقول في قاعدة البيانات حرصًا على تقليل التغييرات.
    # سيتم احتسابهما ديناميكيًا وإرجاعهما في واجهات REST عبر الـ Serializer.

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
        """تمثيل مبسّط وآمن لا يعتمد على جلب علاقات كسولة.

        ملاحظة: كان التمثيل السابق يصل إلى self.violation.code، وهذا قد يطلق
        استعلامًا إضافيًا يجلب كل أعمدة Violation بما فيها عمود اختياري قد لا يكون
        موجودًا في بعض قواعد البيانات القديمة (policy)، مما يسبب خطأً في لوحة الإدارة
        عند بناء التسميات لحقول العلاقات. نتجنب هنا أي وصول لعلاقات؛ نستعمل المعرّف
        وتاريخ الحدوث أو الإنشاء كعرض كافٍ في لوحة الإدارة.
        """
        try:
            date_part = None
            try:
                if getattr(self, "occurred_at", None):
                    date_part = self.occurred_at.strftime("%Y-%m-%d")
            except Exception:
                date_part = None
            if not date_part:
                try:
                    if getattr(self, "created_at", None):
                        date_part = self.created_at.strftime("%Y-%m-%d")
                except Exception:
                    date_part = None
            date_part = date_part or "—"
            # استخدم المعرّف المختصر لسهولة القراءة
            return f"Incident {str(self.id)[:8]} @ {date_part}"
        except Exception:
            return f"Incident {getattr(self, 'id', '')}"


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


class IncidentAttachment(models.Model):
    """File attachments linked to an incident (pledge, signed pledge, other).

    Minimal schema to support Option B later. Provides audit-friendly fields such as
    mime, size and sha256 for integrity checks.
    """

    KIND_CHOICES = (
        ("pledge", "Pledge"),
        ("pledge_signed", "Pledge (Signed)"),
        ("other", "Other"),
    )

    id = models.BigAutoField(primary_key=True)
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name="attachments")
    # ربط اختياري مباشر بالإجراء لتوثيق المستندات الموقعة لكل إجراء
    action = models.ForeignKey(
        "discipline.Action",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="attachments",
        help_text="إن كان المرفق يخص إجراء محدد فسيُربط هنا",
    )
    kind = models.CharField(max_length=32, choices=KIND_CHOICES, default="other")
    file = models.FileField(upload_to="incidents/%Y/%m/")
    mime = models.CharField(max_length=64, blank=True)
    size = models.IntegerField(default=0)
    sha256 = models.CharField(max_length=64, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "مرفق واقعة"
        verbose_name_plural = "مرفقات الوقائع"
        ordering = ("-created_at", "-id")
        indexes = [
            models.Index(fields=["incident", "created_at"], name="inc_att_inc_dt_idx"),
            models.Index(fields=["kind"], name="inc_att_kind_idx"),
            models.Index(fields=["action"], name="inc_att_action_idx"),
        ]
        permissions = (
            ("incident_attachment_view", "Can view incident attachments"),
            ("incident_attachment_upload", "Can upload incident attachments"),
        )

    def __str__(self) -> str:  # pragma: no cover
        try:
            return f"Attachment {self.id} {self.kind} for {str(self.incident_id)[:8]}"
        except Exception:
            return f"Attachment {getattr(self, 'id', '')}"


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


# ===================== نماذج الحضور والأعذار (المرحلة 1 من الخارطة) =====================
class Absence(models.Model):
    """سجل غياب الطالب (يوم كامل أو حصة) مع حالة بعذر/بدون عذر.

    ملاحظة: نبدأ بنطاق مبسّط يدعم التحويل إلى بعذر عند قبول طلب العذر.
    """

    TYPE_CHOICES = (
        ("FULL_DAY", "Full Day"),
        ("PERIOD", "Period"),
    )
    STATUS_CHOICES = (
        ("UNEXCUSED", "Unexcused"),
        ("EXCUSED", "Excused"),
    )
    SOURCE_CHOICES = (
        ("ATTENDANCE_SYSTEM", "Attendance System"),
        ("MANUAL", "Manual"),
    )

    student = models.ForeignKey("school.Student", on_delete=models.PROTECT, related_name="absences")
    date = models.DateField()
    type = models.CharField(max_length=16, choices=TYPE_CHOICES, default="FULL_DAY")
    period = models.PositiveSmallIntegerField(null=True, blank=True, help_text="رقم الحصة عند اختيار نوع PERIOD")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="UNEXCUSED")
    source = models.CharField(max_length=24, choices=SOURCE_CHOICES, default="ATTENDANCE_SYSTEM")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "غياب"
        verbose_name_plural = "غيابات"
        indexes = [
            models.Index(fields=["student", "date"], name="abs_student_date_idx"),
            models.Index(fields=["status"], name="abs_status_idx"),
        ]
        # ضمان عدم التكرار بشروط: يوم كامل (بدون period) مقابل غياب بالحصة (مع period)
        constraints = [
            # لغياب اليوم الكامل: لكل طالب/تاريخ سجل واحد فقط من نوع FULL_DAY مع period فارغ
            models.UniqueConstraint(
                fields=["student", "date"],
                condition=models.Q(type="FULL_DAY") & models.Q(period__isnull=True),
                name="uniq_abs_full_day_per_student_date",
            ),
            # لغياب الحصة: لكل طالب/تاريخ/حصة سجل واحد من نوع PERIOD مع period غير فارغ
            models.UniqueConstraint(
                fields=["student", "date", "period"],
                condition=models.Q(type="PERIOD") & models.Q(period__isnull=False),
                name="uniq_abs_period_per_student_date_period",
            ),
        ]

    def __str__(self) -> str:  # pragma: no cover
        p = f" P{self.period}" if self.period else ""
        return f"Absence {self.student_id} {self.date}{p} {self.status}"


class ExcuseRequest(models.Model):
    """طلب تبرير غياب، يراجع من مشرف الجناح ويحوّل الغياب إلى بعذر عند القبول."""

    STATUS_CHOICES = (
        ("PENDING_JUSTIFICATION", "Pending Justification"),
        ("UNDER_REVIEW", "Under Review"),
        ("APPROVED_EXCUSE", "Approved"),
        ("REJECTED_EXCUSE", "Rejected"),
        ("NEEDS_CORRECTION", "Needs Correction"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    absences = models.ManyToManyField(Absence, related_name="excuse_requests")
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="submitted_excuses"
    )
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default="PENDING_JUSTIFICATION")
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_excuses",
    )
    decision_reason = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "طلب تبرير غياب"
        verbose_name_plural = "طلبات تبرير الغياب"
        ordering = ("-created_at",)
        permissions = (
            ("can_review_excuse_requests", "Can review absence excuse requests"),
            ("can_convert_absence_status", "Can convert absences to excused"),
            ("can_request_attachment_corrections", "Can request attachment corrections for excuses"),
        )

    def __str__(self) -> str:  # pragma: no cover
        return f"ExcuseRequest {str(self.id)[:8]} ({self.status})"

    def approve(self, reviewer, reason: str = ""):
        """اعتماد العذر وتحويل جميع الغيابات المرتبطة إلى بعذر (ذرّي/Idempotent)."""
        from django.db import transaction

        with transaction.atomic():
            # Idempotent: إن كان مُعتمدًا مسبقًا، لا تعدّل إلا إن لزم السبب
            if self.status == "APPROVED_EXCUSE":
                return
            self.status = "APPROVED_EXCUSE"
            self.reviewed_by = reviewer
            if reason:
                self.decision_reason = reason
            self.decided_at = timezone.now()
            self.save(update_fields=["status", "reviewed_by", "decision_reason", "decided_at", "updated_at"])
            # تحديث فقط الغيابات غير المبررة لتكون Idempotent
            ids = list(self.absences.values_list("id", flat=True))
            Absence.objects.filter(id__in=ids, status="UNEXCUSED").update(status="EXCUSED")
            # سجل تدقيق
            try:
                ExcuseAuditLog.objects.create(
                    excuse=self,
                    actor=reviewer,
                    action="APPROVE",
                    reason=reason or "",
                    snapshot={"absence_ids": ids},
                )
            except Exception:
                pass

    def reject(self, reviewer, reason: str = ""):
        from django.db import transaction

        with transaction.atomic():
            if self.status == "REJECTED_EXCUSE":
                return
            self.status = "REJECTED_EXCUSE"
            self.reviewed_by = reviewer
            if reason:
                self.decision_reason = reason
            self.decided_at = timezone.now()
            self.save(update_fields=["status", "reviewed_by", "decision_reason", "decided_at", "updated_at"])
            try:
                ExcuseAuditLog.objects.create(
                    excuse=self,
                    actor=reviewer,
                    action="REJECT",
                    reason=reason or "",
                    snapshot={"absence_ids": list(self.absences.values_list("id", flat=True))},
                )
            except Exception:
                pass


class ExcuseAttachment(models.Model):
    """مرفقات خاصة بطلبات الأعذار (صور/PDF)."""

    CATEGORY_CHOICES = (("EXCUSE_DOC", "Excuse Document"),)

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    excuse = models.ForeignKey(ExcuseRequest, on_delete=models.CASCADE, related_name="attachments")
    category = models.CharField(max_length=16, choices=CATEGORY_CHOICES, default="EXCUSE_DOC")
    url = models.CharField(max_length=512)
    checksum = models.CharField(max_length=128, blank=True)
    origin = models.CharField(max_length=16, blank=True, help_text="scan/photo/other")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="uploaded_excuse_attachments"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "مرفق عذر"
        verbose_name_plural = "مرفقات الأعذار"
        indexes = [
            models.Index(fields=["excuse"], name="excuse_att_excuse_idx"),
            models.Index(fields=["category"], name="excuse_att_category_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"ExcuseAttachment {str(self.id)[:8]} for {str(self.excuse_id)[:8]}"


class ExcuseAuditLog(models.Model):
    """سجل تدقيق لقرارات ومراحل طلبات الأعذار والعمليات المرتبطة بها."""

    ACTION_CHOICES = (
        ("SUBMIT", "Submit"),
        ("REVIEW", "Review"),
        ("APPROVE", "Approve"),
        ("REJECT", "Reject"),
        ("REQUEST_CORRECTION", "Request Correction"),
        ("ATTACHMENT_ADD", "Attachment Add"),
    )

    excuse = models.ForeignKey(ExcuseRequest, on_delete=models.CASCADE, related_name="audit_logs")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=32, choices=ACTION_CHOICES)
    reason = models.TextField(blank=True)
    snapshot = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "سجل تدقيق عذر"
        verbose_name_plural = "سجلات تدقيق الأعذار"
        ordering = ("-created_at", "-id")
        indexes = [
            models.Index(fields=["excuse", "created_at"], name="excuse_audit_exc_dt_idx"),
            models.Index(fields=["action"], name="excuse_audit_action_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"ExcuseAuditLog {self.action} for {str(getattr(self, 'excuse_id', ''))[:8]}"


# ===================== الإجراءات (Action) — المرحلة 2 من الخارطة =====================
class Action(models.Model):
    """إجراء تنفيذي مرتبط بواقعة سلوكية (مهام، إنذارات، تعهدات...).

    نحافظ على مخطط بسيط وقابل للتوسعة دون المساس ببقية الوحدات.
    """

    TYPE_CHOICES = (
        ("VERBAL_NOTICE", "Verbal Notice"),
        ("WRITTEN_NOTICE", "Written Notice"),
        ("WRITTEN_WARNING", "Written Warning"),
        ("BEHAVIOR_CONTRACT", "Behavior Contract"),
        ("GUARDIAN_MEETING", "Guardian Meeting"),
        ("COUNSELING_SESSION", "Counseling Session"),
        ("COMMITTEE_REFERRAL", "Committee Referral"),
        ("SUSPENSION", "Suspension"),
        ("RESTITUTION", "Restitution"),
        ("EXTERNAL_NOTIFICATION", "External Notification"),
        ("CONFISCATION_RECEIPT", "Confiscation Receipt"),
        ("OTHER", "Other"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name="actions")
    type = models.CharField(max_length=32, choices=TYPE_CHOICES)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_actions"
    )
    due_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    requires_guardian_signature = models.BooleanField(default=False)
    doc_required = models.BooleanField(default=False)
    doc_received_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    meta = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "إجراء"
        verbose_name_plural = "إجراءات"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["incident", "created_at"], name="act_inc_created_idx"),
            models.Index(fields=["type"], name="act_type_idx"),
        ]
        permissions = (
            ("action_complete", "Can complete actions for incidents"),
            ("action_create", "Can create actions for incidents"),
            ("action_view", "Can view actions for incidents"),
        )

    def __str__(self) -> str:  # pragma: no cover
        try:
            return f"Action {self.type} for {str(self.incident_id)[:8]}"
        except Exception:
            return f"Action {getattr(self, 'id', '')}"
