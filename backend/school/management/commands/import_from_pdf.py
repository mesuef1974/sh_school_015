from __future__ import annotations

"""
[REMOVED] This management command was permanently removed as part of the safe cleanup.
It remains as a minimal stub to avoid import errors during Django command discovery.
"""
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        "[REMOVED] Timetable import from PDF is no longer available. "
        "All timetable/calendar features and models were removed."
    )

    def handle(self, *args, **options):
        raise CommandError("This command has been removed. Timetable/calendar features are no longer available.")
