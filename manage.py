#!/usr/bin/env python
"""
Root-level Django manage.py shim

Allows running Django management commands from the project root:
  python manage.py migrate
  python manage.py sync_rbac --dry-run

It boots Django using backend/core.settings and ensures the backend/ path is on sys.path.
This does not replace backend/manage.py (if present); it simply forwards commands.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / 'backend'

# Ensure backend package is importable (so 'core.settings' can be found)
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Default to the project's settings module if not already set
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

try:
    from django.core.management import execute_from_command_line
except Exception as e:
    sys.stderr.write(
        'Error: Django is not installed or failed to import.\n'
        f'Details: {e}\n'
    )
    sys.exit(1)

if __name__ == '__main__':
    execute_from_command_line(sys.argv)