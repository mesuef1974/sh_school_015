from __future__ import annotations

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Ensure a Django superuser exists using env vars:\n"
        "DJANGO_SUPERUSER_USERNAME (required), DJANGO_SUPERUSER_EMAIL (optional), DJANGO_SUPERUSER_PASSWORD (optional).\n"
        "If user exists: updates email/password when provided. If missing: requires both email and password to create."
    )

    def handle(self, *args, **options):
        username = os.getenv("DJANGO_SUPERUSER_USERNAME")
        email = os.getenv("DJANGO_SUPERUSER_EMAIL")
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD")

        if not username:
            self.stdout.write(self.style.WARNING("DJANGO_SUPERUSER_USERNAME is required; skipping ensure_superuser."))
            return

        User = get_user_model()
        user = None
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            if email and password:
                user = User.objects.create_user(username=username, email=email, password=password)
                user.is_staff = True
                user.is_superuser = True
                user.save()
                self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' created."))
                return
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"User '{username}' not found and insufficient data to create (need both email and password)."
                    )
                )
                return

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

        if changed:
            user.save()
            self.stdout.write(self.style.HTTP_INFO(f"Superuser '{username}' updated."))
        else:
            self.stdout.write(self.style.HTTP_INFO(f"Superuser '{username}' already up-to-date."))
