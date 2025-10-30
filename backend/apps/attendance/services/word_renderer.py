from __future__ import annotations
from io import BytesIO
from pathlib import Path
from typing import Any

from docxtpl import DocxTemplate  # type: ignore
from django.utils import timezone

# NOTE: Using the path provided by the user for the Tanbih.docx template
TEMPLATE_PATH = Path(r"D:\sh_school_015\DOC\نماذج الغياب\Tanbih.docx")


def render_alert_docx(alert: Any) -> bytes:
    """Render the Absence Alert DOCX using the Tanbih.docx template.
    The template must contain placeholders matching the context keys below.
    """
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"Template not found: {TEMPLATE_PATH}")
    doc = DocxTemplate(str(TEMPLATE_PATH))
    ctx = {
        "number": alert.number,
        "academic_year": alert.academic_year,
        "student_name": getattr(alert.student, "full_name", getattr(alert.student, "name", "")),
        "class_name": getattr(alert, "class_name", ""),
        "student_pid": getattr(alert.student, "sid", getattr(alert.student, "national_id", "")),
        "parent_name": getattr(alert, "parent_name", ""),
        "parent_mobile": getattr(alert, "parent_mobile", ""),
        "excused_days": alert.excused_days,
        "unexcused_days": alert.unexcused_days,
        "period_start": alert.period_start.strftime("%d/%m/%Y"),
        "period_end": alert.period_end.strftime("%d/%m/%Y"),
        "user_name": getattr(getattr(alert, "created_by", None), "get_full_name", lambda: "")(),
        "today": timezone.localdate().strftime("%d/%m/%Y"),
    }
    doc.render(ctx)
    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()