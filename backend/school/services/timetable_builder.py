from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple, Set
from collections import defaultdict

from django.db import transaction

from school.models import (
    TimetableEntry,
    TeachingAssignment,
    Term,
)
from .rules_loader import load_rules


@dataclass
class BuildResult:
    created: int
    replaced_existing: int


class TimetableBuilder:
    """
    Minimal heuristic timetable builder.

    Goals for this initial implementation:
    - Fill TimetableEntry for the current term only.
    - Respect hard constraints:
      * No class has more than one lesson in the same (day, period).
      * No teacher has more than one lesson in the same (day, period).
      * For each (class, subject) avoid placing more than one lesson per day by default.
    - Spread lessons of an assignment across days as evenly as possible.

    Notes:
    - Days are 1..5 (Sun..Thu). Periods considered are 1..7.
    - This version does not yet integrate PeriodTemplate/TemplateSlot; that will be
      layered in next iterations to honor Thursday special timings and wings.
    """

    DAYS: List[int] = [1, 2, 3, 4, 5]
    PERIODS: List[int] = [1, 2, 3, 4, 5, 6, 7]

    def __init__(self, term: Term) -> None:
        self.term = term
        self.rules = load_rules()

    def build_entries(self) -> List[TimetableEntry]:
        # Load assignments
        assignments = list(
            TeachingAssignment.objects.select_related("teacher", "classroom", "subject")
        )
        # Sort by descending weekly load to place hardest first
        assignments.sort(key=lambda a: int(a.no_classes_weekly), reverse=True)

        # Occupancy sets
        class_busy: Set[Tuple[int, int, int]] = set()  # (class_id, day, period)
        teacher_busy: Set[Tuple[int, int, int]] = set()  # (teacher_id, day, period)
        class_subject_on_day: Set[Tuple[int, int, int]] = set()  # (class_id, subject_id, day)

        # Existing timetable (to avoid duplicates if re-running): we will replace term entirely
        # Note: if reporting is needed later, query count on demand.
        # TimetableEntry.objects.filter(term=self.term).count()

        entries: List[TimetableEntry] = []

        # Basic day-cycling cursor per assignment to spread across days
        day_cursors: Dict[Tuple[int, int, int], int] = {}

        # Rules: subject multiple-per-day threshold from YAML (default=5)
        subject_rules = (
            self.rules.get("constraints", {}).get("subject", {})
            if isinstance(self.rules, dict)
            else {}
        )
        try:
            multi_threshold = int(subject_rules.get("allow_multiple_per_day_if_more_than", 5))
        except Exception:
            multi_threshold = 5

        # Teachers exempt from the one-per-day rule (may repeat more than once): from YAML preferences.teacher_free_days keys
        prefs = self.rules.get("preferences", {}) if isinstance(self.rules, dict) else {}
        exempt_teacher_names = set()
        try:
            exempt_teacher_names = set((prefs.get("teacher_free_days", {}) or {}).keys())
        except Exception:
            exempt_teacher_names = set()

        # Normalize for robust matching (some YAML names may be partial)
        def _norm(s: str) -> str:
            return (s or "").strip().lower()

        exempt_norm = {_norm(n) for n in exempt_teacher_names}
        # Add targeted teachers for aggressive filling (partial names)
        targeted_tokens = {
            "سامر جديع",
            "عثمان فاروسي",
            "ناصر الهاجرى",
            "ناصر الهاجري",
            "وجدي يوسفي",
            "وجدي اليوسفي",
        }
        exempt_norm |= {_norm(t) for t in targeted_tokens}

        def is_exempt_teacher(full_name: str) -> bool:
            fn = _norm(full_name)
            if not fn:
                return False
            return any((token and token in fn) for token in exempt_norm)

        # Allow one same-day double (breaking one-per-day) once per assignment (teacher, classroom, subject)
        teacher_double_remaining: Dict[Tuple[int, int, int], int] = defaultdict(lambda: 1)

        # Allow adjacent-pair preference per teacher per week (exempt teachers unlimited)
        teacher_adjacency_remaining: Dict[int, int] = defaultdict(lambda: 2)

        # Track placed periods per (class, subject, day) to support adjacency choice
        placed_by_csd: Dict[Tuple[int, int, int], List[int]] = defaultdict(list)

        for a in assignments:
            remaining = int(a.no_classes_weekly)
            if remaining <= 0:
                continue
            key = (a.classroom_id, a.subject_id, a.teacher_id)
            start_day_index = day_cursors.get(key, 0) % len(self.DAYS)

            # Try to place 'remaining' lessons across the week
            attempts = 0
            placed_for_this_assignment = 0
            while remaining > 0 and attempts < 300:
                attempts += 1
                # Pick next day in a round-robin manner
                day = self.DAYS[(start_day_index + attempts - 1) % len(self.DAYS)]

                # Enforce one (class, subject) per day by default, with two relaxations:
                # 1) If weekly load for this assignment > multi_threshold (e.g., >5), allow two in a day.
                # 2) Otherwise, allow exactly one exception per TEACHER globally (consume teacher_double_remaining).
                existing_same_day = (
                    a.classroom_id,
                    a.subject_id,
                    day,
                ) in class_subject_on_day
                allow_same_day_via_threshold = int(a.no_classes_weekly) > multi_threshold
                allow_same_day_via_teacher = False
                if existing_same_day and not allow_same_day_via_threshold:
                    if a.teacher.full_name in exempt_teacher_names:
                        allow_same_day_via_teacher = True
                    elif teacher_double_remaining[(a.teacher_id, a.classroom_id, a.subject_id)] > 0:
                        allow_same_day_via_teacher = True
                    else:
                        # try next attempt (next day)
                        continue

                # Iterate over periods and pick first feasible (prefer adjacency if this is a same-day second)
                chosen_period = None
                # Adjacency preference
                if (
                    existing_same_day
                    and (allow_same_day_via_threshold or allow_same_day_via_teacher)
                    and teacher_adjacency_remaining[a.teacher_id] > 0
                ):
                    existing_periods = placed_by_csd.get((a.classroom_id, a.subject_id, day), [])
                    if existing_periods:
                        # Try adjacent slots around any existing period (usually only one exists here)
                        for ep in existing_periods:
                            for cand in (ep - 1, ep + 1):
                                if (
                                    cand in self.PERIODS
                                    and (a.classroom_id, day, cand) not in class_busy
                                    and (a.teacher_id, day, cand) not in teacher_busy
                                ):
                                    chosen_period = cand
                                    break
                            if chosen_period is not None:
                                break
                # Fallback to first-free search
                if chosen_period is None:
                    for p in self.PERIODS:
                        if (a.classroom_id, day, p) in class_busy:
                            continue
                        if (a.teacher_id, day, p) in teacher_busy:
                            continue
                        chosen_period = p
                        break

                if chosen_period is None:
                    # Could not place in this day; try another day
                    continue

                # Reserve and create entry
                class_busy.add((a.classroom_id, day, chosen_period))
                teacher_busy.add((a.teacher_id, day, chosen_period))
                class_subject_on_day.add((a.classroom_id, a.subject_id, day))

                # If we used the teacher-level exception (and not the threshold relaxation), consume it now
                if (
                    existing_same_day
                    and allow_same_day_via_teacher
                    and not allow_same_day_via_threshold
                ):
                    teacher_double_remaining[(a.teacher_id, a.classroom_id, a.subject_id)] -= 1

                entries.append(
                    TimetableEntry(
                        classroom_id=a.classroom_id,
                        subject_id=a.subject_id,
                        teacher_id=a.teacher_id,
                        day_of_week=day,
                        period_number=chosen_period,
                        term=self.term,
                    )
                )
                placed_for_this_assignment += 1
                remaining -= 1

            # advance cursor for next pass to balance
            day_cursors[key] = start_day_index + placed_for_this_assignment

        # Second pass: attempt to fill remaining deficits by allowing a controlled same-day double
        # - Respect class/teacher no-conflict
        # - Allow at most 2 lessons of the same (class, subject) per day (unless threshold allows more)
        # - Budget: one extra double per TEACHER across all assignments per week
        teacher_global_double_budget: Dict[int, int] = defaultdict(lambda: 3)
        # Build a quick map of expected loads
        expected_map: Dict[Tuple[int, int, int], int] = {}
        for a in assignments:
            expected_map[(a.classroom_id, a.subject_id, a.teacher_id)] = int(a.no_classes_weekly)
        # Count placed so far per assignment
        placed_count: Dict[Tuple[int, int, int], int] = defaultdict(int)
        for e in entries:
            placed_count[(e.classroom_id, e.subject_id, e.teacher_id)] += 1
        # Try to place leftovers with relaxed rule
        for a in assignments:
            key_asg = (a.classroom_id, a.subject_id, a.teacher_id)
            deficit = expected_map[key_asg] - placed_count.get(key_asg, 0)
            if deficit <= 0:
                continue
            # Flex subjects allow higher per-day cap and budgetless second slot
            subj_name = getattr(a.subject, "name_ar", "") or ""
            subj_norm = subj_name.strip().lower()
            flex_tokens = {
                "تربية بدنية",
                "التربية البدنية",
                "مهارات حياتية",
                "المهارات الحياتية",
                "تكنولوجيا",
                "علوم الحاسب",
                "ادارة اعمال",
                "إدارة أعمال",
            }
            is_flexible_subject = any(tok in subj_norm for tok in flex_tokens)
            is_ex = is_exempt_teacher(a.teacher.full_name)
            for _ in range(deficit):
                placed = False
                # Search days then periods; prefer adjacency if there is already a slot this day
                for day in self.DAYS:
                    # Check per-day count for this (class, subject)
                    per_day_periods = placed_by_csd.get((a.classroom_id, a.subject_id, day), [])
                    per_day_count = len(per_day_periods)
                    existing_same_day = per_day_count > 0
                    allow_same_day_via_threshold = int(a.no_classes_weekly) > multi_threshold
                    # Determine per-day cap
                    per_day_cap = 4 if (is_ex or is_flexible_subject) else 2
                    # Enforce cap: if not threshold, allow up to per_day_cap per day, and relax budget for flex/exempt
                    if existing_same_day and not allow_same_day_via_threshold:
                        if per_day_count >= per_day_cap:
                            continue
                        if not (is_ex or is_flexible_subject):
                            if teacher_global_double_budget[a.teacher_id] <= 0:
                                continue
                    # Try adjacency first
                    candidate_periods: List[int] = []
                    if per_day_periods:
                        for ep in per_day_periods:
                            for cand in (ep - 1, ep + 1):
                                if cand in self.PERIODS:
                                    candidate_periods.append(cand)
                    # Fallback list: all periods
                    candidate_periods += [p for p in self.PERIODS if p not in candidate_periods]
                    # If Life Skills, prefer late periods (break fairness for 6th/7th as requested)
                    if "مهارات حياتية" in subj_norm:
                        late_first = [p for p in [7, 6, 5, 4, 3, 2, 1] if p in candidate_periods]
                        candidate_periods = late_first
                    for p in candidate_periods:
                        if (a.classroom_id, day, p) in class_busy:
                            continue
                        if (a.teacher_id, day, p) in teacher_busy:
                            continue
                        # Place
                        class_busy.add((a.classroom_id, day, p))
                        teacher_busy.add((a.teacher_id, day, p))
                        class_subject_on_day.add((a.classroom_id, a.subject_id, day))
                        placed_by_csd[(a.classroom_id, a.subject_id, day)].append(p)
                        entries.append(
                            TimetableEntry(
                                classroom_id=a.classroom_id,
                                subject_id=a.subject_id,
                                teacher_id=a.teacher_id,
                                day_of_week=day,
                                period_number=p,
                                term=self.term,
                            )
                        )
                        placed_count[key_asg] += 1
                        if (
                            existing_same_day
                            and not allow_same_day_via_threshold
                            and not (is_ex or is_flexible_subject)
                        ):
                            teacher_global_double_budget[a.teacher_id] -= 1
                        placed = True
                        break
                    if placed:
                        break
        # Third pass: targeted swap fixer to resolve hard conflicts
        # Try limited local swaps to free a slot for remaining deficits
        # Recompute deficits
        placed_count = defaultdict(int)
        for e in entries:
            placed_count[(e.classroom_id, e.subject_id, e.teacher_id)] += 1
        remaining_list: List[Tuple[TeachingAssignment, int]] = []
        for a in assignments:
            need = expected_map[(a.classroom_id, a.subject_id, a.teacher_id)] - placed_count.get(
                (a.classroom_id, a.subject_id, a.teacher_id), 0
            )
            if need > 0:
                remaining_list.append((a, need))
        # Fast index of entries by (day, period)
        slots_map: Dict[Tuple[int, int], List[TimetableEntry]] = defaultdict(list)
        for e in entries:
            slots_map[(e.day_of_week, e.period_number)].append(e)

        def can_place(a: TeachingAssignment, day: int, p: int) -> bool:
            return (a.classroom_id, day, p) not in class_busy and (
                a.teacher_id,
                day,
                p,
            ) not in teacher_busy

        swap_attempts = 0
        MAX_SWAPS = 800
        for a, need in remaining_list:
            if swap_attempts >= MAX_SWAPS:
                break
            for _ in range(need):
                done = False
                # Prefer flexible subjects and exempt teachers
                subj_name = (getattr(a.subject, "name_ar", "") or "").strip().lower()
                is_ex = is_exempt_teacher(a.teacher.full_name)
                flex_tokens = {
                    "تربية بدنية",
                    "التربية البدنية",
                    "مهارات حياتية",
                    "المهارات الحياتية",
                    "تكنولوجيا",
                    "علوم الحاسب",
                }
                is_flexible_subject = any(tok in subj_name for tok in flex_tokens)
                for day in self.DAYS:
                    if done:
                        break
                    # If direct place possible, do it
                    placed_direct = False
                    for p in self.PERIODS:
                        if can_place(a, day, p):
                            # place directly
                            class_busy.add((a.classroom_id, day, p))
                            teacher_busy.add((a.teacher_id, day, p))
                            class_subject_on_day.add((a.classroom_id, a.subject_id, day))
                            placed_by_csd[(a.classroom_id, a.subject_id, day)].append(p)
                            new_e = TimetableEntry(
                                classroom_id=a.classroom_id,
                                subject_id=a.subject_id,
                                teacher_id=a.teacher_id,
                                day_of_week=day,
                                period_number=p,
                                term=self.term,
                            )
                            entries.append(new_e)
                            slots_map[(day, p)].append(new_e)
                            placed_count[(a.classroom_id, a.subject_id, a.teacher_id)] += 1
                            done = True
                            placed_direct = True
                            break
                    if placed_direct:
                        break
                    # Try swap: look at each period in day, try to move one occupant elsewhere to free it
                    for p in self.PERIODS:
                        if done or swap_attempts >= MAX_SWAPS:
                            break
                        # If same class/teacher already busy here, consider swapping that entry
                        candidates = list(slots_map.get((day, p), []))
                        for e2 in candidates:
                            # Don't swap with exactly same assignment (no benefit)
                            if (
                                e2.classroom_id == a.classroom_id
                                and e2.teacher_id == a.teacher_id
                                and e2.subject_id == a.subject_id
                            ):
                                continue
                            # Try to find alternative slot p2/(day2) for e2 — same day first, then other days
                            moved = False
                            for day2 in [day] + [d for d in self.DAYS if d != day]:
                                if moved:
                                    break
                                for p2 in self.PERIODS:
                                    if day2 == e2.day_of_week and p2 == e2.period_number:
                                        continue
                                    # Temporarily free e2's current occupancy
                                    class_busy.discard(
                                        (
                                            e2.classroom_id,
                                            e2.day_of_week,
                                            e2.period_number,
                                        )
                                    )
                                    teacher_busy.discard(
                                        (
                                            e2.teacher_id,
                                            e2.day_of_week,
                                            e2.period_number,
                                        )
                                    )
                                    # Check if e2 can move to (day2, p2)
                                    if (
                                        e2.classroom_id,
                                        day2,
                                        p2,
                                    ) not in class_busy and (
                                        e2.teacher_id,
                                        day2,
                                        p2,
                                    ) not in teacher_busy:
                                        # Perform swap: move e2 to (day2,p2), place a at (day,p)
                                        e2_old_day, e2_old_p = (
                                            e2.day_of_week,
                                            e2.period_number,
                                        )
                                        e2.day_of_week = day2
                                        e2.period_number = p2
                                        class_busy.add((e2.classroom_id, day2, p2))
                                        teacher_busy.add((e2.teacher_id, day2, p2))
                                        # Update slots map
                                        slots_map[(e2_old_day, e2_old_p)].remove(e2)
                                        slots_map[(day2, p2)].append(e2)
                                        # Now free (day,p) is available; place a
                                        class_busy.add((a.classroom_id, day, p))
                                        teacher_busy.add((a.teacher_id, day, p))
                                        class_subject_on_day.add(
                                            (a.classroom_id, a.subject_id, day)
                                        )
                                        placed_by_csd[(a.classroom_id, a.subject_id, day)].append(p)
                                        new_e = TimetableEntry(
                                            classroom_id=a.classroom_id,
                                            subject_id=a.subject_id,
                                            teacher_id=a.teacher_id,
                                            day_of_week=day,
                                            period_number=p,
                                            term=self.term,
                                        )
                                        entries.append(new_e)
                                        slots_map[(day, p)].append(new_e)
                                        placed_count[
                                            (a.classroom_id, a.subject_id, a.teacher_id)
                                        ] += 1
                                        swap_attempts += 1
                                        done = True
                                        moved = True
                                        break
                                    # Restore e2 occupancy if not moved this attempt
                                    class_busy.add(
                                        (
                                            e2.classroom_id,
                                            e2.day_of_week,
                                            e2.period_number,
                                        )
                                    )
                                    teacher_busy.add(
                                        (
                                            e2.teacher_id,
                                            e2.day_of_week,
                                            e2.period_number,
                                        )
                                    )
                            if moved:
                                break
                # End per-need loop
        return entries

    @transaction.atomic
    def persist(self, entries: List[TimetableEntry]) -> BuildResult:
        # Replace current term timetable
        qs = TimetableEntry.objects.filter(term=self.term)
        existing = qs.count()
        qs.delete()
        # Deduplicate entries on (classroom, day, period) to satisfy unique_together
        deduped: List[TimetableEntry] = []
        seen_keys: Set[Tuple[int, int, int]] = set()
        for e in entries:
            key = (e.classroom_id, e.day_of_week, e.period_number)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            deduped.append(e)
        if deduped:
            TimetableEntry.objects.bulk_create(deduped, batch_size=2000)
        return BuildResult(created=len(deduped), replaced_existing=existing)
