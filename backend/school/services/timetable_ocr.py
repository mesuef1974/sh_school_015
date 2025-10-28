import os
from typing import Tuple


def try_import(name: str):
    try:
        return __import__(name)
    except Exception:
        return None


def _normalize_text(s: str) -> str:
    try:
        import re

        s = re.sub(r"\s+", " ", s or "").strip()
        trans_digits = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
        s = s.translate(trans_digits)
        return s
    except Exception:
        return s or ""


def try_extract_csv_from_pdf(pdf_path: str) -> Tuple[str, str]:
    """Best-effort CSV extraction from a timetable PDF.
    Returns (csv_text, warnings). On failure, returns ("", warning_message).

    This function intentionally avoids hard dependencies. It will use pdfplumber if
    installed, otherwise returns a helpful warning.
    """
    warnings = []
    csv_lines = ["teacher,class,subject,day,period"]

    if not os.path.exists(pdf_path):
        return "", f"الملف غير موجود: {pdf_path}"

    pdfplumber = try_import("pdfplumber")
    if not pdfplumber:
        return "", (
            "تعذر الاستخراج الآلي: مكتبة pdfplumber غير مثبتة.\n"
            "يمكن تثبيتها بإحدى الطرق: pip install pdfplumber\n"
            "بديل: استخدم زر الاستيراد اليدوي عبر نسخ CSV."
        )

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                # Try extracting tables first
                tables = []
                try:
                    tables = page.extract_tables() or []
                except Exception:
                    tables = []
                if tables:
                    for tbl in tables:
                        # Heuristic: scan rows for patterns resembling timetable rows.
                        # This is highly dependent on the PDF layout; we only collect text cells.
                        for row in tbl:
                            # Skip empty rows
                            if not row or not any(c for c in row):
                                continue
                            # Join cells for analysis; users can adjust later.
                            row_text = [(_normalize_text(c) if isinstance(c, str) else "") for c in row]
                            joined = " | ".join(row_text)
                            # We do not know exact columns; append as comment for user visibility.
                            # The admin can quickly edit into canonical 5 columns.
                            warnings.append(f"تم التقاط صف خام من الجدول: {joined}")
                else:
                    # Fallback: extract text lines. This won't build CSV automatically, but helps user.
                    text = page.extract_text() or ""
                    for line in text.splitlines():
                        line = _normalize_text(line)
                        if not line:
                            continue
                        # Heuristic: only keep lines that look like they contain a class pattern like 7-1 or 9-A
                        import re

                        if re.search(r"\b\d\s*[-–]\s*[A-Za-z0-9\u0621-\u064A]+\b", line):
                            warnings.append(f"تم العثور على سطر محتمل: {line}")
        # The function is conservative: it returns just the header if it couldn't map reliably.
        # The captured warnings will appear on the page to help the admin fill quickly.
        return "\n".join(csv_lines) + "\n", "\n".join(warnings) if warnings else ""
    except Exception as e:
        return "", f"فشل استخراج PDF: {e}"


def try_extract_csv_from_image(img_path: str) -> Tuple[str, str]:
    """Attempt OCR from an image timetable with strong Arabic support.
    Handles mirrored (horizontally flipped) sources by trying both original and
    flipped variants, choosing the one with the higher Arabic character score.
    Returns (csv_text, warnings). On failure returns ("", message).
    """
    if not os.path.exists(img_path):
        return "", f"الصورة غير موجودة: {img_path}"

    pytesseract = try_import("pytesseract")
    PIL = try_import("PIL")
    if not (pytesseract and PIL):
        return "", (
            "تعذر الاستخراج الآلي من الصورة: يلزم pytesseract و Pillow.\n"
            "يمكن التثبيت: pip install pytesseract pillow\n"
            "بديل: استخدم زر الاستيراد اليدوي عبر نسخ CSV."
        )

    try:
        import re

        from PIL import Image, ImageFilter, ImageOps

        def arabic_score(s: str) -> int:
            # Count Arabic letters as a quick quality proxy
            return sum(1 for ch in (s or "") if "\u0600" <= ch <= "\u06FF")

        def ocr_image(img: "Image.Image") -> str:
            # Improve readability: convert to L, increase contrast/clarity a bit
            g = img.convert("L")
            # Light unsharp mask to enhance glyph edges (safe default)
            try:
                g = g.filter(ImageFilter.UnsharpMask(radius=1, percent=150, threshold=3))
            except Exception:
                pass
            config = "--oem 1 --psm 6 -c preserve_interword_spaces=1"
            return pytesseract.image_to_string(g, lang="ara+eng", config=config)

        img = Image.open(img_path)
        # OCR original
        text_orig = ocr_image(img)
        score_orig = arabic_score(text_orig)
        # OCR mirrored (handles sources where text appears reversed)
        img_flip = ImageOps.mirror(img)
        text_flip = ocr_image(img_flip)
        score_flip = arabic_score(text_flip)

        # Pick the better text
        if score_flip > max(score_orig, 0):
            used = "mirrored"
            text = text_flip
        else:
            used = "original"
            text = text_orig

        # Normalize lines and prepare helpful hints for the admin
        lines = [
            re.sub(r"\s+", " ", line_text).strip()
            for line_text in (text or "").splitlines()
            if line_text and line_text.strip()
        ]

        # Heuristic: collect lines that look like they include a class pattern (e.g., 7-1, 9-A)
        hints = []
        pat = re.compile(r"\b\d\s*[-–]\s*[A-Za-z0-9\u0621-\u064A]+\b")
        for line in lines:
            if pat.search(line):
                hints.append(line)

        csv_text = "teacher,class,subject,day,period\n"
        if hints:
            head = f"تم الاعتماد على نسخة {'المعكوسة' if used == 'mirrored' else 'الأصلية'} للصورة."
            warnings = head + "\n" + "\n".join([f"سطر محتمل: {h}" for h in hints[:30]])
            if len(hints) > 30:
                warnings += f"\n(+{len(hints)-30} أسطر أخرى)"
        else:
            warnings = (
                f"تم الاعتماد على نسخة {'المعكوسة' if used == 'mirrored' else 'الأصلية'} للصورة، "
                "لكن لم يتم التقاط أسطر مؤكدة تحتوي نمط صف (مثل 7-1).\n"
                "يمكنك مع ذلك نسخ/تحرير CSV يدويًا من المعاينة."
            )
        return csv_text, warnings
    except Exception as e:
        return "", f"فشل OCR للصورة: {e}"
