from __future__ import annotations

import logging
import os
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.management import call_command
from django.db.models.signals import post_migrate
from django.dispatch import receiver

logger = logging.getLogger(__name__)


def _is_truthy(val: str | None) -> bool:
    if val is None:
        return True  # default: enabled
    return val.strip().lower() not in {"0", "false", "no", "off"}


@receiver(post_migrate)
def autoload_catalog_after_migrate(sender, **kwargs):  # pragma: no cover - init-time side effect
    """Auto-load the discipline catalog once after migrations if tables are empty.

    Controlled by env var DISCIPLINE_AUTOLOAD (default: true). Safe no-op if the
    JSON file is missing or if records already exist. Never raises to avoid
    breaking migrations or dev startup.
    """
    try:
        # Only run when discipline app is ready and the discipline models exist
        if not apps.is_installed("discipline"):
            return

        if not _is_truthy(os.getenv("DISCIPLINE_AUTOLOAD")):
            logger.info("Discipline autoload disabled via DISCIPLINE_AUTOLOAD env var.")
            return

        BehaviorLevel = apps.get_model("discipline", "BehaviorLevel")
        Violation = apps.get_model("discipline", "Violation")
        if BehaviorLevel.objects.exists() or Violation.objects.exists():
            return  # already loaded

        # Determine default JSON path relative to repo root (BASE_DIR points to backend/)
        repo_root = Path(settings.BASE_DIR).parent
        json_path = repo_root / "DOC" / "school_DATA" / "violations_detailed.json"
        if not json_path.exists():
            logger.warning("Discipline autoload skipped: JSON not found at %s", json_path)
            return

        logger.info("Discipline autoload: loading catalog from %s", json_path)
        call_command("load_discipline_catalog", file=str(json_path))
    except Exception as e:  # noqa: BLE001
        # Never crash migrations due to optional autoload
        logger.warning("Discipline autoload failed: %s", e)
