from __future__ import annotations


from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q


class Command(BaseCommand):
    help = (
        "Permanently delete attendance data (AttendanceRecord, AttendanceDaily, and ExitEvent) in bulk.\n"
        "This is a destructive purge intended for large cleanups (e.g., > 23k records).\n"
        "Safety features: dry-run preview, explicit --yes confirmation, optional wing filter, optional demo-only mode,\n"
        "and batch deletion to avoid long transactions. Order of deletion respects dependencies: ExitEvent → AttendanceDaily → AttendanceRecord."
    )

    def add_arguments(self, parser):
        parser.add_argument("--wing", type=int, default=None, help="Limit to a specific wing ID")
        parser.add_argument(
            "--only-demo",
            action="store_true",
            help="Only purge records clearly marked as demo ([demo] in notes/source).",
        )
        parser.add_argument("--batch", type=int, default=2000, help="Batch size for deletions (default: 2000)")
        parser.add_argument("--dry-run", action="store_true", help="Preview counts only; do not delete")
        parser.add_argument("--yes", action="store_true", help="Confirm actual deletion (required unless --dry-run)")

    def handle(self, *args, **opts):
        from django.core.exceptions import FieldError
        from django.db import transaction
        from school.models import AttendanceRecord, AttendanceDaily  # type: ignore

        try:
            from school.models import ExitEvent  # type: ignore
        except Exception:
            ExitEvent = None  # type: ignore

        wing_id = opts.get("wing")
        only_demo = bool(opts.get("only_demo"))
        dry = bool(opts.get("dry_run"))
        yes = bool(opts.get("yes"))
        batch_size = max(100, int(opts.get("batch") or 2000))

        if not dry and not yes:
            raise CommandError("Refusing to delete without confirmation. Re-run with --yes or use --dry-run.")

        if wing_id:
            self.stdout.write(self.style.NOTICE(f"Wing filter active: wing_id={wing_id}"))
        if only_demo:
            self.stdout.write(self.style.WARNING("Running in demo-only mode (will match [demo] notes/source only)."))

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

        def _demo_q_for(model_cls):
            q = Q()
            # Tolerant match on common note fields
            for fname in ("note", "notes", "remark", "remarks"):
                try:
                    model_cls._meta.get_field(fname)  # type: ignore[attr-defined]
                    q |= Q(**{f"{fname}__icontains": "[demo]"})
                except Exception:
                    pass
            try:
                model_cls._meta.get_field("source")  # type: ignore[attr-defined]
                q |= Q(source__icontains="demo")
            except Exception:
                pass
            return q if q else Q(pk__in=[])

        # Build querysets
        ar_qs = _filter_by_wing(AttendanceRecord.objects.all())
        ad_qs = _filter_by_wing(AttendanceDaily.objects.all())
        ee_qs = _filter_by_wing(ExitEvent.objects.all()) if ExitEvent is not None else None
        if only_demo:
            ar_qs = ar_qs.filter(_demo_q_for(AttendanceRecord))
            ad_qs = ad_qs.filter(_demo_q_for(AttendanceDaily))
            if ee_qs is not None:
                ee_qs = ee_qs.filter(_demo_q_for(ExitEvent))  # type: ignore[arg-type]

        # Count first for preview
        ar_count = ar_qs.count()
        ad_count = ad_qs.count()
        ee_count = ee_qs.count() if ee_qs is not None else 0
        self.stdout.write(
            self.style.WARNING(
                f"Purge preview — AttendanceRecord: {ar_count}, AttendanceDaily: {ad_count}, ExitEvent: {ee_count}"
            )
        )
        if dry:
            self.stdout.write(self.style.NOTICE("Dry-run only. No deletions performed."))
            return

        # Helper: delete in batches by primary keys to avoid long locks
        def _batched_delete(qs, label: str):
            total = qs.count()
            if total == 0:
                return 0
            deleted = 0
            # Iterate pks in ascending order to keep batches stable
            pks = list(qs.values_list("pk", flat=True).order_by("pk"))
            for i in range(0, len(pks), batch_size):
                chunk = pks[i : i + batch_size]
                with transaction.atomic():
                    qs.model.objects.filter(pk__in=chunk).delete()
                deleted += len(chunk)
                self.stdout.write(self.style.NOTICE(f"Deleted {deleted}/{total} from {label} ..."))
            return deleted

        # Deletion order: ExitEvent → AttendanceDaily → AttendanceRecord
        total_deleted = {"ExitEvent": 0, "AttendanceDaily": 0, "AttendanceRecord": 0}
        if ee_qs is not None and ee_count:
            total_deleted["ExitEvent"] = _batched_delete(ee_qs, "ExitEvent")
        if ad_count:
            total_deleted["AttendanceDaily"] = _batched_delete(ad_qs, "AttendanceDaily")
        if ar_count:
            total_deleted["AttendanceRecord"] = _batched_delete(ar_qs, "AttendanceRecord")

        self.stdout.write(
            self.style.SUCCESS(
                "Purge completed — "
                f"AR: {total_deleted['AttendanceRecord']}, "
                f"AD: {total_deleted['AttendanceDaily']}, "
                f"EE: {total_deleted['ExitEvent']}"
            )
        )
