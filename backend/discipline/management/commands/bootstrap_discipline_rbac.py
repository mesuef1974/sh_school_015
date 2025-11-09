from __future__ import annotations

from typing import Dict, List

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from discipline.models import Incident, Violation


class Command(BaseCommand):
    help = (
        "Create/refresh default Discipline RBAC groups and attach granular permissions. "
        "Idempotent and safe to re-run."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--with-access",
            action="store_true",
            help=("Also grant 'discipline.access' catalog/role permission to WingSupervisor, Counselor, Leadership."),
        )

    def handle(self, *args, **options):
        with_access: bool = bool(options.get("with_access"))

        inc_ct = ContentType.objects.get_for_model(Incident)
        viol_ct = ContentType.objects.get_for_model(Violation)

        # Ensure all permissions exist (create them if missing using model Meta definitions)
        inc_meta = {code: label for code, label in getattr(Incident._meta, "permissions", [])}
        codes = list(inc_meta.keys())
        perms: Dict[str, Permission] = {}
        for code in codes:
            perm, created = Permission.objects.get_or_create(
                codename=code,
                content_type=inc_ct,
                defaults={"name": inc_meta.get(code, code.replace("_", " ").title())},
            )
            # Keep permission name aligned with model meta (idempotent update)
            desired_name = inc_meta.get(code, perm.name)
            if perm.name != desired_name:
                perm.name = desired_name
                perm.save(update_fields=["name"])
            perms[code] = perm

        viol_meta = {code: label for code, label in getattr(Violation._meta, "permissions", [])}
        access_label = viol_meta.get("access", "Can access discipline module")
        access_perm, _ = Permission.objects.get_or_create(
            codename="access", content_type=viol_ct, defaults={"name": access_label}
        )
        if access_perm.name != access_label:
            access_perm.name = access_label
            access_perm.save(update_fields=["name"])

        def ensure_group(name: str, perm_keys: List[str], add_access: bool = False) -> Group:
            g, _ = Group.objects.get_or_create(name=name)
            perm_objs = [perms[k] for k in perm_keys]
            if add_access:
                perm_objs.append(access_perm)
            # Merge with any existing unrelated perms on the group
            current = list(g.permissions.all())
            keep = [p for p in current if p.codename not in codes and p.codename != "access"]
            g.permissions.set(keep + perm_objs)
            g.save()
            return g

        # Mapping based on docs (Teacher minimal, others broader)
        ensure_group("Teacher", ["incident_create", "incident_submit"], add_access=False)
        ensure_group(
            "WingSupervisor",
            [
                "incident_review",
                "incident_escalate",
                "incident_notify_guardian",
                "incident_close",
            ],
            add_access=True if with_access else False,
        )
        ensure_group(
            "Counselor",
            [
                "incident_review",
                "incident_notify_guardian",
            ],
            add_access=True if with_access else False,
        )
        ensure_group(
            "Leadership",
            [
                "incident_review",
                "incident_escalate",
                "incident_notify_guardian",
                "incident_close",
            ],
            add_access=True if with_access else False,
        )

        self.stdout.write(self.style.SUCCESS("Discipline RBAC groups ensured."))
