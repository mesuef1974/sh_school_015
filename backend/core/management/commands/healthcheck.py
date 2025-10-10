"""
Healthcheck management command.

Usage:
    python manage.py healthcheck

Exits with code 0 if the app is healthy (DB reachable), non-zero otherwise.
Prints a short status line to stdout/stderr.
"""

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Checks application health (DB connectivity). Exits 0 if healthy, 1 otherwise."

    def handle(self, *args, **options):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            self.stdout.write(self.style.SUCCESS("ok"))
            return 0
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"db: {e}"))
            return 1
