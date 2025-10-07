from __future__ import annotations

from collections import defaultdict, Counter
from dataclasses import dataclass
from typing import Dict, List, Tuple
import random

# Support both package import (Django app) and direct script execution
try:
    from ..models import (
        Class,
        Staff,
        Subject,
        TeachingAssignment,
        CalendarTemplate,
        CalendarSlot,
    )
    from ..rules_config import DAYS
except ImportError:
    # When run as a standalone script, set up Django and import absolutely
    import os
    import sys
    from pathlib import Path

    # Add <repo>/backend to PYTHONPATH so that 'core' and 'school' are importable
    _FILE = Path(__file__).resolve()
    _BACKEND_DIR = _FILE.parents[2]  # .../backend
    if str(_BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(_BACKEND_DIR))

    # Configure Django settings and initialize
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
    try:
        import django  # type: ignore

        django.setup()
    except Exception:
        # If django.setup() fails we still raise the original ImportError
        raise

    # Now import using absolute package paths
    from school.models import (
        Class,
        Staff,
        Subject,
        TeachingAssignment,
        CalendarTemplate,
        CalendarSlot,
    )
    from school.rules_config import DAYS


@dataclass
class Placement:
    day: str
    slot: CalendarSlot
    subject: Subject
    teacher: Staff
    assignment_id: int


def _usable_slots_by_day(template: CalendarTemplate) -> Dict[str, List[CalendarSlot]]:
    """Expand 'ALL' day slots to each working day and keep only class blocks."""
    slots = list(template.slots.all().order_by("day", "order", "start_time"))
    by_day: Dict[str, List[CalendarSlot]] = {d: [] for d in DAYS}
    for s in slots:
        if (s.day or "").upper() == "ALL":
            for d in DAYS:
                if s.block == CalendarSlot.Block.CLASS:
                    by_day[d].append(s)
        else:
            if s.day in by_day and s.block == CalendarSlot.Block.CLASS:
                by_day[s.day].append(s)
    # sort inside day
    for d in by_day:
        by_day[d].sort(key=lambda x: (x.order, x.start_time, x.period_index))
    return by_day


def _teacher_blocked_first_period(teacher: Staff, slot: CalendarSlot) -> bool:
    # Relaxed per user request: no special blackout rules; only prevent conflicts
    return False


def generate_timetable(
    classroom: Class, template: CalendarTemplate
) -> Tuple[Dict[Tuple[str, int], Placement], List[Dict]]:
    """Greedy generator with essential hard rules and minimal preferences.

    Returns:
      schedule: map of (day, slot_index_in_day) -> Placement
      conflicts: list of conflict dicts for unmet hours
    """
    by_day = _usable_slots_by_day(template)

    # Build tasks: explode each TeachingAssignment into repeated tasks
    assignments = list(
        TeachingAssignment.objects.select_related("teacher", "subject")
        .filter(classroom=classroom)
        .all()
    )

    # Compute total weekly periods per subject for this class (across teachers)
    subject_weekly_count: Dict[int, int] = defaultdict(int)
    for ta in assignments:
        subject_weekly_count[ta.subject_id] += int(ta.no_classes_weekly or 0)

    tasks: List[TeachingAssignment] = []
    for ta in assignments:
        count = int(ta.no_classes_weekly or 0)
        tasks.extend([ta] * count)

    # Simple priority: subjects with larger weekly count first, then teacher id
    def prio(ta: TeachingAssignment) -> Tuple[int, int]:
        return (-int(ta.no_classes_weekly or 0), ta.teacher_id or 0)

    tasks.sort(key=prio)

    schedule: Dict[Tuple[str, int], Placement] = {}
    conflicts: List[Dict] = []

    # Occupancy trackers
    teacher_busy: Dict[int, Dict[str, set]] = defaultdict(lambda: {d: set() for d in DAYS})
    class_busy: Dict[str, set] = {d: set() for d in DAYS}
    class_daily_count: Dict[str, int] = {d: 0 for d in DAYS}
    # Subject/day usage for this class: (subject_id, day) -> count
    subject_day_count: Dict[Tuple[int, str], int] = defaultdict(int)
    # Track per-teacher usage count of period indices ("1".."7") to ensure fairness
    teacher_period_use: Dict[int, Counter] = defaultdict(Counter)

    # Map day->slot list index for adjacency checks
    idx_map: Dict[str, Dict[int, int]] = {d: {} for d in DAYS}
    for d in DAYS:
        for i, s in enumerate(by_day[d]):
            idx_map[d][s.id] = i

    # Prepare a rotating tie-breaker to avoid Sun/Mon bias when counts are equal
    day_index = {d: idx for idx, d in enumerate(DAYS)}
    rr_shift = 0

    # Try to place each task
    unplaced_tasks: List[TeachingAssignment] = []
    for ta in tasks:
        placed = False
        # fair-day scan with rotation tie-breaker: prefer days with fewer lessons for this class
        # and this teacher; when equal, rotate the preferred day across tasks to spread across week
        day_order = sorted(
            DAYS,
            key=lambda d: (
                class_daily_count[d],  # spread class load across the week for the class
                len(teacher_busy[ta.teacher_id][d]),  # spread teacher load across days
                (day_index[d] - rr_shift) % len(DAYS),  # rotate tie-breaker
            ),
        )
        for d in day_order:
            slots = by_day[d]
            # Build candidate slots filtered by no-conflict,
            # then sort by fairness (least-used period for this teacher)
            candidates = []
            for i, s in enumerate(slots):
                key = (d, i)
                if key in schedule:
                    continue
                # Only hard rule: no conflicts for teacher or class at this time index
                if i in teacher_busy[ta.teacher_id][d]:
                    continue
                if i in class_busy[d]:
                    continue
                # Subject/day repetition rule: by default disallow repeating same
                # subject in the same day.
                subj_id = ta.subject_id
                weekly_total = subject_weekly_count.get(subj_id, int(ta.no_classes_weekly or 0))
                per_day_cap = 1 if weekly_total <= 5 else 2
                if subject_day_count[(subj_id, d)] >= per_day_cap:
                    continue
                # fairness score: how many times this teacher has taught at this period index so far
                period_key = str(s.period_index)
                fairness_score = teacher_period_use[ta.teacher_id][period_key]
                candidates.append((fairness_score, random.random(), i, s))
            # Prefer least-used periods; break ties randomly
            for _, __, i, s in sorted(candidates):
                key = (d, i)
                # place
                schedule[key] = Placement(
                    day=d,
                    slot=s,
                    subject=ta.subject,
                    teacher=ta.teacher,
                    assignment_id=ta.id,
                )
                teacher_busy[ta.teacher_id][d].add(i)
                class_busy[d].add(i)
                class_daily_count[d] += 1
                subject_day_count[(ta.subject_id, d)] += 1
                # record period usage for teacher fairness across 1..7
                teacher_period_use[ta.teacher_id][str(s.period_index)] += 1
                placed = True
                # advance rotation to vary next task tie-breakers
                rr_shift = (rr_shift + 1) % len(DAYS)
                break
            if placed:
                break
        if not placed:
            unplaced_tasks.append(ta)

    # Second pass: place any remaining tasks by ignoring fairness and just avoiding conflicts
    if unplaced_tasks:
        for ta in unplaced_tasks:
            placed2 = False
            day_list = list(DAYS)
            random.shuffle(day_list)
            for d in day_list:
                slots = by_day[d]
                idxs = list(range(len(slots)))
                random.shuffle(idxs)
                for i in idxs:
                    key = (d, i)
                    if key in schedule:
                        continue
                    if i in teacher_busy[ta.teacher_id][d]:
                        continue
                    if i in class_busy[d]:
                        continue
                    # Subject/day repetition rule in second pass as well
                    subj_id = ta.subject_id
                    weekly_total = subject_weekly_count.get(subj_id, int(ta.no_classes_weekly or 0))
                    per_day_cap = 1 if weekly_total <= 5 else 2
                    if subject_day_count[(subj_id, d)] >= per_day_cap:
                        continue
                    s = slots[i]
                    schedule[key] = Placement(
                        day=d,
                        slot=s,
                        subject=ta.subject,
                        teacher=ta.teacher,
                        assignment_id=ta.id,
                    )
                    teacher_busy[ta.teacher_id][d].add(i)
                    class_busy[d].add(i)
                    class_daily_count[d] += 1
                    subject_day_count[(ta.subject_id, d)] += 1
                    teacher_period_use[ta.teacher_id][str(s.period_index)] += 1
                    placed2 = True
                    break
                if placed2:
                    break
            if not placed2:
                conflicts.append(
                    {
                        "class": classroom.name,
                        "subject": ta.subject.name_ar,
                        "teacher": ta.teacher.full_name,
                        "reason": "no_slot_available_after_second_pass",
                    }
                )
    return schedule, conflicts
