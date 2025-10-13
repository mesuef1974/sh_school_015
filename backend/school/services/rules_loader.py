from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import yaml


def load_rules() -> Dict[str, Any]:
    """
    Load timetable rules from backend/school/timetable_rules.yaml if present.
    Returns an empty dict on any error. This is intentionally permissive to keep
    the generator decoupled from rules until we wire constraints gradually.
    """
    try:
        rules_path = Path(__file__).resolve().parents[1] / "timetable_rules.yaml"
        if not rules_path.exists():
            return {}
        text = rules_path.read_text(encoding="utf-8")
        if not text.strip():
            return {}
        data = yaml.safe_load(text)
        if isinstance(data, dict):
            return data
        return {}
    except Exception:
        return {}


def dump_rules_preview(rules: Dict[str, Any]) -> str:
    try:
        return json.dumps(rules, ensure_ascii=False, indent=2)
    except Exception:
        return "{}"
