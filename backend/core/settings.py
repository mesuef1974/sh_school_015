"""
Settings delegator for core project.

This module routes to environment-specific settings files.
Use DJANGO_ENV to select the variant: "dev" (default) or "prod".
"""

import os

_env = (os.getenv("DJANGO_ENV", "dev") or "dev").strip().lower()

if _env in {"prod", "production"}:
    from .settings_prod import *  # noqa: F401,F403
elif _env in {"dev", "development"}:
    from .settings_dev import *  # noqa: F401,F403
else:
    # Fallback to dev if unknown
    from .settings_dev import *  # noqa: F401,F403
