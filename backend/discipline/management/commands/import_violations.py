from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from discipline.models import BehaviorLevel, Violation


class Command(BaseCommand):
    help = (
        "[DEPRECATED] Use 'load_discipline_catalog' instead. "
        "This legacy command imports/updates the catalog from a JSON file such as "
        "DOC/school_DATA/violations_detailed.json."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            dest="file",
            help=("Path to the JSON file. Defaults to <repo_root>/DOC/repo/violations_detailed.json"),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse and validate but do not write to the database.",
        )

    def handle(self, *args, **options):
        # Determine default path relative to repo root (BASE_DIR points to backend/)
        repo_root = Path(settings.BASE_DIR).parent
        default_path = repo_root / "DOC" / "repo" / "violations_detailed.json"
        file_path = Path(options.get("file") or default_path)

        if not file_path.exists():
            raise CommandError(f"JSON file not found: {file_path}")

        self.stdout.write(self.style.NOTICE(f"Loading violations from: {file_path}"))

        with file_path.open("r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                raise CommandError(f"Invalid JSON: {e}")

        levels: List[Dict[str, Any]] = data.get("behavior_levels") or []
        if not levels:
            raise CommandError("No 'behavior_levels' array found in JSON.")

        # Map Arabic names to numeric codes 1–4
        arabic_level_to_code = {
            "الأولى": 1,
            "الاولى": 1,
            "الثانية": 2,
            "الثالثة": 3,
            "الرابعة": 4,
        }

        # Perform DB writes in a single transaction for consistency
        dry_run: bool = bool(options.get("dry_run"))

        created_levels = 0
        updated_levels = 0
        created_violations = 0
        updated_violations = 0

        @transaction.atomic
        def _apply():
            nonlocal created_levels, updated_levels, created_violations, updated_violations
            for lvl in levels:
                lvl_name = str(lvl.get("level") or "").strip()
                lvl_code = arabic_level_to_code.get(lvl_name)
                if not lvl_code:
                    # Try to parse digits if present (e.g., "1", "1-الأولى")
                    digits = "".join(ch for ch in lvl_name if ch.isdigit())
                    lvl_code = int(digits) if digits else None
                if not lvl_code:
                    raise CommandError(f"Unrecognized level name: {lvl_name!r}")

                lvl_desc = lvl.get("description") or ""
                bl, created = BehaviorLevel.objects.update_or_create(
                    code=lvl_code,
                    defaults={
                        "name": lvl_name,
                        "description": lvl_desc,
                    },
                )
                if created:
                    created_levels += 1
                else:
                    updated_levels += 1

                violations: List[Dict[str, Any]] = lvl.get("violations") or []
                for v in violations:
                    v_code = v.get("id") or v.get("code")
                    if not v_code:
                        raise CommandError("Violation entry missing 'id' (code)")
                    category = v.get("category") or ""
                    desc = v.get("description") or ""
                    actions = v.get("actions") or v.get("default_actions") or []
                    sanctions = v.get("sanctions") or v.get("default_sanctions") or []

                    # Derive severity from level code; can be refined later if spec provides
                    severity = int(lvl_code)
                    requires_committee = True if severity >= 3 else False

                    viol, v_created = Violation.objects.update_or_create(
                        code=str(v_code),
                        defaults={
                            "level": bl,
                            "category": category,
                            "description": desc,
                            "default_actions": list(actions),
                            "default_sanctions": list(sanctions),
                            "severity": severity,
                            "requires_committee": requires_committee,
                        },
                    )
                    if v_created:
                        created_violations += 1
                    else:
                        updated_violations += 1

        if dry_run:
            # Run in a rollback-only transaction
            with transaction.atomic():
                _apply()
                transaction.set_rollback(True)
                self.stdout.write(self.style.WARNING("Dry-run complete: no changes were committed."))
        else:
            _apply()
            self.stdout.write(
                self.style.SUCCESS(
                    "Violations imported: "
                    f"Levels created {created_levels}, updated {updated_levels}; "
                    f"Violations created {created_violations}, updated {updated_violations}."
                )
            )
