from django.core.management.base import BaseCommand
from django.db import transaction
from datetime import date, time

# Resilient import: support running as a Django management command and as a standalone script
try:
    # Preferred absolute import (works when Django is set up, or when backend is on sys.path)
    from school.models import (
        AcademicYear,
        Term,
        AttendancePolicy,
        PeriodTemplate,
        TemplateSlot,
        Wing,
        SchoolHoliday,
    )
except Exception:
    # Fallback: configure Django environment for direct execution
    import os
    import sys
    from pathlib import Path

    # Add the backend directory (that contains core/settings.py) to sys.path
    backend_dir = Path(__file__).resolve().parents[3]  # .../backend
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    # Ensure Django settings are configured
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

    import django

    django.setup()

    # Retry absolute import after environment setup
    from school.models import (
        AcademicYear,
        Term,
        AttendancePolicy,
        PeriodTemplate,
        TemplateSlot,
        Wing,
        SchoolHoliday,
    )


class Command(BaseCommand):
    help = "Initialize academic year 2025-2026, terms, attendance policy, school wings, and period templates."

    @transaction.atomic
    def handle(self, *args, **options):
        # 1) Academic year
        ay, ay_created = AcademicYear.objects.update_or_create(
            name="2025-2026",
            defaults={
                "start_date": date(2025, 8, 31),
                "end_date": date(2026, 6, 30),
                "is_current": True,
            },
        )
        if ay_created:
            self.stdout.write(self.style.SUCCESS("Created AcademicYear 2025-2026"))
        else:
            self.stdout.write(self.style.WARNING("Updated/Ensured AcademicYear 2025-2026"))

        # Ensure only one is_current
        AcademicYear.objects.exclude(pk=ay.pk).filter(is_current=True).update(is_current=False)

        # 2) Terms (Semesters)
        t1, t1_created = Term.objects.update_or_create(
            academic_year=ay,
            name="الفصل الأول",
            defaults={
                "start_date": date(2025, 8, 31),
                "end_date": date(2025, 12, 20),
                "is_current": False,
            },
        )
        t2, t2_created = Term.objects.update_or_create(
            academic_year=ay,
            name="الفصل الثاني",
            defaults={
                "start_date": date(2026, 1, 5),
                "end_date": date(2026, 6, 30),
                "is_current": True,
            },
        )
        Term.objects.exclude(pk=t2.pk).update(is_current=False)
        self.stdout.write(self.style.SUCCESS("Ensured terms (الفصل الأول/الفصل الثاني)"))

        # 3) Attendance policies for both terms
        for term in (t1, t2):
            AttendancePolicy.objects.update_or_create(
                term=term,
                defaults={
                    "late_threshold_minutes": 5,
                    "late_to_equivalent_period_minutes": 45,
                    "first_two_periods_numbers": [1, 2],
                    "lesson_lock_after_minutes": 120,
                    "daily_lock_time": time(14, 30),
                    "working_days": [1, 2, 3, 4, 5],  # Sun..Thu (Sun=1)
                },
            )
        self.stdout.write(self.style.SUCCESS("Attendance policies created/updated"))

        # 4) Wings 1..5
        wings = [
            ("الجناح 1", "أرضي", "7-1 إلى 7-5"),
            ("الجناح 2", "أرضي", "8-1 إلى 8-4 + 9-1"),
            ("الجناح 3", "علوي", "9-2 إلى 9-4 + 10-1 + 10-2"),
            ("الجناح 4", "علوي", "10-3 + 10-4 + 11-1 + 11-2 + 11-3"),
            ("الجناح 5", "علوي", "11-4 + 12-1 إلى 12-4"),
        ]
        for name, floor, notes in wings:
            Wing.objects.update_or_create(name=name, defaults={"floor": floor, "notes": notes})
        self.stdout.write(self.style.SUCCESS("Wings ensured (1..5)"))

        # 5) Period templates and slots (based on DOC/school_DATA/time_table.png)
        def ensure_template(code: str, name: str, day_of_week: int, scope: str, slots: list[dict]):
            tpl, _ = PeriodTemplate.objects.update_or_create(
                code=code,
                defaults={"name": name, "day_of_week": day_of_week, "scope": scope},
            )
            # Replace slots
            tpl.slots.all().delete()
            for s in slots:
                TemplateSlot.objects.create(
                    template=tpl,
                    number=s.get("no"),
                    start_time=s["start"],
                    end_time=s["end"],
                    kind=s.get("kind", "lesson"),
                )
            return tpl

        # Helper:
        def t(hh, mm):
            return time(hh, mm)

        # Sun–Wed (Ground)
        ensure_template(
            code="sun_wed_ground",
            name="الأحد–الأربعاء (أرضي)",
            day_of_week=1,  # Sun=1
            scope="ground",
            slots=[
                {"no": 1, "start": t(7, 10), "end": t(8, 0)},
                {"no": 2, "start": t(8, 0), "end": t(8, 50)},
                {"no": 3, "start": t(8, 50), "end": t(9, 35)},
                {"kind": "recess", "start": t(9, 35), "end": t(9, 55)},
                {"no": 4, "start": t(9, 55), "end": t(10, 50)},
                {"no": 5, "start": t(10, 50), "end": t(11, 35)},
                {"no": 6, "start": t(11, 35), "end": t(12, 20)},
                {"kind": "prayer", "start": t(12, 20), "end": t(12, 40)},
                {"no": 7, "start": t(12, 40), "end": t(13, 30)},
            ],
        )

        # Sun–Wed (Upper)
        ensure_template(
            code="sun_wed_upper",
            name="الأحد–الأربعاء (علوي)",
            day_of_week=1,
            scope="upper",
            slots=[
                {"no": 1, "start": t(7, 10), "end": t(8, 0)},
                {"no": 2, "start": t(8, 0), "end": t(8, 45)},
                {"no": 3, "start": t(8, 45), "end": t(9, 35)},
                {"no": 4, "start": t(9, 35), "end": t(10, 25)},
                {"kind": "recess", "start": t(10, 25), "end": t(10, 45)},
                {"no": 5, "start": t(10, 45), "end": t(11, 35)},
                {"no": 6, "start": t(11, 35), "end": t(12, 25)},
                {"no": 7, "start": t(12, 25), "end": t(13, 10)},
                {"kind": "prayer", "start": t(13, 10), "end": t(13, 30)},
            ],
        )

        # Thursday (Secondary)
        ensure_template(
            code="thu_secondary",
            name="الخميس (ثانوي)",
            day_of_week=5,
            scope="secondary",
            slots=[
                {"no": 1, "start": t(7, 10), "end": t(7, 55)},
                {"no": 2, "start": t(7, 55), "end": t(8, 40)},
                {"no": 3, "start": t(8, 40), "end": t(9, 20)},
                {"no": 4, "start": t(9, 20), "end": t(10, 5)},
                {"kind": "recess", "start": t(10, 5), "end": t(10, 25)},
                {"no": 5, "start": t(10, 25), "end": t(11, 10)},
                {"no": 6, "start": t(11, 10), "end": t(11, 50)},
                {"no": 7, "start": t(11, 50), "end": t(12, 30)},
                {"kind": "prayer", "start": t(12, 30), "end": t(12, 45)},
            ],
        )

        # Thursday (Grade 9 - sections 2/3/4)
        ensure_template(
            code="thu_grade9_2_3_4",
            name="الخميس (تاسع 2-3-4)",
            day_of_week=5,
            scope="grade9",
            slots=[
                {"no": 1, "start": t(7, 10), "end": t(8, 0)},
                {"no": 2, "start": t(8, 0), "end": t(8, 50)},
                {"no": 3, "start": t(8, 50), "end": t(9, 35)},
                {"kind": "recess", "start": t(9, 35), "end": t(9, 55)},
                {"no": 4, "start": t(9, 55), "end": t(10, 50)},
                {"no": 5, "start": t(10, 50), "end": t(11, 40)},
                {"no": 6, "start": t(11, 40), "end": t(12, 30)},
                {"kind": "prayer", "start": t(12, 30), "end": t(12, 40)},
            ],
        )

        # Thursday (Ground)
        ensure_template(
            code="thu_ground",
            name="الخميس (أرضي)",
            day_of_week=5,
            scope="ground",
            slots=[
                {"no": 1, "start": t(7, 10), "end": t(8, 0)},
                {"no": 2, "start": t(8, 0), "end": t(8, 50)},
                {"no": 3, "start": t(8, 50), "end": t(9, 35)},
                {"kind": "recess", "start": t(9, 35), "end": t(9, 55)},
                {"no": 4, "start": t(9, 55), "end": t(10, 50)},
                {"no": 5, "start": t(10, 50), "end": t(11, 35)},
                {"kind": "prayer", "start": t(11, 35), "end": t(11, 55)},
                {"no": 6, "start": t(11, 55), "end": t(12, 40)},
            ],
        )

        self.stdout.write(self.style.SUCCESS("Period templates and slots ensured"))

        # 6) School holidays (based on provided 2025–2026 calendar image)
        holidays = [
            ("إجازة منتصف الفصل (ت1)", date(2025, 10, 26), date(2025, 10, 30)),
            ("إجازة منتصف العام الأكاديمي", date(2025, 12, 21), date(2026, 1, 3)),
            ("إجازة (رمضان)", date(2026, 3, 15), date(2026, 3, 20)),
            ("إجازة نهاية أسبوع مطولة", date(2026, 4, 8), date(2026, 4, 9)),
            ("إجازة الموظفين في المدارس", date(2026, 6, 28), date(2026, 8, 19)),
        ]
        created_or_updated = 0
        for title, start_d, end_d in holidays:
            obj, _ = SchoolHoliday.objects.update_or_create(
                title=title, defaults={"start": start_d, "end": end_d}
            )
            created_or_updated += 1
        self.stdout.write(
            self.style.SUCCESS(f"School holidays ensured ({created_or_updated} entries)")
        )

        self.stdout.write(self.style.SUCCESS("Initialization completed successfully."))
