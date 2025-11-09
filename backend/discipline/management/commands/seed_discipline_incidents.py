import random
from datetime import timedelta
from typing import Optional

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.utils import timezone

from ...models import Incident, Violation


class Command(BaseCommand):
    help = (
        "Seed demo discipline incidents for a given username to quickly verify UI/API.\n"
        "Idempotent when using --clear. Without --clear, it will just add more incidents."
    )

    def add_arguments(self, parser):
        parser.add_argument("--user", required=True, help="Username to set as reporter for seeded incidents")
        parser.add_argument("--count", type=int, default=12, help="Number of incidents to create (default: 12)")
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing incidents reported by this user before seeding (idempotent mode)",
        )
        parser.add_argument("--dry-run", action="store_true", help="Do not write anything, just report plan")
        parser.add_argument(
            "--student",
            type=int,
            default=None,
            help="Optional Student ID to target. If omitted, a random student will be picked for each incident.",
        )

    def handle(self, *args, **options):
        username: str = options["user"].strip()
        count: int = max(1, min(200, int(options.get("count") or 12)))
        clear: bool = bool(options.get("clear"))
        dry_run: bool = bool(options.get("dry_run"))
        target_student: Optional[int] = options.get("student")

        User = get_user_model()
        try:
            reporter = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"User not found: {username}")

        # Resolve students provider lazily to avoid hard dependency at import time
        Student = None
        try:
            from school.models import Student as StudentModel  # type: ignore

            Student = StudentModel
        except Exception:
            pass

        if not Violation.objects.exists():
            raise CommandError("No violations found. Run 'python manage.py import_violations' first.")

        if clear:
            qs = Incident.objects.filter(reporter_id=reporter.id)
            n = qs.count()
            if dry_run:
                self.stdout.write(self.style.WARNING(f"[dry-run] Would delete {n} existing incidents for {username}"))
            else:
                qs.delete()
                self.stdout.write(self.style.SUCCESS(f"Deleted {n} incidents for {username}"))

        now = timezone.now()
        violations = list(Violation.objects.all())
        if not violations:
            raise CommandError("Violations catalog is empty.")

        # Try to get student population
        students_pool = []
        if Student is not None:
            try:
                if target_student:
                    st = Student.objects.filter(id=target_student).values_list("id", flat=True)
                    students_pool = list(st)
                else:
                    students_pool = list(Student.objects.values_list("id", flat=True)[:500])
            except Exception:
                students_pool = []
        if not students_pool and target_student:
            # Fallback to the provided id only
            students_pool = [int(target_student)]

        created = 0
        statuses = ["open", "under_review", "closed"]
        for i in range(count):
            viol = random.choice(violations)
            sev = int(viol.severity or 1)
            committee = bool(viol.requires_committee or sev >= 3)
            days_ago = random.randint(0, 30)
            occurred_at = now - timedelta(days=days_ago, hours=random.randint(0, 6))
            status_choice = random.choice(statuses)

            # pick a student
            if students_pool:
                student_id = random.choice(students_pool)
            else:
                # As a last resort, try to pick a student id around 1..50 (may fail at save if invalid)
                student_id = random.randint(1, 50)

            payload = dict(
                violation_id=viol.id,
                student_id=student_id,
                reporter_id=reporter.id,
                occurred_at=occurred_at,
                location=random.choice(["فصل 1/1", "ساحة", "ممر A", "مختبر"]),
                narrative=random.choice(
                    [
                        "مقاطعة المعلم أثناء الشرح",
                        "تأخر عن الحصة",
                        "إزعاج الطلاب الآخرين",
                        "خروج بدون إذن",
                    ]
                ),
                status=status_choice,
                severity=sev,
                committee_required=committee,
            )

            # Create incident
            if dry_run:
                self.stdout.write(self.style.WARNING(f"[dry-run] Would create incident: {payload}"))
                created += 1
                continue

            inc = Incident(
                violation_id=payload["violation_id"],
                student_id=payload["student_id"],
                reporter_id=payload["reporter_id"],
                occurred_at=payload["occurred_at"],
                location=payload["location"],
                narrative=payload["narrative"],
                status=payload["status"],
                severity=payload["severity"],
                committee_required=payload["committee_required"],
            )
            # Derive workflow timestamps
            if status_choice in ("under_review", "closed"):
                inc.submitted_at = occurred_at + timedelta(hours=1)
            if status_choice == "under_review":
                inc.reviewed_at = None
            if status_choice == "closed":
                inc.reviewed_at = occurred_at + timedelta(hours=6)
                inc.closed_at = occurred_at + timedelta(hours=12)
                inc.closed_by = reporter
            inc.save()
            created += 1

        self.stdout.write(self.style.SUCCESS(f"Seeded {created} incidents for {username}"))