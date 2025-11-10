from __future__ import annotations

import sys
from pathlib import Path

from django.conf import settings
from django.core.management import BaseCommand, call_command, CommandError
from django.db import connection
from django.db.utils import OperationalError
from django.apps import apps


class Command(BaseCommand):
    help = (
        "Ensure discipline reference data (BehaviorLevel & Violation) exists: "
        "checks DB connectivity, applies migrations if needed, and loads the "
        "catalog JSON when tables are empty."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            dest="file",
            default="",
            help=(
                "Optional path to violations catalog JSON. If omitted, the command "
                "uses the default repository path DOC/school_DATA/violations_detailed.json"
            ),
        )
        parser.add_argument(
            "--purge",
            action="store_true",
            default=False,
            help="Drop existing catalog entries before loading (delegated to loader).",
        )

    def handle(self, *args, **options):
        # 1) Sanity: DB connectivity and target summary
        default_db = settings.DATABASES.get("default", {})
        target = (
            f"{default_db.get('ENGINE','?')}://{default_db.get('HOST','?')}:{default_db.get('PORT','?')}/"
            f"{default_db.get('NAME','?')} as {default_db.get('USER','?')}"
        )
        self.stdout.write(self.style.NOTICE(f"Target database: {target}"))

        # Probe connection early (friendly error on failure)
        self.stdout.write("Checking database connectivity ...")
        try:
            with connection.cursor() as cur:  # noqa: SIM115 - explicit scope
                cur.execute("SELECT 1")
        except OperationalError as e:
            hint = (
                "Database connection failed. Verify backend/.env PG_* (PG_DB, PG_USER, PG_PASSWORD, PG_HOST, PG_PORT) "
                "or provide a DATABASE_URL. If you don't have a local PostgreSQL, you can start one via scripts\\db_up.ps1.\n"
                "Example: PG_DB=sh_school, PG_USER=postgres, PG_PASSWORD=postgres, PG_HOST=127.0.0.1, PG_PORT=5432"
            )
            raise CommandError(f"Cannot connect to database ({target}). Details: {e}.\n{hint}")
        self.stdout.write(self.style.SUCCESS("Database connection OK."))

        # 2) Ensure migrations are applied
        self.stdout.write("Applying migrations (if any) ...")
        call_command("migrate", interactive=False, verbosity=0)
        self.stdout.write(self.style.SUCCESS("Migrations up-to-date."))

        # Fetch models dynamically to avoid import-time app registry issues
        BehaviorLevel = apps.get_model("discipline", "BehaviorLevel")
        Violation = apps.get_model("discipline", "Violation")

        before_levels = BehaviorLevel.objects.count()
        before_violations = Violation.objects.count()
        self.stdout.write(f"Current catalog counts — BehaviorLevel: {before_levels}, Violation: {before_violations}")

        # 3) Decide JSON path
        json_file_arg = (options.get("file") or "").strip()
        if json_file_arg:
            json_path = Path(json_file_arg)
        else:
            # Default relative to repo root; BASE_DIR points to backend/
            json_path = Path(settings.BASE_DIR).parent / "DOC" / "school_DATA" / "violations_detailed.json"

        # 4) Load if needed
        if before_levels == 0 or before_violations == 0:
            if not json_path.exists():
                self.stdout.write(
                    self.style.WARNING(
                        f"Catalog appears empty but JSON not found at: {json_path}. "
                        f"Pass --file to specify a custom path."
                    )
                )
                # Explicit non-zero exit to signal unmet requirement
                sys.exit(2)

            self.stdout.write(
                self.style.NOTICE(f"Loading discipline catalog from: {json_path} (purge={bool(options.get('purge'))})")
            )
            call_command(
                "load_discipline_catalog",
                file=str(json_path),
                purge=bool(options.get("purge")),
                verbosity=1,
            )
        else:
            self.stdout.write("Catalog already present. Skipping load.")

        # 5) Summarize
        after_levels = BehaviorLevel.objects.count()
        after_violations = Violation.objects.count()
        self.stdout.write(
            self.style.SUCCESS(f"Final catalog counts — BehaviorLevel: {after_levels}, Violation: {after_violations}")
        )

        if after_levels == 0 or after_violations == 0:
            self.stderr.write(
                self.style.ERROR(
                    "Discipline catalog still empty after ensure step. Check JSON integrity and DB settings."
                )
            )
            sys.exit(3)

        self.stdout.write(self.style.SUCCESS("Discipline data is present and ready."))
