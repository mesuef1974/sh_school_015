from __future__ import annotations

import os
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Ensure a Django superuser exists with credentials from environment\n"
        "DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL, DJANGO_SUPERUSER_PASSWORD.\n"
        "Idempotent: creates if missing; if exists, updates email and password when provided."
    )

    def handle(self, *args, **options):
        username = os.getenv("DJANGO_SUPERUSER_USERNAME")
        email = os.getenv("DJANGO_SUPERUSER_EMAIL")
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD")

        if not (username and email and password):
            self.stdout.write(
                self.style.WARNING(
                    "DJANGO_SUPERUSER_* env vars are not fully provided; skipping ensure_superuser."
                )
            )
            return

        User = get_user_model()
        user, created = User.objects.get_or_create(
            username=username,
            defaults={"email": email, "is_staff": True, "is_superuser": True},
        )
        changed = False

        # Always enforce is_staff/is_superuser for this bootstrap user
        if not user.is_staff:
            user.is_staff = True
            changed = True
        if not user.is_superuser:
            user.is_superuser = True
            changed = True

        # Update email if different
        if email and user.email != email:
            user.email = email
            changed = True

        # Update password if provided (always reset to ensure correctness)
        if password:
            user.set_password(password)
            changed = True

        if created or changed:
            user.save()

        if created:
            self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' created."))
        elif changed:
            self.stdout.write(self.style.HTTP_INFO(f"Superuser '{username}' updated."))
        else:
            self.stdout.write(
                self.style.HTTP_INFO(f"Superuser '{username}' already up-to-date.")
            )
