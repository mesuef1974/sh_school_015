# Lightweight wrapper to allow running:
# python ensure_superuser.py [--username ... --email ... --password ...]
# It forwards CLI args to the Django management command `ensure_superuser`.

from __future__ import annotations

import sys

from django.core.management import execute_from_command_line


def main() -> None:
    # Build argv for Django as if we're calling: manage.py ensure_superuser <args>
    argv = ["manage.py", "ensure_superuser", *sys.argv[1:]]
    execute_from_command_line(argv)


if __name__ == "__main__":
    main()
