from __future__ import annotations

import sys
from typing import Any, Dict

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Diagnose database configuration and connectivity. Safe, read-only checks."

    def handle(self, *args, **options):  # noqa: D401
        db: Dict[str, Any] = settings.DATABASES.get("default", {})
        engine = db.get("ENGINE", "")
        name = db.get("NAME", "")
        user = db.get("USER", "")
        host = db.get("HOST", "")
        port = db.get("PORT", "")

        self.stdout.write(
            self.style.HTTP_INFO("Effective database settings (default):")
        )
        self.stdout.write(f"  ENGINE   : {engine}")
        self.stdout.write(f"  NAME     : {name}")
        if user:
            self.stdout.write(f"  USER     : {user}")
        if host:
            self.stdout.write(f"  HOST     : {host}")
        if port:
            self.stdout.write(f"  PORT     : {port}")

        # Hint about USE_SQLITE
        use_sqlite = getattr(settings, "USE_SQLITE", None)
        if use_sqlite is not None:
            self.stdout.write(f"  USE_SQLITE: {use_sqlite}")

        # Try to connect
        self.stdout.write("")
        self.stdout.write(self.style.HTTP_INFO("Testing database connection ..."))
        try:
            with connection.cursor() as cursor:
                vendor = connection.vendor
                if vendor == "postgresql":
                    cursor.execute("SELECT version();")
                    ver = cursor.fetchone()[0]
                    self.stdout.write(
                        self.style.SUCCESS("Connected to PostgreSQL successfully.")
                    )
                    self.stdout.write(f"  Server version: {ver}")
                elif vendor == "sqlite":
                    cursor.execute("select sqlite_version();")
                    ver = cursor.fetchone()[0]
                    self.stdout.write(
                        self.style.SUCCESS("Connected to SQLite successfully.")
                    )
                    self.stdout.write(f"  SQLite version: {ver}")
                else:
                    self.stdout.write(
                        self.style.SUCCESS(f"Connected successfully (vendor={vendor}).")
                    )
        except Exception as exc:  # pragma: no cover - environment dependent
            self.stdout.write("")
            self.stderr.write(self.style.ERROR("Failed to connect to the database."))
            self.stderr.write(self.style.ERROR(f"  {exc}"))
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("Common fixes:"))
            self.stdout.write(
                "  - If you intend to use SQLite locally: set USE_SQLITE=True in backend/.env "
                "(or copy .env.example)."
            )
            self.stdout.write(
                "  - If you intend to use PostgreSQL: set USE_SQLITE=False and ensure "
                "DB_NAME/DB_USER/DB_PASSWORD/DB_HOST/DB_PORT are correct in backend/.env."
            )
            self.stdout.write(
                "  - Ensure PostgreSQL service is running and credentials are valid. "
                "Use scripts/postgres_reset_password.ps1 if you forgot the password (Windows)."
            )
            # Exit with non-zero to signal failure in CI/local scripts if desired
            sys.exit(2)

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS("Database diagnostics completed successfully.")
        )
