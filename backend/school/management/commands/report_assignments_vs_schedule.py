from collections import defaultdict
from dataclasses import dataclass
from typing import List, Dict, Tuple

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Sum

from school.models import (
    TeachingAssignment,
    TimetableEntry,
    CalendarTemplate,
)


@dataclass
class AssignmentRow:
    teacher: str
    classroom: str
    subject: str
    expected: int
    scheduled: int
    delta: int


class Command(BaseCommand):
    help = (
        "Compare TeachingAssignments (expected weekly loads) against actual TimetableEntries "
        "for a chosen CalendarTemplate, and print a professional summary report."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--template",
            dest="template_name",
            help="CalendarTemplate name to check (default: 'الجدول الرسمي')",
        )
        parser.add_argument(
            "--template-id",
            dest="template_id",
            type=int,
            help="CalendarTemplate ID to check (overrides --template)",
        )
        parser.add_argument(
            "--only-mismatches",
            action="store_true",
            help="Show only rows where expected != scheduled",
        )
        parser.add_argument(
            "--teacher",
            dest="teacher_contains",
            help="Filter to teacher name contains (optional)",
        )

    def handle(self, *args, **options):
        template = None
        if options.get("template_id"):
            template = CalendarTemplate.objects.filter(id=options["template_id"]).first()
            if not template:
                raise CommandError(f"Template with id={options['template_id']} not found")
        else:
            tname = options.get("template_name") or "الجدول الرسمي"
            template = CalendarTemplate.objects.filter(name=tname).first()
            if not template:
                raise CommandError(f"Template '{tname}' not found")

        only_mismatches: bool = options.get("only_mismatches", False)
        teacher_contains = (options.get("teacher_contains") or "").strip()

        # Build scheduled counts per (teacher_id, classroom_id, subject_id)
        scheduled_qs = (
            TimetableEntry.objects.filter(slot__template=template)
            .values("teacher_id", "classroom_id", "subject_id")
            .annotate(cnt=Sum(1))
        )
        scheduled_map: Dict[Tuple[int, int, int], int] = {}
        for r in scheduled_qs:
            scheduled_map[(r["teacher_id"], r["classroom_id"], r["subject_id"])] = (
                int(r["cnt"]) if r["cnt"] is not None else 0
            )

        rows: List[AssignmentRow] = []
        per_teacher_expected: Dict[int, int] = defaultdict(int)
        per_teacher_scheduled: Dict[int, int] = defaultdict(int)
        per_class_expected: Dict[int, int] = defaultdict(int)
        per_class_scheduled: Dict[int, int] = defaultdict(int)

        assignments = TeachingAssignment.objects.select_related("teacher", "classroom", "subject")
        if teacher_contains:
            assignments = assignments.filter(teacher__full_name__icontains=teacher_contains)

        for a in assignments:
            key = (a.teacher_id, a.classroom_id, a.subject_id)
            scheduled = scheduled_map.get(key, 0)
            expected = int(a.no_classes_weekly)
            delta = scheduled - expected

            rows.append(
                AssignmentRow(
                    teacher=a.teacher.full_name,
                    classroom=a.classroom.name,
                    subject=a.subject.name_ar,
                    expected=expected,
                    scheduled=scheduled,
                    delta=delta,
                )
            )

            per_teacher_expected[a.teacher_id] += expected
            per_teacher_scheduled[a.teacher_id] += scheduled
            per_class_expected[a.classroom_id] += expected
            per_class_scheduled[a.classroom_id] += scheduled

        # Sort rows by teacher, classroom
        rows.sort(key=lambda r: (r.teacher, r.classroom, r.subject))

        if only_mismatches:
            rows = [r for r in rows if r.delta != 0]

        # Print report
        self.stdout.write(
            self.style.NOTICE("\nتقرير مقارنة التكليفات مع الجدول — %s\n" % template.name)
        )
        self.stdout.write("-" * 90)
        self.stdout.write(f"عدد التكليفات المفحوصة: {assignments.count()}\n")

        # Assignment-level table
        self.stdout.write("تفصيل على مستوى التكليف (المعلم/الصف/المادة):")
        self.stdout.write("teacher | classroom | subject | expected | scheduled | delta")
        for r in rows:
            mark = "" if r.delta == 0 else ("+" if r.delta > 0 else "-")
            self.stdout.write(
                f"{r.teacher} | {r.classroom} | {r.subject} | {r.expected:2d} | {r.scheduled:2d} | {r.delta:+d} {mark}"
            )

        # Summaries per teacher
        self.stdout.write("\nملخص بحسب المعلّم:")
        self.stdout.write("teacher | expected_total | scheduled_total | delta")
        # Load teacher names
        teacher_names = {a.teacher_id: a.teacher.full_name for a in assignments}
        for tid in sorted(teacher_names.keys(), key=lambda i: teacher_names[i]):
            exp = per_teacher_expected.get(tid, 0)
            sch = per_teacher_scheduled.get(tid, 0)
            d = sch - exp
            self.stdout.write(f"{teacher_names[tid]} | {exp:3d} | {sch:3d} | {d:+d}")

        # Summaries per class
        self.stdout.write("\nملخص بحسب الصف:")
        self.stdout.write("classroom | expected_total | scheduled_total | delta")
        class_names = {a.classroom_id: a.classroom.name for a in assignments}
        for cid in sorted(class_names.keys(), key=lambda i: class_names[i]):
            exp = per_class_expected.get(cid, 0)
            sch = per_class_scheduled.get(cid, 0)
            d = sch - exp
            self.stdout.write(f"{class_names[cid]} | {exp:3d} | {sch:3d} | {d:+d}")

        # Overall totals
        total_exp = sum(per_teacher_expected.values())
        total_sch = sum(per_teacher_scheduled.values())
        self.stdout.write("\nالإجمالي:")
        self.stdout.write(
            f"expected={total_exp} scheduled={total_sch} delta={total_sch - total_exp:+d}"
        )

        # Guidance
        self.stdout.write("\nملاحظات:\n")
        self.stdout.write("- delta>0 يعني حصص مجدولة أكثر من التكليف (زيادة).\n")
        self.stdout.write("- delta<0 يعني حصص مجدولة أقل من التكليف (عجز).\n")
        self.stdout.write(
            "- استعمل --only-mismatches لعرض الفروقات فقط، و--teacher لتصفية معلم بالاسم.\n"
        )
