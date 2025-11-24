from __future__ import annotations

from datetime import date as _date

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone


class Command(BaseCommand):
    help = (
        "تحويل الغياب الجزئي إلى غياب يوم كامل عندما يكون الطالب غائبًا في الحصتين الأولى والثانية.\n"
        "Idempotent: لن يُنشأ أكثر من سجل لليوم الكامل لنفس الطالب/التاريخ.\n"
        "الاستخدام: python manage.py attendance_finalize_day --date=YYYY-MM-DD"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            dest="date_str",
            help="التاريخ المطلوب معالجته (YYYY-MM-DD). الافتراضي: تاريخ اليوم في المنطقة الزمنية المحلية.",
        )

    def handle(self, *args, **options):
        from school.models import AttendanceRecord  # type: ignore
        from discipline.models import Absence  # type: ignore

        # Resolve target date
        dt_str = (options.get("date_str") or "").strip()
        if dt_str:
            try:
                target_date: _date = _date.fromisoformat(dt_str[:10])
            except Exception:
                self.stderr.write(self.style.ERROR("صيغة التاريخ غير صحيحة. استخدم YYYY-MM-DD."))
                return 1
        else:
            target_date = timezone.localdate()

        self.stdout.write(self.style.NOTICE(f"Finalizing attendance for date: {target_date.isoformat()}"))

        # Find students absent in both first and second periods
        qs = AttendanceRecord.objects.filter(date=target_date, status="absent")
        # Some schemas may name the period field differently; use period_number when available
        try:
            p1 = qs.filter(period_number=1).values_list("student_id", flat=True)
            p2 = qs.filter(period_number=2).values_list("student_id", flat=True)
        except Exception:
            # If period_number doesn't exist, nothing to do
            self.stdout.write(self.style.WARNING("لم يتم العثور على الحقل period_number؛ لا يمكن تطبيق قاعدة الحصتين."))
            return 0

        s1 = set(int(x) for x in p1)
        s2 = set(int(x) for x in p2)
        candidates = sorted(s1.intersection(s2))

        created = 0
        existed = 0
        with transaction.atomic():
            for sid in candidates:
                obj, was_created = Absence.objects.get_or_create(
                    student_id=sid,
                    date=target_date,
                    defaults={
                        "type": "FULL_DAY",
                        "status": "UNEXCUSED",
                        "source": "ATTENDANCE_SYSTEM",
                        "notes": "Auto-finalized: absent in periods 1 and 2",
                    },
                )
                if was_created:
                    created += 1
                else:
                    existed += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"تمت معالجة {len(candidates)} طالبًا. أُنشئ {created} سجل غياب يوم كامل، وتوجد مسبقًا {existed} سجلات."
            )
        )
        return 0
