"""
Rules configuration for timetable generation and validation.

This module encodes the constraints confirmed by the user and will be
used by the future timetable generator. It is intentionally framework-
agnostic (pure Python constants and helpers) so it can be imported from
views, services, or commands.
"""

from __future__ import annotations

from typing import Dict, List, Set

# Working days order used across the app
DAYS: List[str] = ["Sun", "Mon", "Tue", "Wed", "Thu"]

# Preparatory stage definition (confirmed): Grades 7–9 inclusive
PREPARATORY_GRADES: Set[int] = {7, 8, 9}

# ---- HARD CONSTRAINTS ----
HARD: Dict = {
    # Maximum consecutive lessons a teacher can teach (strict)
    "teacher_max_consecutive": 2,
    # Maximum lessons per day for a class. Default 7, with an exception for
    # preparatory (grades 7–9) on Thursday where the max is 6.
    "class_daily_max": {
        "default": 7,
        # exceptions are evaluated by helpers in this module (see: daily_cap_for_class)
        "exceptions": [
            {"grades_in": list(PREPARATORY_GRADES), "day": "Thu", "max": 6},
        ],
    },
    # Only these block types can host a class session
    "block_allow": ["class"],
    # Teacher day/period blackouts by teacher full name (Arabic) — user said:
    # "كل الايام لا يعطي اولى" for the named teacher.
    # We keep it as names to avoid coupling to specific IDs.
    "teacher_blackouts": [
        {
            "teacher_name": "سفيان احمد محمد مسيف",
            "days": DAYS,  # all working days
            "periods": ["1"],  # cannot teach period 1
        }
    ],
}

# ---- SOFT CONSTRAINTS (preferences) ----
SOFT: Dict = {
    # Prioritize science subjects in morning periods (1–3)
    "science_morning_priority": {
        "prefer_periods": ["1", "2", "3"],
        "weight": 3,
        # Subject matching is done via Arabic normalization in the app; we
        # provide a generous list of canonical names and keywords.
        "subjects_canonical": [
            "رياضيات",
            "علوم",
            "احياء",
            "فيزياء",
            "كيمياء",
        ],
        # Additional keywords to catch variants (normalized Arabic, tashkeel removed)
        "keywords": [
            "رياضيات",
            "علم",
            "احياء",
            "فيزيا",
            "كيميا",
        ],
    },
    # After a practical subject for the class, prefer a literary/theory one (alternation)
    "alternate_practical_then_literary": {
        "weight": 1,
        # Practical keywords to detect practical sessions
        "practical_keywords": [
            "عملي",
            "مختبر",
            "تطبيق",
        ],
    },
    # Spread occurrences of the same subject across the week and avoid adjacency
    "spread_across_week": {
        "no_adjacent_duplicates_in_same_day": True,
        "weight": 2,
    },
    # Aim for fairness for teachers on first and last periods across the week
    "teacher_first_last_fairness": {
        "periods": ["1", "7"],
        "weight": 1,
    },
    # Double-period preference for selected subjects (if slots allow)
    "double_period_subjects": {
        "list": [
            "تكنولجيا",
            "تكنولوجيا المعلومات",
            "عمل الحاسب",
            "فنون بصرية",
        ],
        "weight": 2,
    },
    # Weekly distribution patterns by total weekly lessons per subject
    # - 5/week: exactly 1 per day (Sun–Thu)
    # - 6/week: one duplicate day, but the two should not be adjacent in the same day
    # - 10/week: prefer one morning + one later slot each day when possible
    "weekly_distribution": {
        "five_per_week": {
            "rule": "one_per_day",
        },
        "six_per_week": {
            "rule": "one_duplicate_day_non_adjacent",
        },
        "ten_per_week": {
            "rule": "two_per_day_morning_plus_later",
            "morning_periods": ["1", "2", "3"],
            # later periods are inferred as non-morning class blocks
        },
    },
}

# ---- Helper APIs (pure functions) ----


def daily_cap_for_class(grade: int, day: str) -> int:
    """Return the maximum allowed lessons for a given class grade on a given day.

    Defaults to HARD["class_daily_max"]["default"], with overrides applied.
    """
    base = HARD["class_daily_max"]["default"]
    for exc in HARD["class_daily_max"].get("exceptions", []):
        if day == exc.get("day") and grade in set(exc.get("grades_in", [])):
            return int(exc.get("max", base))
    return base


def is_science_subject(name_ar_normalized: str) -> bool:
    """Heuristic match for science subjects using normalized Arabic name.

    A subject is considered science if it matches any canonical name or contains
    one of the science keywords after normalization.
    """
    s = name_ar_normalized or ""
    if not s:
        return False
    canon = set(
        SOFT["science_morning_priority"]["subjects_canonical"]
    )  # already normalized in repo
    if s in canon:
        return True
    for kw in SOFT["science_morning_priority"]["keywords"]:
        if kw and kw in s:
            return True
    return False


def teacher_is_blocked_first_period(teacher_full_name: str) -> bool:
    """True if the teacher has a blanket block on period 1 for all days."""
    name = (teacher_full_name or "").strip()
    for blk in HARD.get("teacher_blackouts", []):
        if blk.get("teacher_name") == name:
            periods = set(blk.get("periods", []))
            if "1" in periods:
                return True
    return False
