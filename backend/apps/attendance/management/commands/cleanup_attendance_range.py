from __future__ import annotations

from datetime import date, timedelta
from typing import Iterable, Optional

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q


def _daterange(a: date, b: date) -> Iterable[date]:
    cur = a
    while cur <= b:
        yield cur
        cur = cur + timedelta(days=1)


def _parse_ui_or_iso_date(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    s = s.strip()
    if not s:
        return None
    try:
        if "/" in s:
            d, m, y = s.split("/")
            if len(y) == 4:
                return date(int(y), int(m), int(d))
    except Exception:
        pass
    try:
        if "-" in s and len(s) >= 10:
            return date.fromisoformat(s[:10])
    except Exception:
        pass
    return None


class Command(BaseCommand):
    help = (
        "Remove attendance data (records, daily summaries, and exit events) within a given date range, "
        "optionally limited to a specific wing. Safer than raw SQL and supports dry-run."
    )

    def add_arguments(self, parser):
        parser.add_argument("--start", type=str, required=True, help="Start date (YYYY-MM-DD or DD/MM/YYYY)")
        parser.add_argument("--end", type=str, required=True, help="End date (YYYY-MM-DD or DD/MM/YYYY)")
        parser.add_argument("--wing", type=int, default=None, help="Limit to a specific wing ID")
        parser.add_argument(
            "--only-demo",
            action="store_true",
            help="Only delete records clearly marked as demo ([demo] in notes).",
        )
        parser.add_argument("--dry-run", action="store_true", help="Do not write, only report counts")
        parser.add_argument("--yes", action="store_true", help="Confirm deletion. Required unless --dry-run is used.")

    def handle(self, *args, **opts):
        from django.core.exceptions import FieldError
        from school.models import AttendanceRecord, AttendanceDaily  # type: ignore
        try:
            from school.models import ExitEvent  # type: ignore
        except Exception:
            ExitEvent = None  # type: ignore

        start = _parse_ui_or_iso_date(opts.get("start"))
        end = _parse_ui_or_iso_date(opts.get("end"))
        wing_id = opts.get("wing")
        dry = bool(opts.get("dry_run"))
        only_demo = bool(opts.get("only_demo"))
        yes = bool(opts.get("yes"))

        if not start or not end:
            raise CommandError("Both --start and --end must be provided and valid.")
        if end < start:
            raise CommandError("--end must be >= --start")

        if not dry and not yes:
            raise CommandError("Refusing to delete without confirmation. Re-run with --yes or use --dry-run.")

        self.stdout.write(self.style.NOTICE(f"Target range: {start} -> {end}"))
        if wing_id:
            self.stdout.write(self.style.NOTICE(f"Wing filter active: wing_id={wing_id}"))
        if only_demo:
            self.stdout.write(self.style.WARNING("Running in demo-only mode (will match [demo] notes only)."))

        def _filter_by_wing(qs):
            if wing_id is None:
                return qs
            # Try common relations in order; if a filter fails, try next
            try:
                return qs.filter(classroom__wing_id=wing_id)
            except FieldError:
                pass
            try:
                return qs.filter(class_fk__wing_id=wing_id)
            except FieldError:
                pass
            try:
                return qs.filter(wing_id=wing_id)
            except FieldError:
                pass
            try:
                return qs.filter(student__class_fk__wing_id=wing_id)
            except FieldError:
                pass
            return qs.none()

        # AttendanceRecord
        ar_qs = AttendanceRecord.objects.filter(date__gte=start, date__lte=end)
        ar_qs = _filter_by_wing(ar_qs)
        if only_demo:
            ar_qs = ar_qs.filter(Q(note__icontains="[demo]") | Q(notes__icontains="[demo]"))
        ar_count = ar_qs.count()

        # AttendanceDaily
        ad_qs = AttendanceDaily.objects.filter(date__gte=start, date__lte=end)
        ad_qs = _filter_by_wing(ad_qs)
        if only_demo:
            ad_qs = ad_qs.filter(
                Q(note__icontains="[demo]") | Q(notes__icontains="[demo]") | Q(source__icontains="demo")
            )
        ad_count = ad_qs.count()

        # ExitEvent (optional)
        ee_count = 0
        ee_qs = None
        if ExitEvent is not None:
            try:
                ee_qs = _filter_by_wing(ExitEvent.objects.filter(date__gte=start, date__lte=end))
            except Exception:
                ee_qs = _filter_by_wing(ExitEvent.objects.filter(started_at__date__gte=start, started_at__date__lte=end))
            if only_demo:
                ee_qs = ee_qs.filter(Q(note__icontains="[demo]") | Q(notes__icontains="[demo]"))
            ee_count = ee_qs.count()

        self.stdout.write(
            self.style.WARNING(
                f"Range cleanup preview — AR: {ar_count}, AD: {ad_count}, EE: {ee_count}"
            )
        )

        if dry:
            self.stdout.write(self.style.NOTICE("Dry-run only. No deletions performed."))
            return

        from django.db import transaction
        from django.db.models.deletion import ProtectedError
        with transaction.atomic():
            try:
                # Delete child records first to satisfy FK constraints (e.g., ExitEvent -> AttendanceRecord)
                if ee_qs is not None and ee_count:
                    ee_qs.delete()
                # Daily summaries are independent; safe to delete anytime
                if ad_count:
                    ad_qs.delete()
                # Finally remove the per-lesson attendance records
                if ar_count:
                    ar_qs.delete()
            except ProtectedError as pe:
                # Provide a clear diagnostic and abort transaction
                self.stderr.write(self.style.ERROR("Deletion blocked by database protection (ProtectedError)."))
                self.stderr.write(self.style.ERROR("Hint: ensure dependent records (e.g., ExitEvent or other FKs) are deleted first."))
                raise
        self.stdout.write(self.style.SUCCESS("Range cleanup done."))