from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from django.apps import apps

# Models will be resolved lazily inside the command after Django apps are ready.
# This avoids AppRegistryNotReady when this module is imported or executed directly.

# Try to use tabula-py for table extraction
try:
    import tabula  # type: ignore
except Exception:  # pragma: no cover
    tabula = None

# Arabic digits translation
AR_NUMS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

# Mapping Arabic day labels to English codes used in DB
DAY_AR_TO_EN = {
    "الاحد": "Sun",
    "الأحد": "Sun",
    "احد": "Sun",
    "أحد": "Sun",
    "الاثنين": "Mon",
    "الإثنين": "Mon",
    "اثنين": "Mon",
    "الثلاثاء": "Tue",
    "ثلاثاء": "Tue",
    "الثلاثا": "Tue",
    "الثلاثا ء": "Tue",
    "الاربعاء": "Wed",
    "الأربعاء": "Wed",
    "اربعاء": "Wed",
    "الخميس": "Thu",
    "خميس": "Thu",
}


def norm_ar(s: str) -> str:
    if s is None:
        return ""
    s = str(s)
    s = s.strip()
    # remove diacritics
    s = re.sub(r"[\u064B-\u065F\u0670]", "", s)
    # normalize spaces
    s = re.sub(r"\s+", " ", s)
    return s


def try_read_pdf_tables(pdf_path: Path):
    """
    Read tables from a PDF and return a list of pandas.DataFrame (dtype=str).
    Strategy:
    1) Try tabula-py (Java) if available and working.
    2) Fallback to pure-Python pdfplumber to avoid Java dependency.
    """
    # First, try tabula if import succeeded
    if tabula is not None:
        try:
            tables = tabula.read_pdf(
                str(pdf_path),
                pages="all",
                multiple_tables=True,
                lattice=True,
                pandas_options={"dtype": str},
            )
            if tables:
                return tables
        except Exception:
            # Swallow and fallback to pdfplumber below
            pass

    # Fallback: pdfplumber (pure Python)
    try:
        import pandas as pd  # type: ignore
    except Exception as e:  # pragma: no cover
        raise CommandError(
            "Neither tabula-py worked nor pandas is available for the fallback. "
            "Install pandas (pip install pandas)."
        ) from e

    try:
        import pdfplumber  # type: ignore
    except Exception as e:  # pragma: no cover
        raise CommandError(
            "Java/tabula-py is unavailable and pdfplumber is not installed. "
            "Install with: pip install pdfplumber"
        ) from e

    dfs = []
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page in pdf.pages:
                # Try to extract tables. pdfplumber returns a list of tables, each as list of rows
                # Use table_settings to be a bit more permissive for Arabic RTL docs.
                tables = (
                    page.extract_tables(
                        table_settings={
                            "horizontal_strategy": "lines",
                            "vertical_strategy": "lines",
                            "snap_tolerance": 3,
                            "intersection_tolerance": 3,
                            "edge_min_length": 3,
                            "text_tolerance": 2,
                        }
                    )
                    or []
                )
                if not tables:
                    # Retry with stream-like settings (no explicit lines)
                    tables = (
                        page.extract_tables(
                            table_settings={
                                "horizontal_strategy": "text",
                                "vertical_strategy": "text",
                                "text_tolerance": 2,
                            }
                        )
                        or []
                    )
                page_text = page.extract_text() or ""
                for tbl in tables:
                    if not tbl or all(
                        (cell is None or str(cell).strip() == "")
                        for row in tbl
                        for cell in row
                    ):
                        continue
                    # Determine header: if first row looks like headers (contains Arabic words
                    # or digits for periods), use it.
                    header = tbl[0]

                    def _is_header_cell(x: Optional[str]) -> bool:
                        s = norm_ar(x or "")
                        return bool(
                            any(
                                k in s
                                for k in ["اليوم", "المعلم", "المدرس", "الشعبة", "الصف"]
                            )
                            or re.search(r"\d+", s.translate(AR_NUMS))
                        )

                    use_first_as_header = any(_is_header_cell(c) for c in header)
                    rows = tbl[1:] if use_first_as_header else tbl
                    # Build DataFrame
                    # Normalize width to max columns
                    max_cols = max(len(r) for r in rows) if rows else len(header)

                    def _pad(r):
                        return list(r) + [None] * (max_cols - len(r))

                    data_rows = [_pad(r) for r in rows]
                    if use_first_as_header:
                        cols = [norm_ar(c or f"col{i+1}") for i, c in enumerate(header)]
                        cols = cols + [f"col{i+1}" for i in range(len(cols), max_cols)]
                        df = pd.DataFrame(data_rows, columns=cols)
                    else:
                        cols = [f"col{i+1}" for i in range(max_cols)]
                        df = pd.DataFrame(data_rows, columns=cols)
                    # Ensure string dtype for downstream logic
                    for c in df.columns:
                        df[c] = df[c].astype(str)
                    # Attach page-level text for downstream heuristics
                    try:
                        df["__page_text__"] = page_text
                    except Exception:
                        pass
                    dfs.append(df)
    except Exception as e:
        raise CommandError(f"Failed to read PDF tables from {pdf_path}: {e}")

    return dfs


class Command(BaseCommand):
    help = (
        "Import school timetable data from PDFs. Reads teacher schedules with subjects and classes "
        "from المعلمون.pdf when available. Also supports شعب.pdf (classes) to seed Class list."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "base_dir",
            help=(
                "Directory containing the PDFs: المعلمون.pdf, الشعب.pdf, الجدول العام.pdf "
                "(any subset acceptable)"
            ),
        )
        parser.add_argument(
            "--template-name",
            default="الجدول الرسمي",
            help="CalendarTemplate name to use/create",
        )
        parser.add_argument(
            "--wipe",
            action="store_true",
            help=(
                "Delete existing TimetableEntry before import "
                "(affects all except skipped teachers)"
            ),
        )
        parser.add_argument(
            "--skip-teacher",
            action="append",
            default=["يوسف يعقوب"],
            help="Full name of teacher to exclude (can repeat)",
        )
        parser.add_argument(
            "--dry-run", action="store_true", help="Validate only; no DB writes"
        )

    def handle(
        self,
        base_dir: str,
        template_name: str,
        wipe: bool,
        skip_teacher: List[str],
        dry_run: bool,
        **opts,
    ):
        # Resolve models lazily now that Django apps are ready
        self.Staff = apps.get_model("school", "Staff")
        self.Class = apps.get_model("school", "Class")
        self.Subject = apps.get_model("school", "Subject")
        self.CalendarTemplate = apps.get_model("school", "CalendarTemplate")
        self.CalendarSlot = apps.get_model("school", "CalendarSlot")
        self.TimetableEntry = apps.get_model("school", "TimetableEntry")
        self.TeachingAssignment = apps.get_model("school", "TeachingAssignment")
        self.ClassSubject = apps.get_model("school", "ClassSubject")

        base = Path(base_dir)
        if not base.exists():
            raise CommandError(f"Base directory not found: {base}")

        # Locate files (some may be missing; we proceed best-effort)
        teachers_pdf = base / "المعلمون.pdf"
        classes_pdf = base / "الشعب.pdf"
        general_pdf = base / "الجدول العام.pdf"

        # 1) Ensure/prepare CalendarTemplate and Slots
        tmpl = self._ensure_template(template_name)
        days = [
            d.strip()
            for d in (tmpl.days or "Sun,Mon,Tue,Wed,Thu").split(",")
            if d.strip()
        ]
        slots_index: Dict[Tuple[str, str], object] = {}
        for d in days:
            for s in tmpl.slots.filter(
                day=d, block=self.CalendarSlot.Block.CLASS
            ).order_by("order", "start_time"):
                slots_index[(d, str(s.period_index))] = s

        # 2) Seed classes from الشعب.pdf if present
        if classes_pdf.exists():
            self.stdout.write(f"[info] Reading classes from {classes_pdf} ...")
            self._import_classes(classes_pdf)

        created_entries: List[object] = []
        subjects_cache: Dict[str, object] = {}
        classes_cache: Dict[str, object] = {c.name: c for c in self.Class.objects.all()}
        teachers_cache: Dict[str, object] = {
            t.full_name: t for t in self.Staff.objects.all()
        }

        rows_seen = 0

        # 3) Preferred source: المعلمون.pdf contains per-teacher timetable with subject+class
        if teachers_pdf.exists():
            self.stdout.write(
                f"[info] Reading teachers' timetables from {teachers_pdf} ..."
            )
            tables = try_read_pdf_tables(teachers_pdf)
            for df in tables:
                df = df.fillna("")
                # Extract page-level text (if present)
                # and drop helper column from further processing
                page_text = ""
                if "__page_text__" in df.columns:
                    try:
                        page_text = str(df["__page_text__"].iat[0] or "")
                    except Exception:
                        page_text = ""
                    try:
                        df = df.drop(columns=["__page_text__"])
                    except Exception:
                        pass
                cols_norm = [norm_ar(c) for c in df.columns]
                # Heuristic: find teacher name column if present
                teacher_col_idx = None
                for i, c in enumerate(cols_norm):
                    if (
                        "المعلم" in c
                        or "المدرس" in c
                        or "الأستاذ" in c
                        or "استاذ" in c
                        or "اسم" in c
                    ):
                        teacher_col_idx = i
                        break
                # Detect day column if present
                day_col_idx = None
                for i, c in enumerate(cols_norm):
                    if "اليوم" in c:
                        day_col_idx = i
                        break
                # Detect period columns (those whose header ends with a digit)
                period_cols: List[Tuple[int, str]] = []  # (index, period_index)
                for i, c in enumerate(cols_norm):
                    m = re.search(r"(\d+)$", c.translate(AR_NUMS))
                    if m:
                        period_cols.append((i, m.group(1)))
                if not period_cols:
                    # Some files label periods like "حصة 1" etc.
                    for i, c in enumerate(cols_norm):
                        m = re.search(r"حصة\s*(\d+)", c.translate(AR_NUMS))
                        if m:
                            period_cols.append((i, m.group(1)))
                # Heuristic branch: detect a multi-teacher grid (teachers across columns),
                # where the first column = period 1..7 repeated
                multi_grid_handled = False
                try:
                    first_col = (
                        df.iloc[:, 0]
                        .astype(str)
                        .map(lambda s: norm_ar(s).translate(AR_NUMS))
                    )
                    nums = [int(x) for x in first_col if x.isdigit()]
                except Exception:
                    nums = []
                grid_rows_ok = len(df) >= 21 and nums[:7] == list(range(1, 8))
                if day_col_idx is None and grid_rows_ok:
                    # Extract teacher names from page text block
                    lines = [norm_ar(line) for line in (page_text or "").splitlines()]
                    day_tokens = set(DAY_AR_TO_EN.keys())
                    # Collect Arabic-looking candidate names
                    candidates: List[str] = []
                    for line in lines:
                        if not line:
                            continue
                        if any(d in line for d in day_tokens):
                            continue
                        # Skip lines that are mostly digits or dot-separated class codes
                        if re.fullmatch(r"[0-9\s\.\-]+", line.translate(AR_NUMS)):
                            continue
                        if re.search(r"[\u0600-\u06FF]", line) and len(line) >= 2:
                            candidates.append(line)
                    # Data columns (exclude first period index column)
                    data_cols = list(df.columns[1:])
                    # Heuristic: take the last N Arabic lines as teacher names
                    # where N = number of columns
                    N = len(data_cols)
                    teacher_names: List[str] = candidates[-N:] if N else []
                    # If still mismatched, truncate/pad to fit columns
                    if len(teacher_names) != N:
                        teacher_names = (teacher_names + [""] * N)[:N]
                    if N > 0 and teacher_names:
                        # Determine how many full day groups exist by scanning
                        # the first column for runs 1..7
                        days_order = ["Sun", "Mon", "Tue", "Wed", "Thu"]
                        total_periods = 7
                        # Count how many complete sequences 1..7 exist
                        seq = [
                            int(x)
                            for x in first_col
                            if x.isdigit() and 1 <= int(x) <= 7
                        ]
                        complete_runs = len(seq) // total_periods
                        max_day_groups = min(len(days_order), complete_runs)
                        for day_idx in range(max_day_groups):
                            day_en = days_order[day_idx]
                            for p in range(1, total_periods + 1):
                                r = day_idx * total_periods + (p - 1)
                                if r >= len(df):
                                    break
                                for col_idx, col_name in enumerate(data_cols):
                                    teacher_name = (
                                        norm_ar(teacher_names[col_idx])
                                        or f"معلم-{col_idx+1}"
                                    )
                                    val = norm_ar(df.iloc[r][col_name])
                                    if not val:
                                        continue
                                    # Resolve teacher
                                    t_obj = teachers_cache.get(teacher_name)
                                    if not t_obj:
                                        t_obj, _ = self.Staff.objects.get_or_create(
                                            full_name=teacher_name
                                        )
                                        teachers_cache[teacher_name] = t_obj
                                    if t_obj and t_obj.full_name in skip_teacher:
                                        continue
                                    # Parse class + subject
                                    cname = ""
                                    sname = ""
                                    parts = val.split()
                                    if len(parts) >= 2:
                                        cname = norm_ar(parts[0])
                                        sname = norm_ar(" ".join(parts[1:]))
                                    else:
                                        cname = val
                                        sname = ""
                                    if not cname:
                                        continue
                                    # Resolve class
                                    c_obj = classes_cache.get(cname)
                                    if not c_obj:
                                        c_obj = self.Class.objects.filter(
                                            name=cname
                                        ).first()
                                        if not c_obj:
                                            m = re.search(
                                                r"(\d+)", cname.translate(AR_NUMS)
                                            )
                                            grade = int(m.group(1)) if m else 0
                                            c_obj = self.Class.objects.create(
                                                name=cname, grade=grade
                                            )
                                        classes_cache[cname] = c_obj
                                    # Resolve subject
                                    if sname:
                                        subj_obj = subjects_cache.get(sname)
                                        if not subj_obj:
                                            subj_obj = self.Subject.objects.filter(
                                                name_ar=sname
                                            ).first()
                                            if not subj_obj:
                                                subj_obj = self.Subject.objects.create(
                                                    name_ar=sname
                                                )
                                            subjects_cache[sname] = subj_obj
                                    else:
                                        subj_obj = self.Subject.objects.get_or_create(
                                            name_ar="غير محدد"
                                        )[0]
                                    # Resolve/Create slot
                                    slot = slots_index.get((day_en, str(p)))
                                    if not slot:
                                        slot = self._ensure_slot(tmpl, day_en, str(p))
                                        slots_index[(day_en, str(p))] = slot
                                    created_entries.append(
                                        self.TimetableEntry(
                                            classroom=c_obj,
                                            day=day_en,
                                            slot=slot,
                                            subject=subj_obj,
                                            teacher=t_obj,
                                        )
                                    )
                        multi_grid_handled = True
                if not period_cols and not multi_grid_handled:
                    continue  # not a layout we can parse

                if multi_grid_handled:
                    # Done with this table
                    continue

                # Iterate rows
                # Try to pre-detect teacher from page header text if teacher column is absent
                current_teacher = None
                if not any(
                    k in (teacher_col_idx if teacher_col_idx is not None else [])
                    for k in []
                ):
                    # Simple regex to capture a teacher name following a label
                    m = (
                        re.search(
                            r"(?:الأستاذ|استاذ|المدرس|المعلم)[:：]?\s*([^\n\r]+)",
                            norm_ar(page_text),
                        )
                        if page_text
                        else None
                    )
                    if m:
                        teacher_from_header = norm_ar(m.group(1))
                        if teacher_from_header:
                            t_obj = teachers_cache.get(teacher_from_header)
                            if not t_obj:
                                t_obj, _ = self.Staff.objects.get_or_create(
                                    full_name=teacher_from_header
                                )
                                teachers_cache[teacher_from_header] = t_obj
                            current_teacher = t_obj
                for _, row in df.iterrows():
                    rows_seen += 1
                    teacher_name = (
                        norm_ar(row.iloc[teacher_col_idx])
                        if teacher_col_idx is not None
                        else ""
                    )
                    day_ar = (
                        norm_ar(row.iloc[day_col_idx])
                        if day_col_idx is not None
                        else ""
                    )
                    day_en = DAY_AR_TO_EN.get(day_ar, None) if day_ar else None
                    # If no explicit day column, this table might be per-teacher
                    # with one row per day section, or the day is embedded in a
                    # separate column; try deriving from first column.
                    if day_col_idx is None:
                        first_cell = norm_ar(row.iloc[0]) if len(row) else ""
                        cand = DAY_AR_TO_EN.get(first_cell)
                        if cand:
                            day_en = cand
                    if not day_en:
                        continue

                    # Ensure teacher exists (reuse last seen teacher within the same table)
                    # if the teacher column is empty
                    if teacher_name:
                        t_obj = teachers_cache.get(teacher_name)
                        if not t_obj:
                            t_obj, _ = self.Staff.objects.get_or_create(
                                full_name=teacher_name
                            )
                            teachers_cache[teacher_name] = t_obj
                        current_teacher = t_obj
                    else:
                        t_obj = current_teacher

                    # Skip excluded teachers
                    if t_obj and t_obj.full_name in skip_teacher:
                        continue

                    for idx, period_index in period_cols:
                        val = norm_ar(row.iloc[idx])
                        if not val:
                            continue
                        # Expect patterns like "10-3 رياضيات" or "10-3-أ" etc.
                        # Try to split class and subject by space;
                        # first token is usually the class name.
                        cname = ""
                        sname = ""
                        parts = val.split()
                        if len(parts) >= 2:
                            cname = norm_ar(parts[0])
                            sname = norm_ar(" ".join(parts[1:]))
                        else:
                            # If only one token, it might be class only
                            cname = val
                            sname = ""

                        if not cname:
                            continue

                        # Resolve class
                        c_obj = classes_cache.get(cname)
                        if not c_obj:
                            c_obj = self.Class.objects.filter(name=cname).first()
                            if not c_obj:
                                # Create with best-effort grade from name
                                m = re.search(r"(\d+)", cname.translate(AR_NUMS))
                                grade = int(m.group(1)) if m else 0
                                c_obj = self.Class.objects.create(
                                    name=cname, grade=grade
                                )
                            classes_cache[cname] = c_obj

                        # Resolve subject (allow Arabic name_ar)
                        subj_obj: Optional[object] = None
                        if sname:
                            subj_obj = subjects_cache.get(sname)
                            if not subj_obj:
                                subj_obj = self.Subject.objects.filter(
                                    name_ar=sname
                                ).first()
                                if not subj_obj:
                                    subj_obj = self.Subject.objects.create(
                                        name_ar=sname
                                    )
                                subjects_cache[sname] = subj_obj
                        else:
                            # Create placeholder subject when absent
                            subj_obj = self.Subject.objects.get_or_create(
                                name_ar="غير محدد"
                            )[0]

                        # Resolve teacher: if absent in row and no carry-over, skip
                        if not t_obj:
                            continue

                        # Resolve slot
                        slot = slots_index.get((day_en, str(period_index)))
                        if not slot:
                            # Create slot if missing with default timing cascade (45 min)
                            slot = self._ensure_slot(tmpl, day_en, str(period_index))
                            slots_index[(day_en, str(period_index))] = slot

                        # Prepare entry
                        created_entries.append(
                            self.TimetableEntry(
                                classroom=c_obj,
                                day=day_en,
                                slot=slot,
                                subject=subj_obj,
                                teacher=t_obj,
                            )
                        )

        # 4) Fallback: parse الجدول العام.pdf if present and needed (optional)
        if not created_entries and general_pdf.exists():
            try:
                self.stdout.write(
                    f"[info] Reading general timetable from {general_pdf} ..."
                )
                tables = try_read_pdf_tables(general_pdf)
            except Exception:
                tables = []
            days_order = ["Sun", "Mon", "Tue", "Wed", "Thu"]
            total_periods = 7
            for df in tables:
                try:
                    df = df.fillna("")
                except Exception:
                    continue

                # Detect teacher-name column: the column with most Arabic letters and few digits
                def score_name_col(series) -> int:
                    cnt = 0
                    for v in series.astype(str):
                        s = norm_ar(v)
                        if not s:
                            continue
                        if re.search(r"[\u0600-\u06FF]", s) and not re.search(
                            r"\d", s.translate(AR_NUMS)
                        ):
                            cnt += 1
                    return cnt

                best_idx = None
                best_score = -1
                for i in range(len(df.columns)):
                    sc = score_name_col(df.iloc[:, i])
                    if sc > best_score:
                        best_score = sc
                        best_idx = i
                if best_idx is None or best_score < 5:
                    continue
                name_col = best_idx
                # Candidate data columns: all except name column
                data_cols = [i for i in range(len(df.columns)) if i != name_col]
                if len(data_cols) < total_periods * len(days_order):
                    continue
                # Try both LTR and RTL orders
                for cols_order in (data_cols, list(reversed(data_cols))):
                    # Map day->period indices slicing
                    needed = total_periods * len(days_order)
                    cols_slice = cols_order[:needed]
                    ok = len(cols_slice) == needed
                    if not ok:
                        continue
                    # Iterate rows (one per teacher)
                    for _, row in df.iterrows():
                        teacher_name = norm_ar(str(row.iloc[name_col]))
                        if not teacher_name:
                            continue
                        # skip excluded teachers
                        if teacher_name in skip_teacher:
                            continue
                        # resolve teacher
                        t_obj = teachers_cache.get(teacher_name)
                        if not t_obj:
                            t_obj, _ = self.Staff.objects.get_or_create(
                                full_name=teacher_name
                            )
                            teachers_cache[teacher_name] = t_obj
                        # For each day/period
                        idx = 0
                        for day_en in days_order:
                            for p in range(1, total_periods + 1):
                                col_i = cols_slice[idx]
                                idx += 1
                                val = norm_ar(str(row.iloc[col_i]))
                                if not val:
                                    continue
                                parts = val.split()
                                if len(parts) >= 2:
                                    cname = norm_ar(parts[0])
                                    sname = norm_ar(" ".join(parts[1:]))
                                else:
                                    cname = val
                                    sname = ""
                                if not cname:
                                    continue
                                c_obj = classes_cache.get(cname)
                                if not c_obj:
                                    c_obj = self.Class.objects.filter(
                                        name=cname
                                    ).first()
                                    if not c_obj:
                                        m = re.search(
                                            r"(\d+)", cname.translate(AR_NUMS)
                                        )
                                        grade = int(m.group(1)) if m else 0
                                        c_obj = self.Class.objects.create(
                                            name=cname, grade=grade
                                        )
                                    classes_cache[cname] = c_obj
                                if sname:
                                    subj_obj = subjects_cache.get(sname)
                                    if not subj_obj:
                                        subj_obj = self.Subject.objects.filter(
                                            name_ar=sname
                                        ).first()
                                        if not subj_obj:
                                            subj_obj = self.Subject.objects.create(
                                                name_ar=sname
                                            )
                                        subjects_cache[sname] = subj_obj
                                else:
                                    subj_obj = self.Subject.objects.get_or_create(
                                        name_ar="غير محدد"
                                    )[0]
                                slot = slots_index.get((day_en, str(p)))
                                if not slot:
                                    slot = self._ensure_slot(tmpl, day_en, str(p))
                                    slots_index[(day_en, str(p))] = slot
                                created_entries.append(
                                    self.TimetableEntry(
                                        classroom=c_obj,
                                        day=day_en,
                                        slot=slot,
                                        subject=subj_obj,
                                        teacher=t_obj,
                                    )
                                )
                    # If we created any entries using this orientation, stop trying the other one
                    if created_entries:
                        break
                # Stop on first table that yields entries
                if created_entries:
                    break

        if dry_run:
            dry_msg = (
                "[DRY] Parsed rows: {rows}, will create {n} TimetableEntry rows "
                "(after skipping: {skips} teacher(s))"
            ).format(rows=rows_seen, n=len(created_entries), skips=len(skip_teacher))
            self.stdout.write(dry_msg)
            return

        # 5) Write DB: wipe (except skipped teachers), then bulk create,
        # then build TeachingAssignment
        with transaction.atomic():
            if wipe:
                # delete all except skipped teachers
                if skip_teacher:
                    self.TimetableEntry.objects.exclude(
                        teacher__full_name__in=skip_teacher
                    ).delete()
                else:
                    self.TimetableEntry.objects.all().delete()

            # bulk_create with ignore_conflicts to make command idempotent across runs
            # Group by key and keep last occurrence within this batch
            dedup_map: Dict[Tuple[int, str, int], object] = {}
            for e in created_entries:
                key = (e.classroom_id or e.classroom.id, e.day, e.slot_id or e.slot.id)
                dedup_map[key] = e
            # Skip rows that already exist due to unique constraint (classroom, day, slot)
            self.TimetableEntry.objects.bulk_create(
                list(dedup_map.values()), ignore_conflicts=True
            )

            # Rebuild TeachingAssignment counts from TimetableEntry
            agg: Dict[Tuple[int, int, int], int] = {}
            qs = self.TimetableEntry.objects.all().select_related(
                "classroom", "subject", "teacher"
            )
            if skip_teacher:
                qs = qs.exclude(teacher__full_name__in=skip_teacher)
            for e in qs:
                key = (e.classroom_id, e.subject_id, e.teacher_id)
                agg[key] = agg.get(key, 0) + 1
            for (cid, sid, tid), cnt in agg.items():
                # Ensure the subject is attached to the class (required by TeachingAssignment.clean)
                if not self.ClassSubject.objects.filter(
                    classroom_id=cid, subject_id=sid
                ).exists():
                    self.ClassSubject.objects.create(
                        classroom_id=cid, subject_id=sid, weekly_default=cnt
                    )
                ta, _ = self.TeachingAssignment.objects.get_or_create(
                    classroom_id=cid,
                    subject_id=sid,
                    teacher_id=tid,
                    defaults={"no_classes_weekly": cnt},
                )
                if ta.no_classes_weekly != cnt:
                    ta.no_classes_weekly = cnt
                    ta.save(update_fields=["no_classes_weekly"])

        self.stdout.write(
            self.style.SUCCESS(
                "Imported timetable entries (idempotent: existing rows skipped) "
                "and updated teaching assignments."
            )
        )

    # --- helpers ---

    def _ensure_template(self, name: str) -> object:
        tmpl, created = self.CalendarTemplate.objects.get_or_create(
            name=name, defaults={"days": "Sun,Mon,Tue,Wed,Thu"}
        )
        # Ensure at least 7 class blocks per day with default times if none exist
        if not tmpl.slots.filter(block=self.CalendarSlot.Block.CLASS).exists():
            from datetime import datetime, timedelta

            def add_minutes(t, mins):
                dt = datetime.combine(datetime.today(), t) + timedelta(minutes=mins)
                return dt.time()

            start = datetime.strptime("08:00", "%H:%M").time()
            for day in [
                d.strip()
                for d in (tmpl.days or "Sun,Mon,Tue,Wed,Thu").split(",")
                if d.strip()
            ]:
                t0 = start
                for p in range(1, 8):
                    t1 = add_minutes(t0, 45)
                    self.CalendarSlot.objects.create(
                        template=tmpl,
                        day=day,
                        period_index=str(p),
                        start_time=t0,
                        end_time=t1,
                        block=self.CalendarSlot.Block.CLASS,
                        order=p,
                    )
                    # 5-minute break
                    t0 = add_minutes(t1, 5)
        return tmpl

    def _ensure_slot(self, tmpl: object, day: str, period_index: str) -> object:
        slot = self.CalendarSlot.objects.filter(
            template=tmpl, day=day, period_index=str(period_index)
        ).first()
        if slot:
            return slot
        # create with default time based on order as last known + 50 minutes per period
        from datetime import datetime, timedelta

        existing = tmpl.slots.filter(
            day=day, block=self.CalendarSlot.Block.CLASS
        ).order_by("order", "start_time")
        if existing.exists():
            last = existing.last()
            start = (
                datetime.combine(datetime.today(), last.end_time) + timedelta(minutes=5)
            ).time()
            end = (
                datetime.combine(datetime.today(), start) + timedelta(minutes=45)
            ).time()
            order = (last.order or 0) + 1
        else:
            start = datetime.strptime("08:00", "%H:%M").time()
            end = (
                datetime.combine(datetime.today(), start) + timedelta(minutes=45)
            ).time()
            order = 1
        return self.CalendarSlot.objects.create(
            template=tmpl,
            day=day,
            period_index=str(period_index),
            start_time=start,
            end_time=end,
            block=self.CalendarSlot.Block.CLASS,
            order=order,
        )

    def _import_classes(self, pdf_path: Path) -> None:
        tables = try_read_pdf_tables(pdf_path)
        created = 0
        for df in tables:
            df = df.fillna("")
            for _, row in df.iterrows():
                # try common headers: الشعبة / الصف
                cname = norm_ar(row.get("الشعبة", "")) or norm_ar(row.get("الصف", ""))
                if not cname:
                    # maybe first column is name
                    if len(row.index) > 0:
                        cname = norm_ar(row.iloc[0])
                if not cname:
                    continue
                # parse grade from name (first digits)
                m = re.search(r"(\d+)", cname.translate(AR_NUMS))
                grade = int(m.group(1)) if m else 0
                obj, created_flag = self.Class.objects.get_or_create(
                    name=cname, defaults={"grade": grade}
                )
                if not created_flag and obj.grade != grade and grade:
                    obj.grade = grade
                    obj.save(update_fields=["grade"])
                if created_flag:
                    created += 1
        if created:
            self.stdout.write(
                f"[info] Created {created} class(es) from {pdf_path.name}"
            )


if __name__ == "__main__":
    # Friendly guidance when this file is executed directly.
    # Django management commands must be run via manage.py so that Django
    # initializes settings and the app registry before calling the command.
    import sys

    print("[import_from_pdf] This is a Django management command.")
    print(
        "Run it via: python backend\\manage.py import_from_pdf "
        "D:\\sh_school_015\\DOC\\school_DATA --dry-run"
    )
    print("If the dry-run looks correct, run:")
    print(
        "python backend\\manage.py import_from_pdf "
        "D:\\sh_school_015\\DOC\\school_DATA --wipe"
    )
    print(
        "Note: teacher 'يوسف يعقوب' is skipped by default; use --skip-teacher to adjust."
    )
    sys.exit(0)
