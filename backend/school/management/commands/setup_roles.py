from __future__ import annotations

from typing import Iterable

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

# We keep imports lazy and resilient: not all models may exist in this project yet.
try:
    from ...models import AttendanceRecord, AttendanceDaily
except Exception:  # pragma: no cover - be tolerant if models are moved/renamed
    AttendanceRecord = None  # type: ignore
    AttendanceDaily = None  # type: ignore


CORE_ROLES: list[str] = [
    # Core admin/leadership
    "Super Admin",
    "School Admin",
    "Principal",
    "Vice Principal",
    # Academic
    "Department Head",
    "Homeroom Teacher",
    "Subject Teacher",
    # Discipline/operations
    "Wing Supervisor",
    # Student/Guardian
    "Student",
    "Guardian",
    # Specialized/support
    "School Nurse",
    "Counselor Social",
    "Counselor Psych",
    "Special Support Supervisor",
    # Technical/guest
    "IT Support",
    "Guest",
]


def ensure_groups(names: Iterable[str]) -> dict[str, Group]:
    out: dict[str, Group] = {}
    for n in names:
        grp, _ = Group.objects.get_or_create(name=n)
        out[n] = grp
    return out


def add_perms_for_model(group: Group, model, codenames: Iterable[str]) -> int:
    if model is None:
        return 0
    ct = ContentType.objects.get_for_model(model)
    added = 0
    for code in codenames:
        try:
            perm = Permission.objects.get(content_type=ct, codename=code)
        except Permission.DoesNotExist:
            continue
        group.permissions.add(perm)
        added += 1
    return added


class Command(BaseCommand):
    help = (
        "Create/update RBAC groups and attach safe baseline permissions that exist in the current schema. "
        "Idempotent and non-destructive."
    )

    def handle(self, *args, **options):
        groups = ensure_groups(CORE_ROLES)

        # Minimal, safe baseline mapping aligned with current models.
        # Wing Supervisor: attendance review within their wing (model-level add/change/view; scoping is enforced in views).
        wing = groups.get("Wing Supervisor")
        total_added = 0
        for mdl in (AttendanceRecord, AttendanceDaily):
            total_added += (
                add_perms_for_model(
                    wing,
                    mdl,
                    [
                        # Django default model permissions
                        # We intentionally DO NOT grant delete.*
                        f"view_{mdl._meta.model_name}" if mdl else "",
                        f"add_{mdl._meta.model_name}" if mdl else "",
                        f"change_{mdl._meta.model_name}" if mdl else "",
                    ],
                )
                if wing and mdl
                else 0
            )

        # Teachers: allow recording their own class attendance (model-level; object scoping enforced at view layer).
        for teacher_group_name in ("Homeroom Teacher", "Subject Teacher"):
            tg = groups.get(teacher_group_name)
            for mdl in (AttendanceRecord, AttendanceDaily):
                total_added += (
                    add_perms_for_model(
                        tg,
                        mdl,
                        [
                            f"view_{mdl._meta.model_name}" if mdl else "",
                            f"add_{mdl._meta.model_name}" if mdl else "",
                            f"change_{mdl._meta.model_name}" if mdl else "",
                        ],
                    )
                    if tg and mdl
                    else 0
                )

        # Intentionally do NOT assign any grade/health/psych/social/IEP permissions here
        # because these models are not present (yet) in this repository version. This command
        # is designed to be re-run safely after such models are introduced.

        self.stdout.write(self.style.SUCCESS("RBAC setup complete."))
        self.stdout.write(f"Groups ensured: {', '.join(sorted(groups.keys()))}")
        self.stdout.write(f"Permissions attached (existing only): {total_added}")
        self.stdout.write(
            "Note: Object-level scoping must be enforced in views/serializers. "
            "Re-run this command after adding new sensitive models (health/psych/social/IEP)."
        )
