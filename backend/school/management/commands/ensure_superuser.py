from __future__ import annotations

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Ensure a Django superuser exists with credentials from CLI args or environment.\n"
        "--username is required; --email/--password are optional for updating.\n"
        "If creating a new user, both email and password are required."
    )

    def add_arguments(self, parser):
        parser.add_argument("--username", type=str, help="Superuser username")
        parser.add_argument("--email", type=str, help="Superuser email")
        parser.add_argument("--password", type=str, help="Superuser password (plain text)")

    def handle(self, *args, **options):
        username = options.get("username") or os.getenv("DJANGO_SUPERUSER_USERNAME")
        email = options.get("email") or os.getenv("DJANGO_SUPERUSER_EMAIL")
        password = options.get("password") or os.getenv("DJANGO_SUPERUSER_PASSWORD")

        if not username:
            self.stdout.write(self.style.WARNING("Username is required (via --username or DJANGO_SUPERUSER_USERNAME)."))
            return

        # If this is the default fallback user and no password is set, use a known default.
        if username == "mesuef" and not password:
            password = "Admin@12345"

        User = get_user_model()
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # Create the user even if email is missing; use a placeholder if needed.
            if password:
                if not email:
                    email = f"{username}@example.local"
                # Create a regular user first (works for any custom user model), then elevate
                user = User.objects.create_user(username=username, email=email, password=password)
                # Elevate to staff/superuser to guarantee admin access
                user.is_staff = True
                user.is_superuser = True
                # If the model has a 'role' field, set it to 'admin' (optional)
                try:
                    if hasattr(user, "role"):
                        setattr(user, "role", "admin")
                except Exception:
                    pass
                user.save()
                self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' created."))
                return
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"User '{username}' not found and no password was provided or defaulted. Cannot create user."
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

        # Ensure the user has the admin role if the field exists
        try:
            if hasattr(user, "role") and getattr(user, "role") != "admin":
                setattr(user, "role", "admin")
                changed = True
        except Exception:
            # Ignore if the custom user model doesn't have role or isn't editable
            pass

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
            self.stdout.write(self.style.HTTP_INFO(f"Superuser '{username}' updated/verified."))
        else:
            self.stdout.write(self.style.HTTP_INFO(f"Superuser '{username}' already up-to-date."))
