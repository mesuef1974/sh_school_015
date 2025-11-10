from __future__ import annotations

# Friendly guard: this file is a Django management command and should not be run directly.
# If executed as a standalone script (e.g., `python backend/discipline/management/commands/load_discipline_catalog.py`),
# provide a clear hint instead of crashing with an ImportError due to relative imports.
if __name__ == "__main__":  # pragma: no cover - developer convenience only
    import sys

    hint = (
        "This file is a Django management command and cannot run directly.\n"
        "Use one of the following instead:\n"
        "  1) From repo root: scripts\\load_discipline_catalog.ps1 -Purge\n"
        "  2) From backend/: python manage.py load_discipline_catalog --purge\n"
        'You may pass --file "D:\\sh_school_015\\DOC\\school_DATA\\violations_detailed.json" if needed.'
    )
    print(hint)
    sys.exit(2)

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction, connection
from django.db.utils import OperationalError

from ...models import BehaviorLevel, Violation
from django.conf import settings


class Command(BaseCommand):
    help = (
        "Load or refresh the discipline behavior levels and violations catalog from a JSON file.\n"
        "The expected structure is an object with a 'behavior_levels' array; each item contains:\n"
        "  - level (str): display name of the level (e.g., 'الأولى')\n"
        "  - description (str)\n"
        "  - violations (array): each with id (code), category, description, actions, sanctions\n"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            dest="file",
            default=None,
            help=(
                "Path to JSON file. If omitted, defaults to DOC/school_DATA/violations_detailed.json under BASE_DIR."
            ),
        )
        parser.add_argument(
            "--purge",
            action="store_true",
            help="Purge existing BehaviorLevel and Violation records before load",
        )

    def handle(self, *args, **options):
        # Print resolved DB target for diagnostics
        default_db = getattr(settings, "DATABASES", {}).get("default", {})
        target = (
            f"{default_db.get('ENGINE','?')}://{default_db.get('HOST','?')}:{default_db.get('PORT','?')}/"
            f"{default_db.get('NAME','?')} as {default_db.get('USER','?')}"
        )
        self.stdout.write(self.style.NOTICE(f"Target database: {target}"))
        # Early connectivity probe for clearer error if credentials are wrong
        try:
            with connection.cursor() as cur:
                cur.execute("SELECT 1")
        except OperationalError as e:
            hint = (
                "Database connection failed. Verify backend/.env PG_* (PG_DB, PG_USER, PG_PASSWORD, PG_HOST, PG_PORT) "
                "or provide a DATABASE_URL. If you don't have a local PostgreSQL, you can start one via scripts\\db_up.ps1.\n"
                "Example: PG_DB=sh_school, PG_USER=postgres, PG_PASSWORD=postgres, PG_HOST=127.0.0.1, PG_PORT=5432"
            )
            raise CommandError(f"Cannot connect to database ({target}). Details: {e}.\n{hint}")

        file_arg = options.get("file")
        if file_arg:
            json_path = Path(file_arg)
        else:
            # Default to the repo root DOC/... (BASE_DIR points to backend/)
            json_path = Path(settings.BASE_DIR).parent / "DOC" / "school_DATA" / "violations_detailed.json"

        if not json_path.exists():
            raise CommandError(f"JSON file not found: {json_path}")

        self.stdout.write(self.style.NOTICE(f"Loading catalog from: {json_path}"))

        with json_path.open("r", encoding="utf-8") as f:
            try:
                payload = json.load(f)
            except json.JSONDecodeError as e:
                raise CommandError(f"Invalid JSON: {e}")

        blist = payload.get("behavior_levels")
        if not isinstance(blist, list) or not blist:
            raise CommandError("JSON must contain a non-empty 'behavior_levels' array")

        with transaction.atomic():
            if options.get("purge"):
                # Purge children first
                Violation.objects.all().delete()
                BehaviorLevel.objects.all().delete()
                self.stdout.write(self.style.WARNING("Purged existing catalog records."))

            level_map: dict[int, BehaviorLevel] = {}
            # Use the position as numeric code (1..N) and 'level' as name
            for idx, level_obj in enumerate(blist, start=1):
                name = str(level_obj.get("level") or f"Level {idx}").strip()
                desc = str(level_obj.get("description") or "").strip()

                level, _created = BehaviorLevel.objects.update_or_create(
                    code=idx,
                    defaults={
                        "name": name,
                        "description": desc,
                    },
                )
                level_map[idx] = level

            # Upsert violations
            v_count = 0
            for idx, level_obj in enumerate(blist, start=1):
                level = level_map[idx]
                violations = level_obj.get("violations") or []
                if not isinstance(violations, list):
                    continue
                for v in violations:
                    code = str(v.get("id") or "").strip()
                    if not code:
                        # Skip invalid entries silently
                        continue
                    category = (v.get("category") or "").strip()
                    description = (v.get("description") or "").strip()
                    actions = v.get("actions") or []
                    sanctions = v.get("sanctions") or []

                    # Ensure arrays
                    if not isinstance(actions, list):
                        actions = [str(actions)] if actions else []
                    if not isinstance(sanctions, list):
                        sanctions = [str(sanctions)] if sanctions else []

                    # Severity: align with level code by default (can be overridden later)
                    severity = idx

                    # requires_committee: infer false by default; can be set true if wording hints present
                    requires_committee = False

                    Violation.objects.update_or_create(
                        code=code,
                        defaults={
                            "level": level,
                            "category": category,
                            "description": description,
                            "default_actions": actions,
                            "default_sanctions": sanctions,
                            "severity": severity,
                            "requires_committee": requires_committee,
                        },
                    )
                    v_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Catalog loaded successfully: {BehaviorLevel.objects.count()} levels, {Violation.objects.count()} violations (processed {v_count})."
            )
        )
