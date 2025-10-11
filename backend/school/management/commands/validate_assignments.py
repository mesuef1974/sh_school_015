from django.core.management.base import BaseCommand
from django.db.models import Sum
from school.models import Class, TeachingAssignment, Subject, Staff, ClassSubject


class Command(BaseCommand):
    help = (
        "يتحقق من جاهزية تكليفات التدريس أسبوعيًا بحسب القواعد الرسمية، ويُصدر تحذيرات/ملاحظات: "
        "• للمرحلة الإعدادية (7–9): 34 حصة أسبوعيًا (الأحد–الأربعاء 7، الخميس 6). "
        "• للمرحلة الثانوية (10–12): 35 حصة أسبوعيًا (7 يوميًا). "
        "ويضيف/يعرض ملاحظات للحالات الخاصة المذكورة."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply-notes",
            action="store_true",
            help="تطبيق الملاحظات تلقائيًا على حقول notes في التكليفات بدل العرض فقط.",
        )
        parser.add_argument(
            "--expected-total",
            type=int,
            default=862,
            help="القيمة المتوقعة لإجمالي الحصص على مستوى المدرسة (الافتراضي 862)",
        )

    def handle(self, *args, **options):
        apply_notes: bool = options.get("apply_notes", False)
        expected_school_total: int = int(options.get("expected_total") or 862)

        def capacity_for_class(grade: int) -> int:
            if grade is None:
                return 0
            if 7 <= grade <= 9:
                return 34
            if 10 <= grade <= 12:
                return 35
            return 35  # افتراضي

        def find_subject(q: str):
            return Subject.objects.filter(name_ar__icontains=q).first()

        def ensure_note(class_name: str, subj_contains: str, teacher_contains: str, note_text: str):
            qs = TeachingAssignment.objects.select_related(
                "classroom", "subject", "teacher"
            ).filter(
                classroom__name=class_name,
                subject__name_ar__icontains=subj_contains,
            )
            if teacher_contains:
                qs = qs.filter(teacher__full_name__icontains=teacher_contains)
            affected = 0
            for a in qs:
                if note_text not in (a.notes or ""):
                    affected += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"[NOTE]{'(+apply)' if apply_notes else ''} {a.teacher.full_name} | {a.classroom.name} | {a.subject.name_ar}: {note_text}"
                        )
                    )
                    if apply_notes:
                        a.notes = (a.notes + " | " if a.notes else "") + note_text
                        a.save(update_fields=["notes", "updated_at"])  # type: ignore
            return affected

        # لا نعدّ كل الصفوف في الجاهزية؛ يتم استثناء صفوف الاحتياجات الخاصة (ESE)
        def is_special_needs_class(cls: Class) -> bool:
            name = (getattr(cls, "name", "") or "").upper()
            return "ESE" in name

        total_classes = 0  # سيُحتسب فقط للصفوف غير المستثناة
        ready = under = over = 0
        warnings_count = 0
        school_total_assigned = 0

        self.stdout.write("ملخص جاهزية الصفوف الأسبوعية:")
        self.stdout.write("id,name,grade,assigned,capacity,status")

        for c in Class.objects.all().order_by("name"):
            assigned = (
                TeachingAssignment.objects.filter(classroom=c).aggregate(
                    total=Sum("no_classes_weekly")
                )["total"]
                or 0
            )
            school_total_assigned += int(assigned)

            if is_special_needs_class(c):
                # صفوف احتياجات خاصة: لا جدول دراسي أسبوعي، تُستثنى من الجاهزية والسعة
                cap = 0
                status = "SKIPPED"
                self.stdout.write(
                    f"{c.id},{getattr(c, 'name', str(c))},{getattr(c, 'grade', '')},{int(assigned)},{cap},{status}"
                )
                # لا نزيد أي عدادات (ready/under/over) ولا total_classes
                continue

            cap = capacity_for_class(getattr(c, "grade", None))
            total_classes += 1
            if assigned == cap:
                status = "OK"
                ready += 1
            elif assigned < cap:
                status = "UNDER"
                under += 1
            else:
                status = "OVER"
                over += 1
            self.stdout.write(
                f"{c.id},{getattr(c, 'name', str(c))},{getattr(c, 'grade', '')},{int(assigned)},{cap},{status}"
            )

            # تفاصيل الفجوات واقتراحات الإكمال عند وجود عجز
            if status == "UNDER":
                missing = int(cap) - int(assigned)
                try:
                    suggestions = []
                    # لا اقتراح خاص للفنون البصرية للصف العاشر حسب سياسة المدرسة الحالية.
                    # قارن المضاف لكل مادة مقابل weekly_default للمادة أو لمادة الصف
                    cs_qs = ClassSubject.objects.select_related("subject").filter(classroom=c)
                    for cs in cs_qs:
                        target = int(cs.weekly_default or cs.subject.weekly_default or 0)
                        if target <= 0:
                            continue
                        cur = (
                            TeachingAssignment.objects.filter(
                                classroom=c, subject=cs.subject
                            ).aggregate(total=Sum("no_classes_weekly"))["total"]
                            or 0
                        )
                        deficit = max(0, int(target) - int(cur))
                        if deficit > 0:
                            suggestions.append((deficit, cs.subject.name_ar))
                    # رتّب الاقتراحات بالأكبر أولًا وخذ أفضل 3
                    suggestions.sort(key=lambda t: t[0], reverse=True)
                    suggestions = suggestions[:3]
                    if suggestions:
                        sug_txt = ", ".join([f"{name} (+{d})" for d, name in suggestions])
                        self.stdout.write(
                            self.style.WARNING(f"  => نقص {missing} حصص. مقترح الإكمال: {sug_txt}")
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f"  => نقص {missing} حصص. (أضف مواد مناسبة من مواد الصف)"
                            )
                        )
                except Exception:
                    # لا نكسر التنفيذ إن فشلت الاقتراحات
                    self.stdout.write(self.style.WARNING(f"  => نقص {missing} حصص."))

        # حالات الملاحظات الخاصة
        warnings_count += ensure_note(
            class_name="11-4",
            subj_contains="كيمياء",
            teacher_contains=(
                "أحمد" if Staff.objects.filter(full_name__icontains="أحمد").exists() else ""
            ),
            note_text="ملاحظة: حصتان مشتركتان مع المعلم يوسف يعقوب بنفس التوقيت",
        )
        # 12-1 و 11-1 تكنولوجيا/فنون بصرية (تقسيم مجموعات)
        for cls_name in ("12-1", "11-1"):
            warnings_count += ensure_note(
                class_name=cls_name,
                subj_contains="تكنولوجيا",
                teacher_contains=(
                    "محمد إسماعيل"
                    if Staff.objects.filter(full_name__icontains="محمد").exists()
                    else ""
                ),
                note_text="ملاحظة: بعض الطلاب تكنولوجيا والآخرون فنون بصرية (تقسيم مجموعات)",
            )
            warnings_count += ensure_note(
                class_name=cls_name,
                subj_contains="فنون",
                teacher_contains=(
                    "يوسف يعقوب"
                    if Staff.objects.filter(full_name__icontains="يوسف").exists()
                    else ""
                ),
                note_text="ملاحظة: بعض الطلاب تكنولوجيا والآخرون فنون بصرية (تقسيم مجموعات)",
            )

        # ملخص شامل وإجمالي المدرسة
        self.stdout.write("")
        pct = int(round((ready / total_classes) * 100)) if total_classes else 0
        self.stdout.write(self.style.SUCCESS(f"Ready: {ready}/{total_classes} ({pct}%)"))
        if under:
            self.stdout.write(self.style.WARNING(f"Under capacity: {under}"))
        if over:
            self.stdout.write(self.style.ERROR(f"Over capacity: {over}"))

        self.stdout.write("")
        delta_school = school_total_assigned - expected_school_total
        if delta_school == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f"إجمالي الحصص للمدرسة = {school_total_assigned} مطابق للقيمة المتوقعة ({expected_school_total})."
                )
            )
        else:
            warnings_count += 1
            self.stdout.write(
                self.style.ERROR(
                    f"Mismatch: total_assigned={school_total_assigned} expected={expected_school_total} delta={delta_school:+d}"
                )
            )

        # كود الخروج
        exit_code = 0 if (under == 0 and over == 0 and warnings_count == 0) else 1
        if exit_code != 0:
            # اخرج برمز غير صفري بدون إرجاع قيمة غير نصية إلى Django
            raise SystemExit(exit_code)
        # لا نعيد قيمة غير نصية إلى self.stdout.write في Django
        return ""
