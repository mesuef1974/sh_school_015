from __future__ import annotations

from datetime import date
from typing import Optional

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q


class Command(BaseCommand):
    help = (
        "Remove ALL demo-tagged attendance data ([demo]) safely, optionally limited by wing and/or date range.\n"
        "Deletes in dependency-safe order: ExitEvent → AttendanceDaily → AttendanceRecord.\n"
        "Supports dry-run and requires --yes for actual deletion."
    )

    def add_arguments(self, parser):
        parser.add_argument("--wing", type=int, default=None, help="Limit to a specific wing ID")
        parser.add_argument("--start", type=str, default=None, help="Optional start date (YYYY-MM-DD or DD/MM/YYYY)")
        parser.add_argument("--end", type=str, default=None, help="Optional end date (YYYY-MM-DD or DD/MM/YYYY)")
        parser.add_argument("--dry-run", action="store_true", help="Do not write, only report counts")
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Confirm deletion. Required unless --dry-run is used.",
        )

    @staticmethod
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

    def handle(self, *args, **opts):
        from django.core.exceptions import FieldError
        from school.models import AttendanceRecord, AttendanceDaily  # type: ignore

        try:
            from school.models import ExitEvent  # type: ignore
        except Exception:
            ExitEvent = None  # type: ignore

        wing_id = opts.get("wing")
        start = self._parse_ui_or_iso_date(opts.get("start"))
        end = self._parse_ui_or_iso_date(opts.get("end"))
        dry = bool(opts.get("dry_run"))
        yes = bool(opts.get("yes"))

        if (start and not end) or (end and not start):
            raise CommandError("When specifying a range, both --start and --end must be provided.")
        if start and end and end < start:
            raise CommandError("--end must be >= --start")
        if not dry and not yes:
            raise CommandError("Refusing to delete without confirmation. Re-run with --yes or use --dry-run.")

        if wing_id:
            self.stdout.write(self.style.NOTICE(f"Wing filter active: wing_id={wing_id}"))
        if start and end:
            self.stdout.write(self.style.NOTICE(f"Date range: {start} → {end}"))
        else:
            self.stdout.write(self.style.NOTICE("No date range provided: will target ALL dates (demo-tagged only)."))

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

        def _filter_by_range(qs, field_names: list[str]):
            if not (start and end):
                return qs
            q = Q()
            for f in field_names:
                q |= Q(**{f"{f}__gte": start, f"{f}__lte": end})
            return qs.filter(q)

        # Helper: build a tolerant Q for demo-tagged notes/fields on any model
        def _demo_q_for(model_cls):
            q = Q()
            # common note fields
            for fname in ("note", "notes", "remark", "remarks"):
                try:
                    # Test if field exists by building a harmless filter (won't be evaluated yet)
                    model_cls._meta.get_field(fname)  # type: ignore[attr-defined]
                    q |= Q(**{f"{fname}__icontains": "[demo]"})
                except Exception:
                    # ignore missing fields
                    pass
            # sometimes a 'source' field contains 'demo'
            try:
                model_cls._meta.get_field("source")  # type: ignore[attr-defined]
                q |= Q(source__icontains="demo")
            except Exception:
                pass
            return q if q else Q(pk__in=[])  # if nothing matched, return empty condition

        # AttendanceRecord (period-level)
        ar_qs = AttendanceRecord.objects.all()
        ar_qs = _filter_by_wing(ar_qs)
        ar_qs = ar_qs.filter(_demo_q_for(AttendanceRecord))
        ar_qs = _filter_by_range(ar_qs, ["date"])  # optional
        ar_count = ar_qs.count()

        # AttendanceDaily
        ad_qs = AttendanceDaily.objects.all()
        ad_qs = _filter_by_wing(ad_qs)
        ad_qs = ad_qs.filter(_demo_q_for(AttendanceDaily))
        ad_qs = _filter_by_range(ad_qs, ["date"])  # optional
        ad_count = ad_qs.count()

        # ExitEvent (optional model)
        ee_qs = None
        ee_count = 0
        if ExitEvent is not None:
            ee_qs = ExitEvent.objects.all()
            ee_qs = _filter_by_wing(ee_qs)
            ee_qs = ee_qs.filter(_demo_q_for(ExitEvent))
            # Try common date fields; only apply if a range was provided
            if start and end:
                try:
                    ee_qs = _filter_by_range(ee_qs, ["date"])  # type: ignore[arg-type]
                except Exception:
                    ee_qs = _filter_by_range(ee_qs, ["started_at__date"])  # type: ignore[arg-type]
            ee_count = ee_qs.count()

        self.stdout.write(self.style.WARNING(f"Demo cleanup preview — AR: {ar_count}, AD: {ad_count}, EE: {ee_count}"))

        if dry:
            self.stdout.write(self.style.NOTICE("Dry-run only. No deletions performed."))
            return

        from django.db import transaction

        with transaction.atomic():
            # Delete children first
            if ee_qs is not None and ee_count:
                ee_qs.delete()
            if ad_count:
                ad_qs.delete()
            if ar_count:
                ar_qs.delete()
        self.stdout.write(self.style.SUCCESS("Demo cleanup completed."))
