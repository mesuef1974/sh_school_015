import os
import django

# Ensure Django settings are correctly set for tests regardless of environment quirks
# Force override to avoid accidental trailing spaces or inherited invalid values
os.environ["DJANGO_SETTINGS_MODULE"] = "core.settings"
# Make sure backend is on PYTHONPATH when running tests in various environments
import sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
backend = root / "backend"
if str(backend) not in sys.path:
    sys.path.insert(0, str(backend))

django.setup()