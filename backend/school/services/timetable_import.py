import csv
import io
import re
from typing import Dict, Any

from django.db import transaction

from ..models import Class, Staff, Subject, TimetableEntry, Term


def _normalize_ar(s: str) -> str:
    if s is None:
        return ""
    s = str(s)
    s = re.sub(r"\s+", " ", s).strip()
    s = s.replace("ـ", "")
    s = re.sub(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]", "", s)
    replacements = {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ٱ": "ا",
        "ى": "ي",
        "ئ": "ي",
        "ؤ": "و",
        "ة": "ه",
    }
    for k, v in replacements.items():
        s = s.replace(k, v)
    s = re.sub(r"[^\w\s\u0600-\u06FF]", "", s)
    trans_digits = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
    s = s.translate(trans_digits)
    return s.lower()


_DAY_MAP = {
    "1": 1,
    "الاحد": 1,
    "أحد": 1,
    "الاحد ": 1,
    "2": 2,
    "الاثنين": 2,
    "إثنين": 2,
    "الاثنين ": 2,
    "3": 3,
    "الثلاثاء": 3,
    "4": 4,
    "الاربعاء": 4,
    "الأربعاء": 4,
    "5": 5,
    "الخميس": 5,
}


def _parse_day(v: str) -> int:
    if v is None:
        return 0
    s = _normalize_ar(str(v))
    # numbers as text already normalized to ascii
    if s.isdigit():
        try:
            n = int(s)
            return n if 1 <= n <= 5 else 0
        except Exception:
            return 0
    return _DAY_MAP.get(s, 0)


def _parse_period(v: str) -> int:
    try:
        n = int(str(v).strip())
        return n if 1 <= n <= 7 else 0
    except Exception:
        return 0


def import_timetable_csv(file_obj, *, dry_run: bool = False) -> Dict[str, Any]:
    """Import TimetableEntry rows from a CSV file.

    CSV headers (case-insensitive, Arabic accepted in values):
      teacher, class, subject, day, period
    - teacher: full name of Staff
    - class: either class name (e.g., "7-1" or Arabic name stored) or grade-section
    - subject: Arabic subject name
    - day: 1..5 or Arabic day name
    - period: 1..7
    Replaces any existing entry conflicts at the same (day,period) for the same
    teacher or same classroom.
    Returns a summary dict.
    """
    if hasattr(file_obj, "read"):
        data = file_obj.read()
        if isinstance(data, bytes):
            data = data.decode("utf-8-sig", errors="ignore")
        text = data
    else:
        # assume path string
        with open(file_obj, "r", encoding="utf-8-sig") as f:
            text = f.read()

    reader = csv.DictReader(io.StringIO(text))
    headers = {k.lower().strip(): k for k in reader.fieldnames or []}
    required = ["teacher", "class", "subject", "day", "period"]
    for r in required:
        if r not in headers:
            raise ValueError(f"Missing required header: {r}")

    # Build lookup maps
    teachers_by_key = {}
    for t in Staff.objects.all():
        k = _normalize_ar(t.full_name).replace(" ", "")
        if k:
            teachers_by_key.setdefault(k, t)

    classes_by_name = {}
    classes_by_gs = {}
    for c in Class.objects.all():
        classes_by_name[_normalize_ar(c.name)] = c
        gs = f"{c.grade}-{(c.section or '').strip()}" if c.section else str(c.grade)
        classes_by_gs[_normalize_ar(gs)] = c

    subjects_by_key = {_normalize_ar(s.name_ar): s for s in Subject.objects.all()}

    term = Term.objects.filter(is_current=True).first()
    if not term:
        raise ValueError("لا يوجد فصل دراسي حالي")

    created = 0
    replaced = 0
    skipped = 0
    errors = []

    # transactional import
    ctx = transaction.atomic() if not dry_run else None
    if ctx:
        ctx.__enter__()
    try:
        for i, row in enumerate(reader, start=2):  # start=2 accounting for header
            teacher_v = str(row.get(headers["teacher"], "")).strip()
            class_v = str(row.get(headers["class"], "")).strip()
            subject_v = str(row.get(headers["subject"], "")).strip()
            day_v = row.get(headers["day"], "")
            period_v = row.get(headers["period"], "")

            tkey = _normalize_ar(teacher_v).replace(" ", "")
            teacher = teachers_by_key.get(tkey)
            if not teacher:
                skipped += 1
                errors.append(f"سطر {i}: المعلم غير معروف: {teacher_v}")
                continue

            ckey1 = _normalize_ar(class_v)
            classroom = classes_by_name.get(ckey1) or classes_by_gs.get(ckey1)
            if not classroom:
                skipped += 1
                errors.append(f"سطر {i}: الصف غير معروف: {class_v}")
                continue

            skey = _normalize_ar(subject_v)
            subject = subjects_by_key.get(skey)
            if not subject:
                skipped += 1
                errors.append(f"سطر {i}: المادة غير معروفة: {subject_v}")
                continue

            day = _parse_day(str(day_v))
            period = _parse_period(str(period_v))
            if not (1 <= day <= 5 and 1 <= period <= 7):
                skipped += 1
                errors.append(f"سطر {i}: اليوم/الحصة غير صالحين: day={day_v} period={period_v}")
                continue

            if dry_run:
                # just simulate success
                created += 1
                continue

            # Replace conflicts: same teacher or same class at that slot
            q_teacher = TimetableEntry.objects.filter(
                term=term, day_of_week=day, period_number=period, teacher=teacher
            )
            q_class = TimetableEntry.objects.filter(
                term=term, day_of_week=day, period_number=period, classroom=classroom
            )
            rep_count = (
                q_teacher.count()
                + q_class.exclude(id__in=q_teacher.values_list("id", flat=True)).count()
            )
            if rep_count:
                replaced += rep_count
            q_teacher.delete()
            q_class.delete()

            TimetableEntry.objects.create(
                classroom=classroom,
                subject=subject,
                teacher=teacher,
                day_of_week=day,
                period_number=period,
                term=term,
            )
            created += 1
    finally:
        if ctx:
            if dry_run:
                ctx.__exit__(None, None, None)  # no commit
            else:
                ctx.__exit__(None, None, None)

    return {
        "ok": True,
        "created": created,
        "replaced": replaced,
        "skipped": skipped,
        "errors": errors,
        "term": term.id if term else None,
    }
