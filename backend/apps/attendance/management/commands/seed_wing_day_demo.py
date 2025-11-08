from __future__ import annotations

import random
from datetime import datetime, date, timedelta
from typing import Iterable, Dict, Tuple

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from school.models import (
    AttendanceRecord,
    AttendanceDaily,
    Class,
    Student,
    Term,
    TimetableEntry,
    Wing,
)

# Probabilities for statuses per period (sum <= 1; remaining goes to present)
P_STATUS = {
    "absent": 0.05,
    "late": 0.06,
    "left_early": 0.03,
    "excused": 0.02,
    "runaway": 0.005,
}

DEMO_TAG = "[demo]"
APPROVAL_TAG = "[approved_by_wing_supervisor]"


def _dow(d: date) -> int:
    # Project uses 1..7 (Sun..Sat)
    # Python: Monday=0..Sunday=6
    py = d.weekday()  # Mon=0
    # Convert to 1..7 with Sun=7
    # Mon(0)->2, Tue->3, Wed->4, Thu->5, Fri->6, Sat->7?, Sun ???
    # But TimetableEntry uses 1..5 (Sun..Thu). Let's map: Sun=1, Mon=2, Tue=3, Wed=4, Thu=5, Fri=6, Sat=7
    # Python weekday: Mon=0..Sun=6 => Sun is 6
    m = {0: 2, 1: 3, 2: 4, 3: 5, 4: 6, 5: 7, 6: 1}
    return m[py]


def pick_status() -> str:
    r = random.random()
    cum = 0.0
    for k, p in P_STATUS.items():
        cum += p
        if r <= cum:
            return k
    return "present"


def compute_daily_from_periods(period_statuses: Iterable[Tuple[str, int, int]]) -> Dict[str, int | bool]:
    present_periods = 0
    absent_periods = 0
    runaway_periods = 0
    excused_periods = 0
    late_minutes = 0
    early_minutes = 0

    for status, late_m, early_m in period_statuses:
        if status == "present":
            present_periods += 1
        elif status == "late":
            present_periods += 1
            late_minutes += late_m
        elif status == "absent":
            absent_periods += 1
        elif status == "runaway":
            runaway_periods += 1
        elif status in ("excused", "left_early"):
            excused_periods += 1
            if early_m:
                early_minutes += early_m

    daily_absent_unexcused = absent_periods > 0 and (present_periods == 0)
    daily_excused = excused_periods > 0 and absent_periods == 0
    daily_excused_partial = excused_periods > 0 and present_periods > 0

    return {
        "present_periods": present_periods,
        "absent_periods": absent_periods,
        "runaway_periods": runaway_periods,
        "excused_periods": excused_periods,
        "late_minutes": late_minutes,
        "early_minutes": early_minutes,
        "daily_absent_unexcused": daily_absent_unexcused,
        "daily_excused": daily_excused,
        "daily_excused_partial": daily_excused_partial,
    }


class Command(BaseCommand):
    help = "Seed realistic FAKE attendance for a wing on a specific date (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument("--wing", type=int, default=5, help="Wing ID to seed (default: 5)")
        parser.add_argument(
            "--date",
            type=str,
            default="2025-11-03",
            help="Date in YYYY-MM-DD or DD/MM/YYYY (default: 2025-11-03)",
        )
        parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
        parser.add_argument("--dry-run", action="store_true", help="Do not write to DB, only report counts")
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
            help="Print professional summary percentages per class and overall after seeding",
        )

    def handle(self, *args, **opts):
        from apps.common.date_utils import parse_ui_or_iso_date

        wing_id: int = opts["wing"]
        dt = parse_ui_or_iso_date(opts["date"]) if isinstance(opts["date"], str) else opts["date"]
        if not dt:
            raise CommandError("Invalid --date. Use YYYY-MM-DD or DD/MM/YYYY")

        # Guard: do not seed on Fridays or Saturdays (Sun→Thu working days)
        if dt.weekday() in (4, 5):  # Fri=4, Sat=5 in Python
            self.stdout.write(self.style.WARNING(f"{dt} is Fri/Sat; skipping seeding for weekends."))
            return

        random.seed(int(opts["seed"]))

        try:
            wing = Wing.objects.get(pk=wing_id)
        except Wing.DoesNotExist:
            raise CommandError(f"Wing id={wing_id} not found")

        # Resolve term covering date
        term = Term.objects.filter(start_date__lte=dt, end_date__gte=dt).order_by("-is_current").first()
        if not term:
            raise CommandError(f"No Term covering date {dt}")

        self.stdout.write(self.style.NOTICE(f"Seeding demo attendance for Wing {wing_id} – {wing.name} on {dt}"))

        # Classes and students in the wing
        classes = list(Class.objects.filter(wing_id=wing_id))
        if not classes:
            raise CommandError(f"No classes found in Wing {wing_id}")

        students = list(
            Student.objects.filter(class_fk__in=classes, active=True).select_related("class_fk").order_by("sid")
        )
        if not students:
            raise CommandError(f"No active students in Wing {wing_id}")

        dow = _dow(dt)
        # Timetable entries for those classes for that day and term
        entries = list(
            TimetableEntry.objects.filter(classroom__in=classes, day_of_week=dow, term=term)
            .select_related("classroom", "subject", "teacher")
            .order_by("classroom_id", "period_number")
        )
        if not entries:
            self.stdout.write(self.style.WARNING("No timetable entries for this day; nothing to seed."))
            return

        # We will need approximate period times. Try to get from first matching class' period template via related slots if available.
        # If not available, fall back to synthetic times starting 08:00 with 50-minute lessons.
        period_times: Dict[int, Tuple[datetime.time, datetime.time]] = {}
        try:
            # heuristic: search TemplateSlot for this day via PeriodTemplate
            from school.models import TemplateSlot

            slots = (
                TemplateSlot.objects.filter(template__day_of_week=dow, kind="lesson")
                .order_by("number")
                .values_list("number", "start_time", "end_time")
            )
            for num, st, et in slots:
                if num:
                    period_times[int(num)] = (st, et)
        except Exception:
            pass

        def get_times(pn: int) -> Tuple[datetime.time, datetime.time]:
            if pn in period_times:
                return period_times[pn]
            # fallback synthetic times
            base = datetime(dt.year, dt.month, dt.day, 8, 0)
            start = (base + timedelta(minutes=(pn - 1) * 50)).time()
            end = (base + timedelta(minutes=(pn - 1) * 50 + 45)).time()
            return start, end

        # Idempotency: delete previous demo records for this date and wing
        # We detect by note containing DEMO_TAG and classroom wing_id
        prior_qs = AttendanceRecord.objects.filter(
            date=dt,
            classroom__wing_id=wing_id,
            note__icontains=DEMO_TAG,
        )
        # We will not delete existing daily summaries to avoid overwriting real data

        created_records = 0
        created_daily = 0
        # Summary accumulators
        overall = {
            "total_periods": 0,
            "status": {
                "present": 0,
                "late": 0,
                "absent": 0,
                "runaway": 0,
                "excused": 0,
                "left_early": 0,
            },
            "late_minutes": 0,
            "early_minutes": 0,
            "p12_total": 0,
            "p12_absent": 0,
        }
        per_class: Dict[int, dict] = {}

        def _cls_acc(cid: int) -> dict:
            if cid not in per_class:
                per_class[cid] = {
                    "total_periods": 0,
                    "status": {
                        "present": 0,
                        "late": 0,
                        "absent": 0,
                        "runaway": 0,
                        "excused": 0,
                        "left_early": 0,
                    },
                    "late_minutes": 0,
                    "early_minutes": 0,
                    "p12_total": 0,
                    "p12_absent": 0,
                }
            return per_class[cid]

        with transaction.atomic():
            prior_count = prior_qs.count()
            if prior_count:
                self.stdout.write(self.style.WARNING(f"Removing {prior_count} previous demo records..."))
                if not opts["dry_run"]:
                    prior_qs.delete()

            class_names = {c.id: c.name for c in classes}

            # Build a mapping of class -> entries for efficiency
            by_class: Dict[int, list[TimetableEntry]] = {}
            for e in entries:
                by_class.setdefault(e.classroom_id, []).append(e)

            # Optional: enforce a target absence ratio for periods 1 and 2 per class
            forced_absent: Dict[tuple[int, int], set[int]] = {}
            p12_abs = opts.get("p12-absent")
            if p12_abs is not None:
                if p12_abs < 0 or p12_abs > 1:
                    raise CommandError("--p12-absent must be between 0 and 1 (e.g., 0.10)")
                # Group students by class
                class_students: Dict[int, list[Student]] = {}
                for stu in students:
                    class_students.setdefault(stu.class_fk_id, []).append(stu)
                # For each class that has period 1/2 entries, choose ~ratio of students to be absent in that period
                for class_id, ents in by_class.items():
                    pnums = {e.period_number for e in ents}
                    for pn in (1, 2):
                        if pn in pnums:
                            stus = class_students.get(class_id, [])
                            N = len(stus)
                            if N == 0:
                                continue
                            n_abs = round(p12_abs * N)
                            if p12_abs > 0 and n_abs == 0:
                                n_abs = 1
                            if n_abs > 0:
                                chosen = set(s.id for s in random.sample(stus, k=min(n_abs, N)))
                                forced_absent[(class_id, pn)] = chosen

            now = timezone.now()

            for stu in students:
                class_entries = by_class.get(stu.class_fk_id, [])
                period_details: list[Tuple[str, int, int]] = []
                created_any_for_student = False

                for e in class_entries:
                    # Skip if a record already exists for this key (do not overwrite real data)
                    exists = AttendanceRecord.objects.filter(
                        student=stu,
                        date=dt,
                        period_number=e.period_number,
                        term=term,
                    ).exists()
                    if exists:
                        continue

                    status = pick_status()
                    # Enforce forced absence for P1/P2 if configured
                    if (
                        stu.class_fk_id,
                        e.period_number,
                    ) in forced_absent and stu.id in forced_absent[(stu.class_fk_id, e.period_number)]:
                        status = "absent"
                    st_time, et_time = get_times(e.period_number)
                    late_m = 0
                    early_m = 0
                    note = f"{DEMO_TAG} auto-seeded"
                    exit_reasons = ""
                    exit_left_at = None
                    exit_returned_at = None

                    if status == "late":
                        late_m = random.randint(5, 18)
                        note = f"{DEMO_TAG} Late by {late_m}m"
                    elif status == "left_early":
                        early_m = random.randint(10, 25)
                        note = f"{DEMO_TAG} Left {early_m}m early"
                    elif status == "excused":
                        # Treat as exit permission during period
                        early_m = random.randint(15, 40)
                        exit_reasons = random.choice(["wing", "nurse", "admin"])  # restroom less likely as excuse
                        # Compose timestamps inside the period window
                        start_dt = datetime.combine(dt, st_time)
                        end_dt = datetime.combine(dt, et_time)
                        offset = random.randint(5, 25)
                        exit_left_at = timezone.make_aware(start_dt + timedelta(minutes=offset))
                        return_offset = min(offset + early_m, int((end_dt - start_dt).total_seconds() // 60) - 1)
                        exit_returned_at = timezone.make_aware(start_dt + timedelta(minutes=return_offset))
                        note = f"{DEMO_TAG} Excused by {exit_reasons}"
                    elif status == "runaway":
                        # Two flavors: no_show vs left_and_not_returned
                        note = f"{DEMO_TAG} runaway"

                    # Approval/finalization adjustments
                    if opts.get("approve"):
                        note = f"{note} {APPROVAL_TAG}".strip()
                    src = "office" if opts.get("approve") else "import"
                    is_locked = bool(opts.get("finalize"))

                    rec = AttendanceRecord(
                        student=stu,
                        classroom=stu.class_fk,
                        subject=e.subject,
                        teacher=e.teacher,
                        term=term,
                        date=dt,
                        day_of_week=dow,
                        period_number=e.period_number,
                        start_time=st_time,
                        end_time=et_time,
                        status=status,
                        late_minutes=late_m,
                        early_minutes=early_m,
                        note=note,
                        exit_reasons=exit_reasons,
                        exit_left_at=exit_left_at,
                        exit_returned_at=exit_returned_at,
                        source=src,
                        locked=is_locked,
                        created_at=now,
                        updated_at=now,
                    )

                    if not opts["dry_run"]:
                        rec.save()
                    created_records += 1
                    period_details.append((status, late_m, early_m))
                    created_any_for_student = True

                    # Accumulate summary stats
                    overall["total_periods"] += 1
                    overall["status"][status] = overall["status"].get(status, 0) + 1
                    overall["late_minutes"] += late_m
                    overall["early_minutes"] += early_m
                    ca = _cls_acc(stu.class_fk_id)
                    ca["total_periods"] += 1
                    ca["status"][status] = ca["status"].get(status, 0) + 1
                    ca["late_minutes"] += late_m
                    ca["early_minutes"] += early_m
                    if e.period_number in (1, 2):
                        overall["p12_total"] += 1
                        ca["p12_total"] += 1
                        if status == "absent":
                            overall["p12_absent"] += 1
                            ca["p12_absent"] += 1

                # Daily summary
                if class_entries and created_any_for_student:
                    agg = compute_daily_from_periods(period_details)
                    if not opts["dry_run"]:
                        # create daily summary only if not exists
                        daily_obj, created = AttendanceDaily.objects.get_or_create(
                            student=stu,
                            date=dt,
                            term=term,
                            defaults={
                                "school_class": stu.class_fk,
                                "wing": stu.class_fk.wing,
                                **agg,
                                "locked": bool(opts.get("finalize")),
                            },
                        )
                        # If it already existed, do not overwrite real data. Optionally lock if created only.
                        if created:
                            created_daily += 1
                    else:
                        created_daily += 1

        # If finalize requested, also lock daily summaries for this wing/date (safe bulk update)
        if opts.get("finalize") and not opts.get("dry_run"):
            AttendanceDaily.objects.filter(date=dt, term=term, student__class_fk__wing_id=wing_id).update(locked=True)

        # Optional professional summary output
        if opts.get("summary"):

            def pct(n, d):
                return (n * 100.0 / d) if d else 0.0

            self.stdout.write("")
            self.stdout.write(self.style.NOTICE("=== Summary (Wing {} on {}) ===".format(wing_id, dt)))
            # Per class
            for cid, acc in sorted(per_class.items(), key=lambda kv: class_names.get(kv[0], "")):
                tp = acc["total_periods"]
                p12t = acc["p12_total"]
                p12a = acc["p12_absent"]
                s = acc["status"]
                self.stdout.write(
                    f"Class {class_names.get(cid, cid)}: total={tp}, absent={s['absent']} ({pct(s['absent'], tp):.1f}%), "
                    f"late={s['late']} ({pct(s['late'], tp):.1f}%), excused={s['excused']} ({pct(s['excused'], tp):.1f}%), "
                    f"left_early={s['left_early']} ({pct(s['left_early'], tp):.1f}%), runaway={s['runaway']} ({pct(s['runaway'], tp):.2f}%) | "
                    f"P1-2 absent={p12a}/{p12t} ({pct(p12a, p12t):.1f}%) | late_min={acc['late_minutes']} early_min={acc['early_minutes']}"
                )
            # Overall
            s = overall["status"]
            tp = overall["total_periods"]
            p12t = overall["p12_total"]
            p12a = overall["p12_absent"]
            self.stdout.write("")
            self.stdout.write(
                self.style.SUCCESS(
                    "OVERALL: total={}, absent={} ({:.1f}%), late={} ({:.1f}%), excused={} ({:.1f}%), left_early={} ({:.1f}%), "
                    "runaway={} ({:.2f}%) | P1-2 absent={}/{} ({:.1f}%) | late_min={} early_min={}".format(
                        tp,
                        s["absent"],
                        pct(s["absent"], tp),
                        s["late"],
                        pct(s["late"], tp),
                        s["excused"],
                        pct(s["excused"], tp),
                        s["left_early"],
                        pct(s["left_early"], tp),
                        s["runaway"],
                        pct(s["runaway"], tp),
                        p12a,
                        p12t,
                        pct(p12a, p12t),
                        overall["late_minutes"],
                        overall["early_minutes"],
                    )
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"OK. Created {created_records} AttendanceRecord and {created_daily} AttendanceDaily for wing {wing_id} on {dt}."
            )
        )
