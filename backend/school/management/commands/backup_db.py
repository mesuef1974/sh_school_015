from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        "Create a full PostgreSQL database backup using the running Docker container "
        "(pg-sh-school). "
        "Outputs a timestamped .sql (or .sql.gz) file into a backups folder by default."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--out",
            dest="out_dir",
            type=str,
            help="Output directory for backups (default: <repo_root>/backups)",
        )
        parser.add_argument(
            "--gzip",
            dest="gzip",
            action="store_true",
            help="Compress the backup using gzip (.sql.gz)",
        )

    def handle(self, *args, **options):
        # Repo root is two levels up from backend dir: backend/ -> project root
        repo_root = Path(settings.BASE_DIR).parent
        out_dir = Path(options.get("out_dir") or repo_root / "backups")
        out_dir.mkdir(parents=True, exist_ok=True)

        # Read DB config from Django settings (dotenv already loaded in settings.py)
        pg_user = settings.DATABASES["default"].get("USER") or "postgres"
        pg_db = settings.DATABASES["default"].get("NAME") or "sh_school"
        pg_pass = settings.DATABASES["default"].get("PASSWORD") or "postgres"

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"pg_backup_{pg_db}_{ts}"
        use_gzip = bool(options.get("gzip"))

        container_tmp = f"/tmp/{base_name}.sql.gz" if use_gzip else f"/tmp/{base_name}.sql"
        host_out = out_dir / Path(container_tmp).name

        container = "pg-sh-school"

        # Ensure docker is available
        if not self._has_docker():
            raise CommandError("Docker CLI not available. Please install/start Docker Desktop.")

        # Ensure container exists
        if not self._container_exists(container):
            raise CommandError(
                (
                    f"Container '{container}' not found. "
                    "Start it via scripts/serve.ps1 or scripts/db_up.ps1 first."
                )
            )
        # Ensure running
        if not self._container_running(container):
            self.stdout.write(f"Starting container {container} ...")
            self._run(["docker", "start", container])

        self.stdout.write(
            self.style.HTTP_INFO(
                f"Creating database backup of '{pg_db}' from container '{container}' ..."
            )
        )

        # Build inner command executed inside container
        if use_gzip:
            inner = (
                f"PGPASSWORD='{pg_pass}'"
                f" pg_dump -U '{pg_user}' -d '{pg_db}'"
                " -F p --no-owner --no-privileges"
                f" | gzip -c > '{container_tmp}'"
            )
        else:
            inner = (
                f"PGPASSWORD='{pg_pass}'"
                f" pg_dump -U '{pg_user}' -d '{pg_db}'"
                " -F p --no-owner --no-privileges"
                f" > '{container_tmp}'"
            )

        # Execute inside container
        self._run(["docker", "exec", "-u", "postgres", container, "sh", "-lc", inner])
        # Copy to host
        self._run(["docker", "cp", f"{container}:{container_tmp}", str(host_out)])
        # Cleanup temp (best effort)
        try:
            self._run(["docker", "exec", container, "rm", "-f", container_tmp])
        except Exception:
            pass

        self.stdout.write(self.style.SUCCESS(f"Backup completed: {host_out}"))
        if use_gzip:
            self.stdout.write(
                self.style.HTTP_INFO(
                    (
                        f"Restore (gz): gunzip -c '{host_out}' | psql -h 127.0.0.1 -U {pg_user} "
                        f"-d {pg_db}"
                    )
                )
            )
        else:
            self.stdout.write(
                self.style.HTTP_INFO(
                    (
                        f"Restore (plain SQL): psql -h 127.0.0.1 -U {pg_user} -d {pg_db} "
                        f"-f '{host_out}'"
                    )
                )
            )

    # ---- helpers ----
    def _has_docker(self) -> bool:
        try:
            subprocess.run(["docker", "--version"], capture_output=True, check=True)
            return True
        except Exception:
            return False

    def _container_exists(self, name: str) -> bool:
        try:
            res = subprocess.run(
                [
                    "docker",
                    "ps",
                    "-a",
                    "--filter",
                    f"name={name}",
                    "--format",
                    "{{.ID}}",
                ],
                capture_output=True,
                check=True,
                text=True,
            )
            return bool(res.stdout.strip())
        except Exception:
            return False

    def _container_running(self, name: str) -> bool:
        try:
            res = subprocess.run(
                ["docker", "ps", "--filter", f"name={name}", "--format", "{{.ID}}"],
                capture_output=True,
                check=True,
                text=True,
            )
            return bool(res.stdout.strip())
        except Exception:
            return False

    def _run(self, args: list[str]) -> None:
        proc = subprocess.run(args, text=True)
        if proc.returncode != 0:
            raise CommandError(f"Command failed: {' '.join(args)}")
