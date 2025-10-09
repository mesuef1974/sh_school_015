from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        "[REMOVED] Timetable generation is no longer supported. "
        "All timetable/calendar features and related database models were removed."
    )

    def handle(self, *args, **options):
        raise CommandError(
            "This command has been removed. Timetable and calendar features are no longer available."
        )
