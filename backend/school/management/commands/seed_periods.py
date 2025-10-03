from django.core.management import BaseCommand
from django.db import transaction
from datetime import time
from ...models import CalendarTemplate, CalendarSlot


TEMPLATES = [
    (
        "Sun-Wed Upper",
        "Upper",
        "ALL",
        [
            ("1", time(7, 10), time(8, 0), "class"),
            ("2", time(8, 0), time(8, 45), "class"),
            ("3", time(8, 45), time(9, 35), "class"),
            ("4", time(9, 35), time(10, 25), "class"),
            ("BREAK", time(10, 25), time(10, 45), "break"),
            ("5", time(10, 45), time(11, 35), "class"),
            ("6", time(11, 35), time(12, 25), "class"),
            ("7", time(12, 25), time(13, 10), "class"),
            ("PRAYER", time(13, 10), time(13, 30), "prayer"),
        ],
    ),
    (
        "Sun-Wed Ground",
        "Ground",
        "ALL",
        [
            ("1", time(7, 10), time(8, 0), "class"),
            ("2", time(8, 0), time(8, 50), "class"),
            ("3", time(8, 50), time(9, 35), "class"),
            ("BREAK", time(9, 35), time(9, 55), "break"),
            ("4", time(9, 55), time(10, 50), "class"),
            ("5", time(10, 50), time(11, 35), "class"),
            ("6", time(11, 35), time(12, 20), "class"),
            ("PRAYER", time(12, 20), time(12, 40), "prayer"),
            ("7", time(12, 40), time(13, 30), "class"),
        ],
    ),
    (
        "Thu Secondary",
        "Secondary",
        "Thu",
        [
            ("1", time(7, 10), time(7, 55), "class"),
            ("2", time(7, 55), time(8, 40), "class"),
            ("3", time(8, 40), time(9, 20), "class"),
            ("4", time(9, 20), time(10, 5), "class"),
            ("BREAK", time(10, 5), time(10, 25), "break"),
            ("5", time(10, 25), time(11, 5), "class"),
            ("6", time(11, 5), time(11, 50), "class"),
            ("7", time(11, 50), time(12, 30), "class"),
            ("PRAYER", time(12, 30), time(12, 45), "prayer"),
        ],
    ),
    (
        "Thu Grade9(2-4)",
        "Grade9(2-4)",
        "Thu",
        [
            ("1", time(7, 10), time(8, 0), "class"),
            ("2", time(8, 0), time(8, 50), "class"),
            ("3", time(8, 50), time(9, 35), "class"),
            ("BREAK", time(9, 35), time(9, 55), "break"),
            ("4", time(10, 0), time(10, 50), "class"),
            ("5", time(10, 50), time(11, 10), "class"),
            ("OTHER", time(11, 10), time(11, 40), "other"),
            ("6", time(11, 40), time(12, 30), "class"),
            ("PRAYER", time(12, 30), time(12, 40), "prayer"),
        ],
    ),
    (
        "Thu Ground",
        "Ground",
        "Thu",
        [
            ("1", time(7, 10), time(8, 0), "class"),
            ("2", time(8, 0), time(8, 50), "class"),
            ("3", time(8, 50), time(9, 35), "class"),
            ("BREAK", time(9, 35), time(9, 55), "break"),
            ("4", time(9, 55), time(10, 50), "class"),
            ("5", time(10, 50), time(11, 35), "class"),
            ("PRAYER", time(11, 35), time(11, 55), "prayer"),
            ("6", time(11, 55), time(12, 40), "class"),
        ],
    ),
]


class Command(BaseCommand):
    help = "Seed CalendarTemplate and CalendarSlot from predefined schedule blocks"

    def handle(self, *args, **options):
        created_templates = 0
        created_slots = 0
        with transaction.atomic():
            for name, scope, days, slots in TEMPLATES:
                tmpl, created = CalendarTemplate.objects.get_or_create(
                    name=name, defaults={"scope": scope, "days": days}
                )
                if created:
                    created_templates += 1
                # Clear existing slots for idempotency
                tmpl.slots.all().delete()
                order = 1
                for period_index, start_t, end_t, block in slots:
                    CalendarSlot.objects.create(
                        template=tmpl,
                        day=days,
                        period_index=str(period_index),
                        start_time=start_t,
                        end_time=end_t,
                        block=block,
                        order=order,
                    )
                    created_slots += 1
                    order += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded templates={created_templates}, slots={created_slots} (idempotent)"
            )
        )
