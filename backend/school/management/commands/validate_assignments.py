from django.core.management.base import BaseCommand
from django.db.models import Sum
from school.models import Class, CalendarTemplate, CalendarSlot, TeachingAssignment


class Command(BaseCommand):
    help = (
        "Validate that each class's weekly assigned lessons match the weekly capacity "
        "(days x class periods) inferred from the first CalendarTemplate."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=None,
            help="Override days per week (fallback if no template configured).",
        )
        parser.add_argument(
            "--periods",
            type=int,
            default=None,
            help="Override class periods per day (fallback if cannot infer from template).",
        )
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Exit with non-zero if any class is under or over capacity (default).",
        )

    def handle(self, *args, **options):
        days_override = options.get("days")
        periods_override = options.get("periods")

        # Infer days and periods per day
        tmpl = CalendarTemplate.objects.order_by("name").first()
        if days_override is not None:
            n_days = int(days_override)
        else:
            if tmpl and (tmpl.days or "").strip():
                n_days = len([d for d in tmpl.days.split(",") if d.strip()])
            else:
                n_days = 5  # default Sun-Thu
        if periods_override is not None:
            per_day = int(periods_override)
        else:
            if tmpl:
                # count CLASS blocks for first listed day; fallback to total slots that day
                first_day = (tmpl.days or "Sun,Mon,Tue,Wed,Thu").split(",")[0].strip()
                per_day = (
                    tmpl.slots.filter(
                        day=first_day, block=CalendarSlot.Block.CLASS
                    ).count()
                    or tmpl.slots.filter(day=first_day).count()
                )
            else:
                per_day = 7

        capacity = int(n_days) * int(per_day)

        total_classes = Class.objects.count()
        ready = 0
        under = 0
        over = 0

        self.stdout.write(
            self.style.NOTICE(
                f"Using weekly capacity per class = {capacity} ({n_days} days x {per_day} periods)"
            )
        )
        self.stdout.write("")
        self.stdout.write("Class readiness summary:")
        self.stdout.write("id,name,assigned,capacity,status")

        for c in Class.objects.all().order_by("name"):
            assigned = (
                TeachingAssignment.objects.filter(classroom=c).aggregate(
                    total=Sum("no_classes_weekly")
                )["total"]
                or 0
            )
            if assigned == capacity:
                status = "OK"
                ready += 1
            elif assigned < capacity:
                status = "UNDER"
                under += 1
            else:
                status = "OVER"
                over += 1
            self.stdout.write(
                f"{c.id},{getattr(c, 'name', str(c))},{int(assigned)},{capacity},{status}"
            )

        self.stdout.write("")
        pct = int(round((ready / total_classes) * 100)) if total_classes else 0
        self.stdout.write(
            self.style.SUCCESS(f"Ready: {ready}/{total_classes} ({pct}%)")
        )
        if under:
            self.stdout.write(self.style.WARNING(f"Under capacity: {under}"))
        if over:
            self.stdout.write(self.style.ERROR(f"Over capacity: {over}"))

        # Exit code non-zero if any mismatch
        return 0 if (under == 0 and over == 0) else 1
