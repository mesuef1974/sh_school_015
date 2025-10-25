# Ensure Django test settings are always correct and robust to stray whitespace
import os
import sys
from pathlib import Path

val = os.environ.get("DJANGO_SETTINGS_MODULE", "").strip()
if val not in ("core.settings", "core.settings_dev", "core.settings_test"):
    # Force to main settings if unset or malformed
    os.environ["DJANGO_SETTINGS_MODULE"] = "core.settings"
else:
    # Normalize to remove any trailing/leading spaces
    os.environ["DJANGO_SETTINGS_MODULE"] = val

# Ensure backend on sys.path early so `core` package is importable
root = Path(__file__).resolve().parent
backend = root / "backend"
if str(backend) not in sys.path:
    sys.path.insert(0, str(backend))