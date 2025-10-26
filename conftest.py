import os

# Respect existing DJANGO_SETTINGS_MODULE (e.g., CI sets core.settings_test). Default to lightweight test settings.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings_test")

# Ensure backend package is importable regardless of CWD
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
backend = root / "backend"
if str(backend) not in sys.path:
    sys.path.insert(0, str(backend))

# Defer django.setup() to pytest-django; it calls setup itself when needed
