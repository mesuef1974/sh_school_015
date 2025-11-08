from __future__ import annotations

from datetime import date, timedelta
from typing import Optional, Tuple, Iterable

from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command

# Local lightweight date parser to avoid cross-app import issues
from datetime import date as _date


def parse_ui_or_iso_date(s: Optional[str]) -> Optional[_date]:
    if not s:
        return None
    s = s.strip()
    if not s:
        return None
    try:
        if "/" in s:
            d, m, y = s.split("/")
            if len(y) == 4:
                return _date(int(y), int(m), int(d))
    except Exception:
        pass
    try:
        if "-" in s and len(s) >= 10:
            return _date.fromisoformat(s[:10])
    except Exception:
        pass
    return None


def _dow(d: date) -> int:
    # Project day mapping 1..7 with Sun=1 .. Sat=7
    # Python weekday: Mon=0..Sun=6
    m = {0: 2, 1: 3, 2: 4, 3: 5, 4: 6, 5: 7, 6: 1}
    return m[d.weekday()]


def _week_range_from_any(dt: date) -> Tuple[date, date]:
    """Return (start, end) for the school working week containing dt.

    The project uses Sun..Thu as working days (1..5). We take:
    - start = the Sunday of that week
    - end   = the Thursday of that week
    """
    # find Sunday (python weekday == 6)
    days_back_to_sun = (dt.weekday() - 6) % 7
    start = dt - timedelta(days=days_back_to_sun)
    end = start + timedelta(days=4)  # Sun..Thu
    return start, end


def _daterange(a: date, b: date) -> Iterable[date]:
    cur = a
    while cur <= b:
        yield cur
        cur = cur + timedelta(days=1)


class Command(BaseCommand):
    help = "Seed realistic FAKE attendance for a wing across a full week or a custom date range by orchestrating seed_wing_day_demo."

    def add_arguments(self, parser):
        parser.add_argument("--wing", type=int, default=5, help="Wing ID to seed (default: 5)")
        parser.add_argument(
            "--week",
            type=str,
            default=None,
            help="Any date inside the target week (YYYY-MM-DD or DD/MM/YYYY). If omitted, use today's date.",
        )
        parser.add_argument("--start", type=str, default=None, help="Explicit start date (YYYY-MM-DD or DD/MM/YYYY)")
        parser.add_argument("--end", type=str, default=None, help="Explicit end date (YYYY-MM-DD or DD/MM/YYYY)")
        parser.add_argument("--seed", type=int, default=42, help="Random seed base for reproducibility")
        parser.add_argument("--dry-run", action="store_true", help="Do not write to DB, only print summaries")
        parser.add_argument(
            "--p12-absent",
            type=float,
            default=None,
            help="Target absent ratio (0..1) for periods 1 and 2 (e.g., 0.10 for 10%)",
        )
        parser.add_argument(
            "--finalize",
            action="store_true",
            help="Lock created records and daily summaries (closed)",
        )
        parser.add_argument(
            "--approve",
            action="store_true",
            help="Mark generated entries as approved by wing supervisor (note tag; source=office)",
        )
        parser.add_argument(
            "--summary",
            action="store_true",
            help="Print per-day summaries during seeding (delegates to day command)",
        )
        parser.add_argument(
            "--workflow",
            choices=["teacher", "supervisor", "all"],
            default="all",
            help=(
                "Workflow simulation: "
                "teacher = create demo without approval/finalize; "
                "supervisor = approve+finalize existing demo for the range; "
                "all = perform teacher phase then supervisor phase consecutively."
            ),
        )
        parser.add_argument(
            "--with-exits",
            action="store_true",
            help="Also seed ExitEvent records (approved/closed)",
        )
        parser.add_argument(
            "--with-alerts",
            action="store_true",
            help="Also issue AbsenceAlert for the week (archived)",
        )
        parser.add_argument("--with-behavior", action="store_true", help="Also seed behavior incidents if supported")

    def handle(self, *args, **opts):
        from django.utils import timezone

        wing_id: int = int(opts["wing"])
        dry_run: bool = bool(opts.get("dry_run"))
        wk = parse_ui_or_iso_date(opts.get("week")) if opts.get("week") else timezone.localdate()
        start = parse_ui_or_iso_date(opts.get("start")) if opts.get("start") else None
        end = parse_ui_or_iso_date(opts.get("end")) if opts.get("end") else None

        if (start and not end) or (end and not start):
            raise CommandError("When specifying a custom range, both --start and --end must be provided.")

        if start and end:
            if end < start:
                raise CommandError("--end must be >= --start")
            rng = (start, end)
        else:
            rng = _week_range_from_any(wk)

        start, end = rng
        self.stdout.write(self.style.NOTICE(f"Seeding wing {wing_id} for range {start} -> {end}"))

        # Prepare list of working days (Sun..Thu), but we still attempt all; day command will skip gracefully if no timetable
        days = [d for d in _daterange(start, end) if _dow(d) in (1, 2, 3, 4, 5)]
        if not days:
            self.stdout.write(self.style.WARNING("No working days in selected range."))
            return

        # Default extras: enable exits and alerts if no explicit flags were passed
        if not any([opts.get("with_exits"), opts.get("with_alerts"), opts.get("with_behavior")]):
            opts["with_exits"] = True
            opts["with_alerts"] = True

        # Pass-through options to day command
        base_kwargs = {
            "wing": wing_id,
            "p12_absent": opts.get("p12_absent"),
            "seed": int(opts.get("seed") or 42),
            "dry_run": dry_run,
            "summary": bool(opts.get("summary")),
        }

        workflow: str = opts.get("workflow") or "all"

        def run_phase(approve: bool, finalize: bool, seed_offset: int = 0, banner: str = ""):
            if banner:
                self.stdout.write(self.style.NOTICE(banner))
            for i, d in enumerate(days):
                # vary seed per day to keep distributions realistic but reproducible
                kw = dict(base_kwargs)
                kw["date"] = d.isoformat()
                kw["seed"] = int(base_kwargs["seed"]) + seed_offset + i
                if approve:
                    kw["approve"] = True
                if finalize:
                    kw["finalize"] = True
                # call the existing day seeder; it is idempotent and removes previous [demo] for that day/wing
                call_command("seed_wing_day_demo", **kw)

        if workflow == "teacher":
            # Teacher fills data without approvals/finalization
            run_phase(approve=False, finalize=False, seed_offset=0, banner="-- Teacher phase --")
        elif workflow == "supervisor":
            # Supervisor validates and finalizes (recreates entries with approval/finalization flags)
            run_phase(approve=True, finalize=True, seed_offset=1000, banner="-- Supervisor phase --")
        else:  # all
            run_phase(approve=False, finalize=False, seed_offset=0, banner="-- Teacher phase --")
            # Immediately follow with supervisor phase (uses different seed to slightly vary notes/minutes while keeping shape)
            run_phase(approve=True, finalize=True, seed_offset=1000, banner="-- Supervisor phase --")

        # --- Optional extras: ExitEvent, AbsenceAlert, Behavior incidents ---
        extras_summary = {"exits": 0, "alerts": 0, "behavior": 0}
        try:
            if opts.get("with_exits"):
                extras_summary["exits"] = self._seed_exits_for_range(wing_id, start, end)
        except Exception as ex:
            self.stderr.write(self.style.WARNING(f"ExitEvent seeding skipped due to error: {ex}"))
        try:
            if opts.get("with_alerts"):
                extras_summary["alerts"] = self._seed_absence_alerts_for_range(wing_id, start, end)
        except Exception as ex:
            self.stderr.write(self.style.WARNING(f"AbsenceAlert seeding skipped due to error: {ex}"))
        try:
            if opts.get("with_behavior"):
                # Behavior module not found in this codebase; print a friendly notice
                self.stdout.write(self.style.WARNING("Behavior incidents model not found; skipping behavior seeding."))
        except Exception:
            pass

        # Print extras summary if any
        if any(extras_summary.values()):
            self.stdout.write(
                self.style.NOTICE(
                    f"Extras: ExitEvent={extras_summary['exits']}, AbsenceAlert={extras_summary['alerts']}, Behavior={extras_summary['behavior']}"
                )
            )

        self.stdout.write(self.style.SUCCESS("Week seeding completed."))

    # --- helpers ---
    def _seed_exits_for_range(self, wing_id: int, start: date, end: date) -> int:
        """Create ExitEvent sessions for excused/left_early attendance in range and approve/close them.
        Idempotent for demo by removing prior demo-tagged ExitEvent notes for the range and wing.
        Returns count created.
        """
        from django.utils import timezone
        from django.contrib.auth.models import User
        from school.models import ExitEvent, AttendanceRecord, Wing

        DEMO_TAG = "[demo]"

        wing = Wing.objects.get(pk=wing_id)
        # Remove prior demo exit events in this range for this wing
        ExitEvent.objects.filter(
            date__gte=start,
            date__lte=end,
            classroom__wing_id=wing_id,
            note__icontains=DEMO_TAG,
        ).delete()

        # Find candidate attendance records
        qs = AttendanceRecord.objects.filter(
            date__gte=start,
            date__lte=end,
            classroom__wing_id=wing_id,
            status__in=["excused", "left_early"],
        ).select_related("student", "classroom")

        # Reviewer: wing supervisor user if set; else any superuser; else None
        reviewer_user = None
        if getattr(wing, "supervisor_id", None) and getattr(wing.supervisor, "user_id", None):
            reviewer_user = wing.supervisor.user
        if not reviewer_user:
            reviewer_user = User.objects.filter(is_superuser=True).first()

        created = 0
        now = timezone.now()
        for rec in qs.iterator():
            ev = ExitEvent(
                student=rec.student,
                classroom=rec.classroom,
                date=rec.date,
                period_number=rec.period_number,
                reason=(rec.exit_reasons or "wing")[:20] or "wing",
                note=f"{DEMO_TAG} auto exit for {rec.status}",
                review_status="approved",
                reviewer=reviewer_user,
                reviewed_at=now,
                review_comment="تم الاعتماد تلقائيًا لبيانات العرض [demo]",
                attendance_record=rec,
            )
            # Close immediately with a realistic duration if timestamps exist; otherwise set short duration
            try:
                if rec.exit_left_at and rec.exit_returned_at:
                    ev.started_at = rec.exit_left_at
                    ev.returned_at = rec.exit_returned_at
                else:
                    # fabricate timestamps inside the same day
                    ev.started_at = timezone.make_aware(timezone.datetime.combine(rec.date, rec.start_time))
                    ev.returned_at = ev.started_at + timezone.timedelta(minutes=max(10, rec.early_minutes or 15))
                ev.duration_seconds = int((ev.returned_at - ev.started_at).total_seconds())
            except Exception:
                pass
            ev.save()
            created += 1
        return created

    def _seed_absence_alerts_for_range(self, wing_id: int, start: date, end: date) -> int:
        """Issue AbsenceAlert for students with >=2 unexcused daily absences within the range.
        Generates and attaches DOCX file via renderer. Idempotent for demo by removing prior demo alerts for the week.
        Returns count created.
        """
        from django.contrib.auth.models import User
        from django.utils import timezone
        from django.core.files.base import ContentFile
        from school.models import AttendanceDaily, AcademicYear, Wing
        from apps.attendance.models_alerts import (
            AbsenceAlert,
            AlertNumberSequence,
            AbsenceAlertDocument,
        )
        from apps.attendance.services.word_renderer import render_alert_docx

        DEMO_TAG = "[demo]"

        wing = Wing.objects.get(pk=wing_id)
        # Determine academic year for the range (pick the one covering start)
        ay = (
            AcademicYear.objects.filter(start_date__lte=start, end_date__gte=end).first()
            or AcademicYear.objects.filter(start_date__lte=start, end_date__gte=start).first()
            or AcademicYear.objects.order_by("-is_current").first()
        )
        year_name = ay.name if ay else "N/A"

        # Delete prior demo alerts in this range for this wing
        AbsenceAlert.objects.filter(
            wing_id=wing_id,
            period_start__gte=start,
            period_end__lte=end,
            notes__icontains=DEMO_TAG,
        ).delete()

        # Aggregate unexcused days per student in this wing for the range
        dqs = AttendanceDaily.objects.filter(
            date__gte=start,
            date__lte=end,
            wing_id=wing_id,
        ).select_related("student", "school_class")
        per_student = {}
        for d in dqs.iterator():
            st = per_student.setdefault(
                d.student_id,
                {"excused": 0, "unexcused": 0, "student": d.student, "class": d.school_class},
            )
            if d.daily_excused:
                st["excused"] += 1
            elif d.absent_periods > 0:
                st["unexcused"] += 1

        created = 0
        creator = None
        # Choose creator: wing supervisor user or first superuser
        if getattr(wing, "supervisor_id", None) and getattr(wing.supervisor, "user_id", None):
            creator = wing.supervisor.user
        if not creator:
            creator = User.objects.filter(is_superuser=True).first()

        for stu_id, agg in per_student.items():
            if agg["unexcused"] >= 2:
                number = AlertNumberSequence.next_number(year_name)
                alert = AbsenceAlert.objects.create(
                    number=number,
                    academic_year=year_name,
                    student=agg["student"],
                    class_name=agg["class"].name if agg.get("class") else "",
                    parent_name=agg["student"].parent_name or "",
                    parent_mobile=agg["student"].parent_phone or "",
                    period_start=start,
                    period_end=end,
                    excused_days=agg["excused"],
                    unexcused_days=agg["unexcused"],
                    notes=f"{DEMO_TAG} Auto-issued for weekly unexcused absences",
                    status="archived",
                    created_by=creator or User.objects.first(),
                    wing=wing,
                    delivered_via="sms",
                    delivered_at=timezone.now(),
                )
                # Render and attach DOCX
                try:
                    content = render_alert_docx(alert)
                    if content:
                        doc = AbsenceAlertDocument(alert=alert, created_by=alert.created_by)
                        doc.file.save(
                            f"absence-alert-{alert.academic_year}-{alert.number}.docx",
                            ContentFile(content),
                        )
                        doc.size = doc.file.size or 0
                        doc.save()
                except Exception:
                    # Non-fatal: proceed without doc
                    pass
                created += 1
        return created
