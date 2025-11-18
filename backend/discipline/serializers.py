from rest_framework import serializers
from .models import Violation, Incident, BehaviorLevel
from .models import Absence, ExcuseRequest, ExcuseAttachment
from .models import Action
from .models import IncidentAttachment
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
    # ملاحظة تقنية مهمة:
    # أثناء التحقق من صحة البيانات (validation) يقوم DRF بحل حقل ForeignKey
    # عبر queryset الحقل. إن كان queryset يسحب كل أعمدة Violation فستحاول
    # قاعدة البيانات إرجاع العمود الاختياري "policy" غير الموجود في بعض
    # قواعد البيانات القديمة، ما يؤدي إلى خطأ 500 عند الحفظ.
    # لذلك نستخدم queryset مُقيَّد بـ only() ويؤجّل policy لتفادي هذا الخطأ.
    violation = serializers.PrimaryKeyRelatedField(
        queryset=Violation.objects.only("id", "severity", "requires_committee").defer("policy")
    )
    # حقول مساعدة اختيارية من الواجهة لتسهيل ربط الواقعة بالحصة لاحقًا
    class_id = serializers.IntegerField(required=False, allow_null=True, write_only=True)
    period_number = serializers.IntegerField(required=False, allow_null=True, write_only=True)

    class Meta:
        model = Incident
        fields = "__all__"
        read_only_fields = (
            "reporter",
            "severity",
            "committee_required",
            # مُسجَّلة تلقائيًا عند جدولة اللجنة عبر endpoint مخصص
            "committee_scheduled_by",
            "committee_scheduled_at",
            "submitted_at",
            "reviewed_by",
            "reviewed_at",
            "closed_by",
            "closed_at",
            "actions_applied",
            "sanctions_applied",
            "escalated_due_to_repeat",
            # تثبيت المادة داخليًا فقط
            "subject",
            "subject_name_cached",
            "status",
        )

    def create(self, validated_data):
        # الحقول المساعدة القادمة من الواجهة (ليست حقول نموذج) يجب عدم تمريرها إلى ORM
        # لأنها ستسبب TypeError: Incident() got unexpected keyword arguments
        # نحتفظ بها محليًا لاستخدام مستقبلي (ربط بالحصة/المادة) دون تعطيل الحفظ.
        _class_id = validated_data.pop("class_id", None)
        _period_number = validated_data.pop("period_number", None)

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
        # عرض حالة حديثة متوافقة: إبقاء القيمة الخام كما هي، وإضافة status_display كحقل مشتق.
        try:
            raw_status = data.get("status") or getattr(instance, "status", "") or ""
            normalized = str(raw_status)
            # خرائط التوافق: under_review → review، open → draft
            if raw_status == "under_review":
                normalized = "review"
            elif raw_status == "open":
                # open التاريخية تُعرض كـ draft لواجهات المستخدم الجديدة
                normalized = "draft"
            # لا تغييرات لبقية القيم (draft/submitted/review/action_required/in_committee/resolved/closed)
            data["status_display"] = normalized
        except Exception:
            data["status_display"] = data.get("status")
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
        # اسم من قام بجدولة اللجنة (إن وُجد)
        try:
            scheduler = getattr(instance, "committee_scheduled_by", None)
            s_name = None
            if scheduler:
                try:
                    from school.models import Staff  # type: ignore

                    s_name = (
                        Staff.objects.filter(user=scheduler)
                        .only("full_name")
                        .values_list("full_name", flat=True)
                        .first()
                    ) or None
                except Exception:
                    s_name = None
                if not s_name and hasattr(scheduler, "get_full_name"):
                    s_name = scheduler.get_full_name() or None
            data["committee_scheduled_by_name"] = s_name
            # ممرّر كما هو من النموذج: committee_scheduled_at (قد يكون null)
            data["committee_scheduled_at"] = getattr(instance, "committee_scheduled_at", None)
        except Exception:
            data["committee_scheduled_by_name"] = None
            data["committee_scheduled_at"] = None
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
        # Derive lesson period number (1..7) and time label (HH:MM–HH:MM) if possible
        try:
            occ = getattr(instance, "occurred_at", None)
            cls = getattr(getattr(getattr(instance, "student", None), "class_fk", None), "id", None)
            if occ and cls:
                # day_of_week: Monday=1 .. Sunday=7 in many DBs; our timing util expects 1..7
                # Python weekday(): Monday=0..Sunday=6, convert to 1..7
                dow = ((occ.weekday() + 1 - 0) % 7) or 7
                try:
                    from apps.attendance.timing import times_for_by_class  # type: ignore

                    slots = times_for_by_class(int(dow), int(cls)) or {}
                    # occ time in minutes
                    hh = occ.hour
                    mm = occ.minute
                    total = hh * 60 + mm
                    chosen_p = None
                    chosen_label = None
                    for pnum, (st, et) in sorted(slots.items()):
                        try:
                            st_min = int(st.hour) * 60 + int(st.minute)
                            et_min = int(et.hour) * 60 + int(et.minute)
                            if total >= st_min and total <= et_min:
                                chosen_p = int(pnum)
                                chosen_label = f"{str(st.hour).zfill(2)}:{str(st.minute).zfill(2)}–{str(et.hour).zfill(2)}:{str(et.minute).zfill(2)}"
                                break
                        except Exception:
                            continue
                    data["period_number"] = chosen_p
                    data["period_time_label"] = chosen_label
                except Exception:
                    data["period_number"] = None
                    data["period_time_label"] = None
            else:
                data["period_number"] = None
                data["period_time_label"] = None
        except Exception:
            data["period_number"] = None
            data["period_time_label"] = None
        # Subject fixation fields: prefer FK + cached label; fallback to previous derivation from timetable
        try:
            subj_id = getattr(instance, "subject_id", None)
            subj_name_cached = getattr(instance, "subject_name_cached", "") or ""
            subj_name = None
            if subj_id:
                try:
                    subj_name = (
                        subj_name_cached
                        or getattr(getattr(instance, "subject", None), "name_ar", None)
                        or getattr(getattr(instance, "subject", None), "name", None)
                    )
                except Exception:
                    subj_name = subj_name_cached or None
            if not subj_id or not subj_name:
                # Fallback to timetable-based derivation (legacy)
                occ = getattr(instance, "occurred_at", None)
                period_num = data.get("period_number")
                class_id = getattr(getattr(getattr(instance, "student", None), "class_fk", None), "id", None)
                subject_label = None
                if occ and class_id and period_num:
                    dow_py = int(occ.weekday())  # 0..6
                    dow_1_7 = ((dow_py + 1 - 0) % 7) or 7  # 1..7
                    day_for_tt = 1 if dow_1_7 == 6 else (5 if dow_1_7 == 7 else dow_1_7)
                    try:
                        from school.models import Term  # type: ignore
                        from school.models import TimetableEntry  # type: ignore

                        term = (
                            Term.objects.filter(start_date__lte=occ.date(), end_date__gte=occ.date())
                            .order_by("-start_date")
                            .first()
                        ) or Term.objects.order_by("-start_date").first()
                        if term is not None:
                            entry = (
                                TimetableEntry.objects.select_related("subject")
                                .filter(
                                    classroom_id=int(class_id),
                                    day_of_week=int(day_for_tt),
                                    period_number=int(period_num),
                                    term=term,
                                )
                                .first()
                            )
                            if entry is not None:
                                subject_label = getattr(getattr(entry, "subject", None), "name_ar", None) or None
                    except Exception:
                        subject_label = None
                subj_name = subj_name or subject_label
            data["subject_id"] = subj_id
            data["subject_name"] = subj_name
        except Exception:
            data["subject_id"] = None
            data["subject_name"] = None
        # Severity color
        try:
            sev = int(getattr(instance, "severity", 1) or 1)
            color = {1: "#2e7d32", 2: "#f9a825", 3: "#fb8c00", 4: "#c62828"}.get(sev, "#2e7d32")
            data["level_color"] = color
        except Exception:
            data["level_color"] = "#2e7d32"
        # Repeat info: same classroom (الصف) + same subject — not by academic term
        try:
            subj_id = getattr(instance, "subject_id", None)
            # الصف الحالي الذي ينتمي إليه الطالب
            class_id = getattr(getattr(getattr(instance, "student", None), "class_fk", None), "id", None)
            repeat_qs = Incident.objects.filter(
                student_id=getattr(instance, "student_id", None),
                violation_id=getattr(instance, "violation_id", None),
                subject_id=subj_id,
            ).exclude(id=getattr(instance, "id", None))
            # قصر العد على الوقائع التي الطالب فيها ضمن نفس الصف
            if class_id:
                repeat_qs = repeat_qs.filter(student__class_fk_id=int(class_id))
            class_label = None
            try:
                class_label = getattr(getattr(getattr(instance, "student", None), "class_fk", None), "name", None)
            except Exception:
                class_label = None
            data["repeat_count_for_subject"] = int(repeat_qs.count())
            # احتفظنا بالمفتاح repeat_window_term_label للتوافق الأمامي، لكنه الآن يحمل اسم الصف
            data["repeat_window_term_label"] = class_label
            # حافظ على التوافق مع الحقول السابقة لكن اجعلها مشتقة منه لأغراض العرض القديم
            data["repeat_count_in_window"] = data["repeat_count_for_subject"]
            data["repeat_window_days"] = None
        except Exception:
            data["repeat_count_for_subject"] = 0
            data["repeat_window_term_label"] = None
            data["repeat_count_in_window"] = 0
            data["repeat_window_days"] = None
        # دلالات نصية مساعدة للواجهة
        try:
            sev = int(getattr(instance, "severity", 1) or 1)
            data["severity_label"] = {
                1: "مستوى 1 (بسيطة)",
                2: "مستوى 2 (متوسطة)",
                3: "مستوى 3 (عالية)",
                4: "مستوى 4 (جسيمة)",
            }.get(sev, f"مستوى {sev}")
        except Exception:
            data["severity_label"] = None
        # إظهار ملخص "الإجراء/العقوبة المقترحة" حتى مع التمثيل الأساسي (ليس فقط الكامل)
        # لاحتياج الواجهة لطباعته ضمن خيار A دون طلب full=1
        try:
            acts = list(getattr(instance, "actions_applied", None) or [])
            sancs = list(getattr(instance, "sanctions_applied", None) or [])
            data["proposed_actions"] = [str((a or {}).get("name") or "").strip() for a in acts if (a or {}).get("name")]
            data["proposed_sanctions"] = [
                str((s or {}).get("name") or "").strip() for s in sancs if (s or {}).get("name")
            ]
            pa = ", ".join(data["proposed_actions"]) if data.get("proposed_actions") else ""
            ps = ", ".join(data["proposed_sanctions"]) if data.get("proposed_sanctions") else ""
            if pa and ps:
                data["proposed_summary"] = f"إجراءات: {pa} • عقوبات: {ps}"
            elif pa:
                data["proposed_summary"] = f"إجراءات: {pa}"
            elif ps:
                data["proposed_summary"] = f"عقوبات: {ps}"
            else:
                data["proposed_summary"] = None
        except Exception:
            data["proposed_actions"] = []
            data["proposed_sanctions"] = []
            data["proposed_summary"] = None
        # حقول مشتقة: repeat_index + suggested_actions (لا تُخزّن في قاعدة البيانات)
        try:
            data["repeat_index"] = compute_repeat_index(instance)
        except Exception:
            data["repeat_index"] = 1
        try:
            data["suggested_actions"] = suggest_actions_for(instance)
        except Exception:
            data["suggested_actions"] = []
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
        # إغناء إضافي متعلق بالمادة والتكرار حسب الصف (وليس الفصل الدراسي)
        try:
            # اضمن تكرار نفس الحقول في التمثيل الكامل
            if "subject_id" not in base:
                base["subject_id"] = getattr(instance, "subject_id", None)
            if "subject_name" not in base:
                base["subject_name"] = getattr(instance, "subject_name_cached", None) or None
            # repeat_count_for_subject قد يكون موجودًا من الأب؛ إن لم يوجد احسبه بشكل آمن
            if base.get("repeat_count_for_subject") is None:
                qs = Incident.objects.filter(
                    student_id=getattr(instance, "student_id", None),
                    violation_id=getattr(instance, "violation_id", None),
                    subject_id=getattr(instance, "subject_id", None),
                ).exclude(id=getattr(instance, "id", None))
                # حصر العد ضمن نفس الصف الحالي للطالب
                class_id = getattr(getattr(getattr(instance, "student", None), "class_fk", None), "id", None)
                if class_id:
                    qs = qs.filter(student__class_fk_id=int(class_id))
                base["repeat_count_for_subject"] = int(qs.count())
                # إعادة استخدام repeat_window_term_label لحمل اسم الصف للتوافق مع الواجهة
                try:
                    base["repeat_window_term_label"] = getattr(
                        getattr(getattr(instance, "student", None), "class_fk", None), "name", None
                    )
                except Exception:
                    base["repeat_window_term_label"] = None
        except Exception:
            pass
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
        # ملخص «الإجراء/القرار المقترح من المراجِع/المقرِّرة» لإظهاره لأعضاء اللجنة
        try:
            acts = list(getattr(instance, "actions_applied", None) or [])
            sancs = list(getattr(instance, "sanctions_applied", None) or [])
            base["proposed_actions"] = [str((a or {}).get("name") or "").strip() for a in acts if (a or {}).get("name")]
            base["proposed_sanctions"] = [
                str((s or {}).get("name") or "").strip() for s in sancs if (s or {}).get("name")
            ]
            # اصنع ملخصًا قصيرًا قابلًا للعرض
            pa = ", ".join(base["proposed_actions"]) if base.get("proposed_actions") else ""
            ps = ", ".join(base["proposed_sanctions"]) if base.get("proposed_sanctions") else ""
            if pa and ps:
                base["proposed_summary"] = f"إجراءات: {pa} • عقوبات: {ps}"
            elif pa:
                base["proposed_summary"] = f"إجراءات: {pa}"
            elif ps:
                base["proposed_summary"] = f"عقوبات: {ps}"
            else:
                base["proposed_summary"] = None
        except Exception:
            base["proposed_actions"] = []
            base["proposed_sanctions"] = []
            base["proposed_summary"] = None
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

    # ===================== Serializers للحضور والأعذار (Phase 1) =====================


class AbsenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Absence
        fields = (
            "id",
            "student",
            "date",
            "type",
            "period",
            "status",
            "source",
            "notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")


class ExcuseAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExcuseAttachment
        fields = ("id", "excuse", "category", "url", "checksum", "origin", "uploaded_by", "uploaded_at")
        read_only_fields = ("uploaded_by", "uploaded_at")


class ExcuseRequestSerializer(serializers.ModelSerializer):
    absences = serializers.PrimaryKeyRelatedField(queryset=Absence.objects.all(), many=True)
    attachments = ExcuseAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = ExcuseRequest
        fields = (
            "id",
            "absences",
            "submitted_by",
            "status",
            "reviewed_by",
            "decision_reason",
            "decided_at",
            "created_at",
            "updated_at",
            "attachments",
        )
        read_only_fields = ("status", "reviewed_by", "decided_at", "created_at", "updated_at")

    def create(self, validated_data):
        absences = validated_data.pop("absences", [])
        req = ExcuseRequest.objects.create(**validated_data)
        if absences:
            req.absences.set(absences)
        return req


# ===================== Serializers للإجراءات (Phase 2) =====================
class ActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Action
        fields = (
            "id",
            "incident",
            "type",
            "assigned_to",
            "due_at",
            "completed_at",
            "requires_guardian_signature",
            "doc_required",
            "doc_received_at",
            "notes",
            "meta",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at", "completed_at")


class IncidentAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = IncidentAttachment
        fields = (
            "id",
            "incident",
            "action",
            "kind",
            "file",
            "mime",
            "size",
            "sha256",
            "created_by",
            "created_at",
            "meta",
        )
        read_only_fields = ("mime", "size", "sha256", "created_by", "created_at")


# ===================== ملحق: حقول مشتقة للواقعة (repeat_index + suggested_actions) =====================
def compute_repeat_index(instance) -> int:
    """احسب رقم التكرار لنفس المخالفة لنفس الطالب ضمن نافذة زمنية policy.window_days.
    التكرار = عدد الوقائع السابقة المشابهة + 1 (لهذه الواقعة).
    """
    try:
        from datetime import timedelta
        from django.conf import settings as dj_settings
        from .models import Incident

        if not getattr(instance, "occurred_at", None):
            return 1
        viol = getattr(instance, "violation", None)
        # Policy precedence: Violation.policy.window_days -> settings.DISCIPLINE_REPEAT_WINDOW_D -> 365
        window_days = 365
        try:
            pol = getattr(viol, "policy", None) or {}
            policy_days = int(pol.get("window_days") or 0)
            if policy_days > 0:
                window_days = policy_days
            else:
                window_days = int(getattr(dj_settings, "DISCIPLINE_REPEAT_WINDOW_D", 365) or 365)
        except Exception:
            try:
                window_days = int(getattr(dj_settings, "DISCIPLINE_REPEAT_WINDOW_D", 365) or 365)
            except Exception:
                window_days = 365
        start_dt = instance.occurred_at - timedelta(days=window_days)
        cnt = (
            Incident.objects.filter(
                student_id=getattr(instance, "student_id", None),
                violation_id=getattr(instance, "violation_id", None),
                occurred_at__lt=instance.occurred_at,
                occurred_at__gte=start_dt,
            )
            .only("id")
            .count()
        )
        return int(cnt) + 1
    except Exception:
        return 1


def suggest_actions_for(instance) -> list:
    """Suggest a list of action type codes based on violation severity and repeat index.

    Mapping derived from the roadmap and policy document. Minimal, stateless, and
    easy to test. Returns a list of Action.TYPE_CHOICES values.
    """
    try:
        deg = int(
            getattr(instance, "severity", None) or getattr(getattr(instance, "violation", None), "severity", 0) or 0
        )
    except Exception:
        deg = 0
    try:
        n = int(compute_repeat_index(instance))
    except Exception:
        n = 1

    # Degree 1
    if deg == 1:
        if n <= 1:
            return ["VERBAL_NOTICE"]
        if n == 2:
            return ["WRITTEN_NOTICE"]
        if n == 3:
            return ["WRITTEN_WARNING", "COUNSELING_SESSION"]
        return ["BEHAVIOR_CONTRACT"]

    # Degree 2
    if deg == 2:
        if n <= 1:
            return ["WRITTEN_WARNING", "BEHAVIOR_CONTRACT"]
        if n == 2:
            return ["WRITTEN_WARNING", "GUARDIAN_MEETING"]
        return ["COMMITTEE_REFERRAL", "SUSPENSION"]

    # Degree 3
    if deg == 3:
        if n <= 1:
            return ["COMMITTEE_REFERRAL"]
        return ["SUSPENSION", "RESTITUTION"]

    # Degree 4
    if deg >= 4:
        return ["COMMITTEE_REFERRAL", "EXTERNAL_NOTIFICATION"]

    return []
