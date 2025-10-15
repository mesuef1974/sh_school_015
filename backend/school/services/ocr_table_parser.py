import os
import csv
import io
import re
from typing import Tuple, List, Dict

from django.conf import settings

from ..models import Staff, Class, Subject, TeachingAssignment


_AR_NUM = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")


def _normalize_ar(s: str) -> str:
    if s is None:
        return ""
    s = str(s)
    s = s.translate(_AR_NUM)
    # remove tatweel and diacritics
    s = s.replace("ـ", "")
    s = re.sub(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]", "", s)
    # common letter normalizations
    s = (
        s.replace("أ", "ا")
        .replace("إ", "ا")
        .replace("آ", "ا")
        .replace("ٱ", "ا")
        .replace("ى", "ي")
        .replace("ئ", "ي")
        .replace("ؤ", "و")
        .replace("ة", "ه")
    )
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


def _reverse_text(s: str) -> str:
    try:
        return (s or "")[::-1]
    except Exception:
        return s or ""


def _reverse_words_chars(s: str) -> str:
    try:
        words = [w for w in re.split(r"\s+", s or "") if w]
        return " ".join([w[::-1] for w in words])
    except Exception:
        return s or ""


def _load_teacher_mapping() -> Dict[str, str]:
    """Optional mapping file DOC/school_DATA/teacher_mapping.csv with columns:
    ocr_name,full_name. Returns dict keyed by normalized ocr_name (no spaces)."""
    base_dir = os.path.abspath(os.path.join(settings.BASE_DIR, "..", "DOC", "school_DATA"))
    path = os.path.join(base_dir, "teacher_mapping.csv")
    mapping: Dict[str, str] = {}
    if not os.path.exists(path):
        return mapping
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            rdr = csv.DictReader(f)
            for row in rdr:
                ocr = _normalize_ar(row.get("ocr_name", "")).replace(" ", "")
                full = str(row.get("full_name", "")).strip()
                if ocr and full:
                    mapping[ocr] = full
    except Exception:
        pass
    return mapping


def _classes_index():
    by_name = {}
    by_gs = {}
    for c in Class.objects.all():
        by_name[_normalize_ar(c.name)] = c
        gs = f"{c.grade}-{(c.section or '').strip()}" if c.section else str(c.grade)
        by_gs[_normalize_ar(gs)] = c
    return by_name, by_gs


def _staff_index():
    by_key = {}
    for t in Staff.objects.all():
        k = _normalize_ar(t.full_name).replace(" ", "")
        if k:
            by_key[k] = t
    return by_key


def _subject_name(subj: Subject) -> str:
    return subj.name_ar


def _resolve_teacher(
    name_raw: str, teacher_map: Dict[str, str], staff_by_key: Dict[str, Staff]
) -> Staff:
    # Try several variants to cope with mirrored OCR for Arabic text
    candidates = []
    base = name_raw or ""
    candidates.append(base)
    candidates.append(_reverse_words_chars(base))  # reverse chars per word
    candidates.append(_reverse_text(base))  # full reverse
    # reverse words order + chars per word
    try:
        words = [w for w in re.split(r"\s+", base.strip()) if w]
        candidates.append(" ".join([w[::-1] for w in reversed(words)]))
    except Exception:
        pass

    # Try mapping and direct staff match for each candidate
    for cand in candidates:
        k = _normalize_ar(cand).replace(" ", "")
        if not k:
            continue
        # Direct staff match
        t = staff_by_key.get(k)
        if t:
            return t
        # Via mapping file
        mapped = teacher_map.get(k)
        if mapped:
            mk = _normalize_ar(mapped).replace(" ", "")
            t2 = staff_by_key.get(mk)
            if t2:
                return t2
    return None


def _token_to_class_code(tok: str) -> str:
    """Convert token like '12.3' or '9.1' to '12-3' or '9-1'."""
    tok = (tok or "").strip().translate(_AR_NUM)
    m = re.match(r"^(\d{1,2})\.(\d)$", tok)
    if m:
        return f"{int(m.group(1))}-{int(m.group(2))}"
    # sometimes tokens like '11.4 ' with spaces
    m = re.match(r"^(\d{1,2})\s*[\.|-]\s*(\d)$", tok)
    if m:
        return f"{int(m.group(1))}-{int(m.group(2))}"
    return ""


def parse_ocr_raw_to_csv(text: str) -> Tuple[str, List[str]]:
    """Parse the provided OCR raw dump into CSV text and return (csv_text, warnings).

    Assumptions:
    - Input contains repeated segments starting with 'تم التقاط صف خام من الجدول:' followed by a line of tokens separated by '|'.
    - Teacher rows include 35 tokens (5 days × 7 periods) followed by the teacher name (not necessarily separated by '|').
    - Period ordering within each day is 7..1 (as in the compact timetable header). We map index 0->(day=1,period=7), index 6->(day=1,period=1), index 7->(day=2,period=7), ...
    - Tokens like '12.3' denote grade-section and will be converted to '12-3'. Empty tokens are skipped.
    - Subject is inferred from TeachingAssignment for (teacher, class). If not found or ambiguous, that cell is skipped with a warning.
    - Teacher name can be corrected using optional DOC/school_DATA/teacher_mapping.csv.
    """
    warnings: List[str] = []
    if not text or not text.strip():
        return ("teacher,class,subject,day,period\n", ["النص الخام فارغ."])

    staff_by_key = _staff_index()
    cls_by_name, cls_by_gs = _classes_index()
    tmap = _load_teacher_mapping()

    # Extract blocks after the marker
    blocks: List[str] = []
    for part in re.split(r"تم التقاط صف خام من الجدول:\s*", text):
        part = part.strip()
        if not part:
            continue
        blocks.append(part)

    # Filters to skip header-like blocks
    def looks_like_header(s: str) -> bool:
        sn = _normalize_ar(s)
        if any(k in sn for k in ["الاحد", "الاثنين", "الثلاثاء", "الاربعاء", "الخميس"]):
            return True
        # Check reversed Arabic (mirrored OCR) for day names
        sn_rev = _normalize_ar(_reverse_text(s))
        if any(k in sn_rev for k in ["الاحد", "الاثنين", "الثلاثاء", "الاربعاء", "الخميس"]):
            return True
        # lot of digits 7|6|5 sequences
        if re.search(r"\b7\s*\|\s*6\s*\|\s*5\s*\|", s):
            return True
        if "ash-shahaniya" in s.lower() or "preparatory" in s.lower() or "school" in s.lower():
            return True
        return False

    # Prepare CSV writer to string buffer
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["teacher", "class", "subject", "day", "period"])

    total_cells = 0
    total_mapped = 0

    for blk in blocks:
        if looks_like_header(blk):
            continue
        # Split by '|' to collect tokens; anything after the last '|' may be teacher name
        # Ensure we capture the teacher name: take the substring after the last '|' as tail
        last_bar = blk.rfind("|")
        if last_bar == -1:
            # no bars — likely garbage
            warnings.append("تخطّي مقطع غير معروف (لا يحتوي على فواصل |)")
            continue
        tail = blk[last_bar + 1 :].strip()
        tokens_part = blk[:last_bar].strip()
        tokens = [t.strip() for t in tokens_part.split("|")]
        # Clean tokens, collapse consecutive empties by just keeping them (we rely on exact length)
        # Remove empty leading/trailing noise
        # Keep tokens as-is; we will normalize length to 35 by trimming/padding
        if len(tokens) < 20:
            # too short to be a 35-slot row
            warnings.append("تخطّي مقطع قصير لا يشبه صف المدرس.")
            continue
        # Determine teacher name (tail may contain reversed segments). Sometimes name leaks into tokens; try last non-empty token as fallback
        teacher_name_raw = tail
        if not teacher_name_raw:
            for t in reversed(tokens):
                # if looks like Arabic letters (not like 12.3)
                if re.search(r"[\u0600-\u06FF]", t) and not re.match(r"^\d{1,2}[\.|-]\d$", t):
                    teacher_name_raw = t
                    break
        teacher = _resolve_teacher(teacher_name_raw, tmap, staff_by_key)
        if not teacher:
            warnings.append(
                f"تخطّي صف بسبب عدم التعرف على اسم المعلم: '{teacher_name_raw or 'غير معروف'}'"
            )
            continue

        # Normalize tokens length to 35 (5×7)
        # Sometimes there are more than 35 due to duplicated day groups; take the last 35 tokens (often the meaningful set for the teacher row)
        if len(tokens) > 35:
            tokens = tokens[-35:]
        elif len(tokens) < 35:
            tokens = (tokens + ([""] * 35))[:35]

        # Map each token to (day, period)
        for idx, tok in enumerate(tokens):
            if not tok or not tok.strip():
                continue
            total_cells += 1
            gs = _token_to_class_code(tok)
            if not gs:
                continue
            classroom = cls_by_name.get(_normalize_ar(gs)) or cls_by_gs.get(_normalize_ar(gs))
            if not classroom:
                warnings.append(f"الصف غير معروف في النظام: {gs} (المعلم: {teacher.full_name})")
                continue
            # Day/period mapping: per group of 7 tokens in order 7..1
            day = (idx // 7) + 1  # 1..5
            offset = idx % 7
            period = 7 - offset  # 7..1
            # Resolve subject via TeachingAssignment
            asg_qs = TeachingAssignment.objects.filter(teacher=teacher, classroom=classroom)
            subject = None
            if asg_qs.count() == 1:
                subject = asg_qs.first().subject
            elif asg_qs.count() > 1:
                # if multiple, try to pick the one most common for this teacher overall (fallback: first)
                subject = asg_qs.first().subject
                warnings.append(
                    f"تعيينات متعددة للمادة (اختيار أول): المعلم {teacher.full_name} الصف {classroom.name}"
                )
            else:
                warnings.append(
                    f"لا توجد تعيين مادة للمعلم {teacher.full_name} في الصف {classroom.name} — تخطّي الخلية"
                )
                continue
            writer.writerow(
                [teacher.full_name, classroom.name, _subject_name(subject), day, period]
            )
            total_mapped += 1

    if total_mapped == 0:
        warnings.append("لم يتم توليد أي صفوف CSV — تحقق من أن النص الخام يخص صفوف المعلمين.")

    return (out.getvalue(), warnings)
