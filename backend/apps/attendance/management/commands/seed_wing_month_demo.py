from __future__ import annotations

from datetime import date as _date, timedelta
from typing import Optional

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


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


def sunday_of_week(dt: _date) -> _date:
    # Python weekday: Mon=0..Sun=6 → back to Sunday
    days_back_to_sun = (dt.weekday() - 6) % 7
    return dt - timedelta(days=days_back_to_sun)


def thursday_of_same_week(sunday: _date) -> _date:
    return sunday + timedelta(days=4)


class Command(BaseCommand):
    help = (
        "Seed realistic FAKE attendance for a wing across a month-like span (default 4 working weeks).\n"
        "Accepts a starting date, expands to Sun→Thu weeks, and delegates to seed_wing_week_demo with a single range.\n"
        "Use this as a convenience wrapper for monthly demos."
    )

    def add_arguments(self, parser):
        parser.add_argument("--wing", type=int, default=5, help="Wing ID to seed (default: 5)")
        parser.add_argument(
            "--start",
            type=str,
            required=True,
            help="Any date inside the first target week (YYYY-MM-DD or DD/MM/YYYY). Example: 2025-09-14",
        )
        parser.add_argument(
            "--weeks",
            type=int,
            default=4,
            help="Number of weeks to include (Sun→Thu). Default: 4",
        )
        parser.add_argument("--seed", type=int, default=42, help="Random seed base for reproducibility")
        parser.add_argument("--dry-run", action="store_true", help="Do not write to DB, only print summaries")
        parser.add_argument(
            "--p12-absent",
            dest="p12_absent",
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
            help="Also issue AbsenceAlert (archived) for each week",
        )
        parser.add_argument("--with-behavior", action="store_true", help="Also seed behavior incidents if supported")

    def handle(self, *args, **opts):
        wing_id: int = int(opts["wing"])
        start_str: str = str(opts["start"]) if opts.get("start") else ""
        start_dt = parse_ui_or_iso_date(start_str)
        if not start_dt:
            raise CommandError("Invalid --start. Use YYYY-MM-DD or DD/MM/YYYY, e.g., 2025-09-14")
        weeks: int = max(1, int(opts.get("weeks") or 4))

        # Compute overall range covering the requested number of Sun→Thu weeks starting from the week that contains start_dt
        first_sun = sunday_of_week(start_dt)
        # End on the Thursday of the (weeks)-th week
        end_dt = thursday_of_same_week(first_sun + timedelta(days=7 * (weeks - 1)))
        start_iso = first_sun.isoformat()
        end_iso = end_dt.isoformat()

        self.stdout.write(self.style.NOTICE(f"Monthly span (Sun->Thu weeks): {start_iso} -> {end_iso} (weeks={weeks})"))

        # Delegate to week-range seeder (it supports arbitrary ranges already)
        kwargs = {
            "wing": wing_id,
            "start": start_iso,
            "end": end_iso,
            "seed": int(opts.get("seed") or 42),
            "dry_run": bool(opts.get("dry_run")),
            "p12_absent": opts.get("p12_absent"),
            "finalize": bool(opts.get("finalize")),
            "approve": bool(opts.get("approve")),
            "summary": bool(opts.get("summary")),
            "workflow": opts.get("workflow") or "all",
            "with_exits": bool(opts.get("with_exits")),
            "with_alerts": bool(opts.get("with_alerts")),
            "with_behavior": bool(opts.get("with_behavior")),
        }
        # Defaults: if no extras specified, enable exits+alerts just like week seeder behavior
        if not any((kwargs["with_exits"], kwargs["with_alerts"], kwargs["with_behavior"])):
            kwargs["with_exits"] = True
            kwargs["with_alerts"] = True

        call_command("seed_wing_week_demo", **kwargs)

        self.stdout.write(self.style.SUCCESS("Monthly seeding completed."))
