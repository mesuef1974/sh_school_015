import os
# Force correct Django settings very early for pytest-django
os.environ["DJANGO_SETTINGS_MODULE"] = "core.settings"

# Ensure backend package is importable regardless of CWD
import sys
from pathlib import Path
root = Path(__file__).resolve().parent
backend = root / "backend"
if str(backend) not in sys.path:
    sys.path.insert(0, str(backend))

# Defer django.setup() to pytest-django; it calls setup itself when needed