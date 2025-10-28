from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from school.models import Term
from school.services.timetable_builder import TimetableBuilder


class Command(BaseCommand):
    help = "Generate official weekly timetables for the current term and persist them."

    def handle(self, *args, **options):
        term = Term.objects.filter(is_current=True).first()
        if not term:
            raise CommandError("No current term found. Please set a current Term.")

        builder = TimetableBuilder(term)
        entries = builder.build_entries()
        result = builder.persist(entries)

        self.stdout.write(
            self.style.SUCCESS(f"Generated {result.created} timetable entries (replaced {result.replaced_existing}).")
        )
