from __future__ import annotations

from typing import List

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from ...models import CalendarSlot, CalendarTemplate, TimetableEntry

SEED_SOURCE_TEMPLATE_NAMES: List[str] = [
    "Sun-Wed Upper",
    "Sun-Wed Ground",
    "Thu Secondary",
    "Thu Grade9(2-4)",
    "Thu Ground",
]

OFFICIAL_TEMPLATE_NAMES: List[str] = [
    "الجدول الرسمي",
    "الجدول الرسمي - الأرضي",
    "الجدول الرسمي - العلوي",
]


class Command(BaseCommand):
    help = (
        "Deep-clean CalendarSlot/CalendarTemplate according to the official day distribution, "
        "then rebuild them from scratch by invoking seed_periods. This will also purge TimetableEntry to "
        "release foreign-key protections."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes-i-know",
            dest="confirm",
            action="store_true",
            help=(
                "CONFIRM destructive operation. Deletes ALL TimetableEntry and ALL CalendarSlot, and removes "
                "known seeded CalendarTemplate records before reseeding."
            ),
        )
        parser.add_argument(
            "--keep-templates",
            action="store_true",
            help=(
                "If provided, will NOT delete CalendarTemplate rows; only slots & entries are purged, then reseeded."
            ),
        )

    def handle(self, *args, **options):
        if not options.get("confirm"):
            raise CommandError(
                "This is a destructive operation. Re-run with --yes-i-know to proceed. "
                "It will delete ALL TimetableEntry and ALL CalendarSlot, then rebuild standard templates via seed_periods."
            )

        keep_templates: bool = options.get("keep_templates", False)

        with transaction.atomic():
            # 1) Delete all timetable entries (releases PROTECT on CalendarSlot)
            deleted_entries = TimetableEntry.objects.all().delete()[0]

            # 2) Delete all calendar slots
            deleted_slots = CalendarSlot.objects.all().delete()[0]

            deleted_templates = 0
            if not keep_templates:
                # 3) Delete known seed/official templates to avoid stale or duplicated definitions
                names = set(SEED_SOURCE_TEMPLATE_NAMES + OFFICIAL_TEMPLATE_NAMES)
                templates_qs = CalendarTemplate.objects.filter(name__in=list(names))
                deleted_templates = templates_qs.delete()[0]

        # 4) Re-seed standard periods and compose official templates
        call_command("seed_periods")

        self.stdout.write(self.style.SUCCESS("Deep clean completed."))
        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted: entries={deleted_entries}, slots={deleted_slots}, templates={deleted_templates}. Reseeded successfully."
            )
        )
