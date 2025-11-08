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


def _weekend_py(d: date) -> bool:
    # Python weekday(): Mon=0..Sun=6 → Fri=4, Sat=5
    return d.weekday() in (4, 5)


class Command(BaseCommand):
    help = (
        "Remove attendance-related data recorded on weekends (Fri/Sat). "
        "Can be constrained by date range and wing. Defaults to ALL dates if no range is provided."
    )

    def add_arguments(self, parser):
        parser.add_argument("--start", type=str, default=None, help="Start date (YYYY-MM-DD or DD/MM/YYYY)")
        parser.add_argument("--end", type=str, default=None, help="End date (YYYY-MM-DD or DD/MM/YYYY)")
        parser.add_argument("--wing", type=int, default=None, help="Limit to a specific wing ID")
        parser.add_argument(
            "--all-weekends",
            action="store_true",
            help="Acknowledge that non-demo data may be deleted if they fall on Fri/Sat",
        )
        parser.add_argument("--dry-run", action="store_true", help="Do not write, only report counts")
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Confirm deletion. Required unless --dry-run is used.",
        )

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
        dangerous = bool(opts.get("all_weekends"))
        yes = bool(opts.get("yes"))

        # Determine target weekend dates set (or None to mean "all weekends in DB range")
        dates: Optional[set[date]] = None
        if start or end:
            if not start or not end:
                raise CommandError("Both --start and --end must be provided together")
            if start > end:
                raise CommandError("--start must be <= --end")
            dates = {d for d in _daterange(start, end) if _weekend_py(d)}

        if not dry and not yes:
            raise CommandError("Refusing to delete without confirmation. Re-run with --yes or use --dry-run.")

        # Diagnostics: explain effective scope and safety mode
        if dates is None and not dangerous:
            self.stdout.write(
                self.style.WARNING(
                    "No --start/--end provided and --all-weekends not set → will only target records tagged [demo] on Fri/Sat.\n"
                    "Tip: provide --start and --end to clean a specific range, or pass --all-weekends to include non-demo data that fall on Fri/Sat."
                )
            )
        if dates is not None:
            self.stdout.write(
                self.style.NOTICE(
                    f"Targeting weekends within range: {min(dates) if dates else ''} → {max(dates) if dates else ''}"
                )
            )
        if wing_id:
            self.stdout.write(self.style.NOTICE(f"Wing filter active: wing_id={wing_id}"))

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

        # Build Q for dates on weekends
        def _q_for_dates(model, field_candidates: list[str]):
            q = Q()
            if dates is None:
                # Without explicit range, rely on weekday function in DB is cumbersome; use broad filter
                # Approach: no date filter here; we'll filter in Python after fetching ids by chunks
                return None
            # When we have an explicit set of dates, build OR expressions
            for f in field_candidates:
                # Using __in on DateField
                q |= Q(**{f"{f}__in": list(dates)})
            return q

        # Collect counts (best-effort)
        total_counts: dict[str, int] = {"AttendanceRecord": 0, "AttendanceDaily": 0, "ExitEvent": 0}

        # AttendanceRecord
        ar_qs = AttendanceRecord.objects.all()
        ar_qs = _filter_by_wing(ar_qs)
        q = _q_for_dates(AttendanceRecord, ["date"])
        if q is not None:
            ar_qs = ar_qs.filter(q)
        # If no explicit range, we cautiously avoid deleting non-demo without --all-weekends
        if dates is None and not dangerous:
            ar_qs = ar_qs.filter(Q(note__icontains="[demo]") | Q(notes__icontains="[demo]"))
        # Additional safety: exclude weekdays just in case a broad filter was used
        # Evaluate ids and post-filter by Python weekday
        ar_ids = list(ar_qs.values_list("id", "date"))
        ar_ids = [i for i in ar_ids if isinstance(i[1], date) and _weekend_py(i[1])]
        total_counts["AttendanceRecord"] = len(ar_ids)

        # AttendanceDaily
        ad_qs = AttendanceDaily.objects.all()
        ad_qs = _filter_by_wing(ad_qs)
        q = _q_for_dates(AttendanceDaily, ["date"])
        if q is not None:
            ad_qs = ad_qs.filter(q)
        if dates is None and not dangerous:
            ad_qs = ad_qs.filter(
                Q(note__icontains="[demo]") | Q(notes__icontains="[demo]") | Q(source__icontains="demo")
            )
        ad_ids = list(ad_qs.values_list("id", "date"))
        ad_ids = [i for i in ad_ids if isinstance(i[1], date) and _weekend_py(i[1])]
        total_counts["AttendanceDaily"] = len(ad_ids)

        # ExitEvent (optional model)
        ee_ids: list[int] = []
        if ExitEvent is not None:
            ee_qs = ExitEvent.objects.all()
            ee_qs = _filter_by_wing(ee_qs)
            # Try common date fields
            # Prefer a plain DateField named 'date'; otherwise use started_at__date
            try:
                q = _q_for_dates(ExitEvent, ["date"])
                if q is not None:
                    ee_qs = ee_qs.filter(q)
                ee_pairs = list(ee_qs.values_list("id", "date"))
                ee_ids = [i for i in ee_pairs if isinstance(i[1], date) and _weekend_py(i[1])]
            except Exception:
                # Fallback via started_at__date
                if dates is not None:
                    ee_qs = ee_qs.filter(started_at__date__in=list(dates))
                if dates is None and not dangerous:
                    ee_qs = ee_qs.filter(Q(note__icontains="[demo]") | Q(notes__icontains="[demo]"))
                pairs = list(ee_qs.values_list("id", "started_at"))
                ee_ids = [p for p in pairs if getattr(p[1], "date", None) and _weekend_py(p[1].date())]
            total_counts["ExitEvent"] = len(ee_ids)

        # Report
        self.stdout.write(
            self.style.WARNING(
                f"Weekend cleanup preview — AR: {total_counts['AttendanceRecord']}, AD: {total_counts['AttendanceDaily']}, EE: {total_counts['ExitEvent']}"
            )
        )

        if dry:
            self.stdout.write(self.style.NOTICE("Dry-run only. No deletions performed."))
            return

        # Apply deletions
        from django.db import transaction

        with transaction.atomic():
            if ar_ids:
                AttendanceRecord.objects.filter(id__in=[i[0] for i in ar_ids]).delete()
            if ad_ids:
                AttendanceDaily.objects.filter(id__in=[i[0] for i in ad_ids]).delete()
            if ExitEvent is not None and ee_ids:
                ExitEvent.objects.filter(id__in=[i[0] for i in ee_ids]).delete()
        self.stdout.write(self.style.SUCCESS("Weekend cleanup done."))
