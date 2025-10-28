from django.core.management.base import BaseCommand, CommandError
from django.test import Client


class Command(BaseCommand):
    help = (
        "Run a lightweight smoke test against built-in health endpoints.\n\n"
        "Success criteria:\n"
        "- GET /livez returns 204.\n"
        "- GET /healthz returns 200 with body 'ok' when DB is reachable, or 500 if DB is down.\n"
        "Exits with code 0 on success and 1 on failure."
    )

    def handle(self, *args, **options):  # noqa: D401
        client = Client()
        ok = True

        # Check /livez
        resp_livez = client.get("/livez")
        if resp_livez.status_code == 204:
            self.stdout.write(self.style.SUCCESS("/livez: 204 (ok)"))
        else:
            self.stderr.write(self.style.ERROR(f"/livez: expected 204, got {resp_livez.status_code}"))
            ok = False

        # Check /healthz
        resp_health = client.get("/healthz")
        if resp_health.status_code == 200 and resp_health.content.strip() == b"ok":
            self.stdout.write(self.style.SUCCESS("/healthz: 200 ok"))
        elif resp_health.status_code == 500:
            # Acceptable for smoke: app is up even if DB is not.
            self.stdout.write(self.style.WARNING("/healthz: 500 (DB not reachable)"))
        else:
            self.stderr.write(
                self.style.ERROR(f"/healthz: unexpected status {resp_health.status_code} body={resp_health.content!r}")
            )
            ok = False

        if not ok:
            raise CommandError("Smoke test failed")

        self.stdout.write(self.style.SUCCESS("Smoke test passed"))
        # Returning normally signals exit code 0.
