from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from ...models import Staff


@dataclass
class Result:
    created: int = 0
    linked_existing: int = 0
    skipped_no_email: int = 0
    skipped_has_user: int = 0
    skipped_excluded: int = 0


EXCLUDED_NAME_KEYWORDS = {
    "سفيان": {"developer"},  # المطور سفيان
    "سلطان": {"school_principal", "admin"},  # مدير المدرسة/أدمن سلطان
}


def should_exclude(staff: Staff) -> bool:
    name = (staff.full_name or "").strip()
    role = (staff.role or "").strip()
    for kw, roles in EXCLUDED_NAME_KEYWORDS.items():
        if kw in name and (not roles or role in roles):
            return True
    return False


def username_from_email(email: str) -> str:
    local = (email or "").split("@", 1)[0].strip()
    # Basic sanitize: keep common username characters
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
    sanitized = "".join(ch for ch in local if ch in allowed)
    return sanitized or local


def ensure_unique_username(base: str, existing_usernames: set[str]) -> str:
    if base not in existing_usernames:
        return base
    i = 1
    while True:
        candidate = f"{base}{i}"
        if candidate not in existing_usernames:
            return candidate
        i += 1


class Command(BaseCommand):
    help = (
        "Create/link a Django user for each Staff where missing. "
        "Username = email local-part; password = '123'. "
        "Excludes developer Sufyan and principal/admin Sultan. Idempotent."
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
        # Cache usernames set for fast uniqueness check
        existing_usernames: set[str] = set(User.objects.values_list("username", flat=True))

        qs: Iterable[Staff] = Staff.objects.all().order_by("id")
        res = Result()

        for staff in qs:
            if should_exclude(staff):
                res.skipped_excluded += 1
                continue

            if staff.user_id:
                res.skipped_has_user += 1
                continue

            if not staff.email:
                res.skipped_no_email += 1
                continue

            base_username = username_from_email(staff.email)
            if not base_username:
                res.skipped_no_email += 1
                continue

            username = ensure_unique_username(base_username, existing_usernames)

            # Try to find an existing user with same username to link
            try:
                user = User.objects.get(username=username)
                # If it exists, just link without changing password/email
                staff.user = user
                if not dry_run:
                    staff.save(update_fields=["user"])
                res.linked_existing += 1
            except User.DoesNotExist:
                # Create new user
                user = User(username=username, email=staff.email)
                if not dry_run:
                    user.set_password("123")
                    user.save()
                    staff.user = user
                    staff.save(update_fields=["user"])
                res.created += 1
                existing_usernames.add(username)

        # Reporting
        def line(label: str, value: int) -> str:
            return f"- {label}: {value}"

        self.stdout.write(self.style.SUCCESS("ensure_staff_users summary:"))
        self.stdout.write(line("created users", res.created))
        self.stdout.write(line("linked to existing users", res.linked_existing))
        self.stdout.write(line("skipped (no email)", res.skipped_no_email))
        self.stdout.write(line("skipped (already has user)", res.skipped_has_user))
        self.stdout.write(line("skipped (excluded by name/role)", res.skipped_excluded))

        if dry_run:
            # Rollback any accidental writes in dry-run
            raise transaction.TransactionManagementError(
                "Dry-run requested: transaction rolled back after reporting."
            )
