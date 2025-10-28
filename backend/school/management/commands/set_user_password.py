from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = "Create or update a user and set password. " "Use --superuser/--staff flags to set staff/superuser."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True, help="Username to create/update")
        parser.add_argument("--password", required=True, help="Password to set")
        parser.add_argument("--email", default="", help="Optional email")
        parser.add_argument("--superuser", action="store_true", help="Mark as superuser")
        parser.add_argument("--staff", action="store_true", help="Mark as staff user")

    def handle(self, *args, **opts):
        U = get_user_model()
        username = opts["username"].strip()
        password = opts["password"]
        email = (opts.get("email") or "").strip()
        is_super = bool(opts.get("superuser"))
        is_staff = bool(opts.get("staff"))

        defaults = {}
        if email:
            defaults["email"] = email
        user, created = U.objects.get_or_create(username=username, defaults=defaults)
        if not created and email and user.email != email:
            user.email = email
        user.set_password(password)
        if is_staff:
            user.is_staff = True
        if is_super:
            user.is_superuser = True
        user.save()
        self.stdout.write(self.style.SUCCESS(f"{'Created' if created else 'Updated'} user '{user.username}'"))
