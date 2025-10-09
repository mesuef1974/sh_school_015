from django.core.management import BaseCommand
from django.db import transaction
from datetime import time
from ...models import CalendarTemplate, CalendarSlot, TimetableEntry


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
            ("5", time(10, 25), time(11, 10), "class"),
            ("6", time(11, 10), time(11, 50), "class"),
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
            ("4", time(9, 55), time(10, 50), "class"),
            ("5", time(10, 50), time(11, 40), "class"),
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

        # Helper: safely clear a template's slots by first removing TimetableEntry refs
        def clear_template_slots(template: CalendarTemplate):
            # Delete timetable entries that reference this template's slots, then delete slots
            TimetableEntry.objects.filter(slot__template=template).delete()
            template.slots.all().delete()

        with transaction.atomic():
            for name, scope, days, slots in TEMPLATES:
                tmpl, created = CalendarTemplate.objects.get_or_create(
                    name=name, defaults={"scope": scope, "days": days}
                )
                if created:
                    created_templates += 1
                # Clear existing slots for idempotency (and remove referencing timetable entries safely)
                clear_template_slots(tmpl)
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

            # Build/refresh unified official templates based on floor distribution
            try:
                # Source templates for Sun-Wed (Upper/Ground) and Thu (Secondary/Ground)
                sw_ground = CalendarTemplate.objects.filter(name="Sun-Wed Ground").first()
                sw_upper = CalendarTemplate.objects.filter(name="Sun-Wed Upper").first()
                thu_ground = CalendarTemplate.objects.filter(name="Thu Ground").first()
                thu_secondary = CalendarTemplate.objects.filter(name="Thu Secondary").first()

                # Helper to clone slots from src Sun..Wed + Thu into target template
                def compose_official(
                    target_name: str,
                    sw_src: CalendarTemplate,
                    thu_src: CalendarTemplate,
                ):
                    nonlocal created_templates, created_slots
                    target, was_created = CalendarTemplate.objects.get_or_create(
                        name=target_name,
                        defaults={"scope": "School", "days": "Sun-Thu"},
                    )
                    if was_created:
                        created_templates += 1
                    # Safely clear slots and any existing timetable entries for this target
                    clear_template_slots(target)
                    order = 1
                    for day in ["Sun", "Mon", "Tue", "Wed"]:
                        for s in sw_src.slots.order_by("order"):
                            CalendarSlot.objects.create(
                                template=target,
                                day=day,
                                period_index=str(s.period_index),
                                start_time=s.start_time,
                                end_time=s.end_time,
                                block=s.block,
                                order=order,
                            )
                            created_slots += 1
                            order += 1
                    for s in thu_src.slots.order_by("order"):
                        CalendarSlot.objects.create(
                            template=target,
                            day="Thu",
                            period_index=str(s.period_index),
                            start_time=s.start_time,
                            end_time=s.end_time,
                            block=s.block,
                            order=order,
                        )
                        created_slots += 1
                        order += 1

                # Maintain legacy single official template for compatibility (Ground-based)
                if (sw_ground or sw_upper) and (thu_ground or thu_secondary):
                    # pick ground first for legacy 'الجدول الرسمي'
                    sw_src = sw_ground or sw_upper
                    thu_src = (
                        thu_ground
                        or thu_secondary
                        or CalendarTemplate.objects.filter(name__startswith="Thu").first()
                    )
                    if sw_src and thu_src:
                        compose_official("الجدول الرسمي", sw_src, thu_src)

                # New: Official per-floor templates
                if sw_ground and thu_ground:
                    compose_official("الجدول الرسمي - الأرضي", sw_ground, thu_ground)
                if sw_upper and thu_secondary:
                    compose_official("الجدول الرسمي - العلوي", sw_upper, thu_secondary)

            except Exception:
                # Do not fail seeding if official template composition fails
                pass
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded templates={created_templates}, slots={created_slots} (idempotent)"
            )
        )
