from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from ...models import Staff

EXCLUDED_ROLES: set[str] = {"developer", "school_principal"}


@dataclass
class Result:
    set_staff_true: int = 0
    set_staff_false: int = 0
    unchanged_true: int = 0
    unchanged_false: int = 0
    skipped_no_user: int = 0


class Command(BaseCommand):
    help = (
        "Activate all linked user accounts as staff (is_staff=True) for Staff, "
        "except those whose role is 'developer' or 'school_principal'. "
        "Idempotent; supports --dry-run."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would change without writing to the database.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run: bool = bool(options.get("dry_run"))

        User = get_user_model()
        qs: Iterable[Staff] = Staff.objects.select_related("user").all().order_by("id")
        res = Result()

        for s in qs:
            if not s.user_id:
                res.skipped_no_user += 1
                continue

            u: User = s.user  # type: ignore[assignment]

            if s.role in EXCLUDED_ROLES:
                # Ensure excluded roles are not marked as staff
                if u.is_staff:
                    if not dry_run:
                        u.is_staff = False
                        u.save(update_fields=["is_staff"])
                    res.set_staff_false += 1
                else:
                    res.unchanged_false += 1
                continue

            # For all others, ensure staff and active
            changed = False
            if not u.is_staff:
                u.is_staff = True
                changed = True
            if not u.is_active:
                u.is_active = True
                changed = True

            if changed:
                if not dry_run:
                    # Save only fields we might have changed
                    fields = ["is_staff", "is_active"]
                    u.save(update_fields=fields)
                res.set_staff_true += 1
            else:
                res.unchanged_true += 1

        # Report
        def line(label: str, value: int) -> str:
            return f"- {label}: {value}"

        self.stdout.write(self.style.SUCCESS("activate_staff_users summary:"))
        self.stdout.write(line("set is_staff=True (and activated)", res.set_staff_true))
        self.stdout.write(line("set is_staff=False (excluded roles)", res.set_staff_false))
        self.stdout.write(line("unchanged already staff", res.unchanged_true))
        self.stdout.write(line("unchanged already non-staff (excluded)", res.unchanged_false))
        self.stdout.write(line("skipped (no linked user)", res.skipped_no_user))

        if dry_run:
            # Ensure no writes persist
            raise transaction.TransactionManagementError("Dry-run requested: transaction rolled back after reporting.")
