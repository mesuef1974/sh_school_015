from django.core.management.base import BaseCommand
from django.db import transaction
from datetime import time

from ...models import CalendarTemplate, CalendarSlot


DEFAULT_NAME = "Default (Sun-Thu)"
DEFAULT_DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu"]

# A simple, reasonable default day structure (7 periods with two breaks)
# You can adjust later from Admin.
DEFAULT_PERIODS = [
    ("1", time(7, 0), time(7, 45), CalendarSlot.Block.CLASS, 1),
    ("2", time(7, 50), time(8, 35), CalendarSlot.Block.CLASS, 2),
    ("BREAK", time(8, 35), time(8, 50), CalendarSlot.Block.BREAK, 3),
    ("3", time(8, 50), time(9, 35), CalendarSlot.Block.CLASS, 4),
    ("4", time(9, 40), time(10, 25), CalendarSlot.Block.CLASS, 5),
    ("PRAYER", time(10, 25), time(10, 45), CalendarSlot.Block.PRAYER, 6),
    ("5", time(10, 50), time(11, 35), CalendarSlot.Block.CLASS, 7),
    ("6", time(11, 40), time(12, 25), CalendarSlot.Block.CLASS, 8),
    ("7", time(12, 30), time(13, 15), CalendarSlot.Block.CLASS, 9),
]


class Command(BaseCommand):
    help = (
        "Bootstrap a default CalendarTemplate and its slots (Sun–Thu). "
        "Idempotent and safe to re-run with --overwrite."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--name",
            default=DEFAULT_NAME,
            help=f"Template name to create/use (default: '{DEFAULT_NAME}')",
        )
        parser.add_argument(
            "--scope",
            default="ALL",
            help="Scope tag for the template (e.g., Upper, Ground, Secondary, etc.)",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="If provided, existing slots for the named template will be replaced",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        name = options["--name"] if "--name" in options else options["name"]
        scope = options["--scope"] if "--scope" in options else options["scope"]
        overwrite = options.get("overwrite", False)

        tmpl, created = CalendarTemplate.objects.get_or_create(
            name=name,
            defaults={
                "scope": scope,
                "days": ",".join(DEFAULT_DAYS),
            },
        )

        if not created:
            # Update meta if changed
            changed = False
            if tmpl.scope != scope:
                tmpl.scope = scope
                changed = True
            days_str = ",".join(DEFAULT_DAYS)
            if tmpl.days != days_str:
                tmpl.days = days_str
                changed = True
            if changed:
                tmpl.save(update_fields=["scope", "days"])

        if overwrite:
            deleted, _ = CalendarSlot.objects.filter(template=tmpl).delete()
            msg = ("Removed {n} existing slots for template '{name}'.").format(
                n=deleted, name=tmpl.name
            )
            self.stdout.write(self.style.WARNING(msg))

        # Create slots only if none exist (or after overwrite)
        if not tmpl.slots.exists():
            bulk = []
            for day in DEFAULT_DAYS:
                for period_index, start, end, block, order in DEFAULT_PERIODS:
                    bulk.append(
                        CalendarSlot(
                            template=tmpl,
                            day=day,
                            period_index=str(period_index),
                            start_time=start,
                            end_time=end,
                            block=block,
                            order=order,
                        )
                    )
            CalendarSlot.objects.bulk_create(bulk)
            msg = ("Created template '{name}' with {slots} slots across {days} days.").format(
                name=tmpl.name, slots=len(bulk), days=len(DEFAULT_DAYS)
            )
            self.stdout.write(self.style.SUCCESS(msg))
        else:
            count = tmpl.slots.count()
            note = (
                "Template '{name}' already has {count} slots. Use --overwrite to regenerate."
            ).format(name=tmpl.name, count=count)
            self.stdout.write(self.style.NOTICE(note))

        self.stdout.write(self.style.SUCCESS("Bootstrap complete."))
