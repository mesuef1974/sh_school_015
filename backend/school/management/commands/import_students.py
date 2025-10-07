from __future__ import annotations

from typing import Optional
import re
from datetime import datetime, date

from django.core.management.base import BaseCommand, CommandParser, CommandError
from django.db import transaction, connection
from django.core.management.color import no_style
import os

import pandas as pd

from school.models import Student, Class


def _to_bool_needs(val: object) -> bool:
    if val is None:
        return False
    s = str(val).strip().lower()
    return s in {"yes", "y", "true", "1", "نعم", "نعم.", "✓"}


def _norm_text(val: object) -> str:
    if val is None:
        return ""
    s = str(val).strip()
    if s in {"-", "--", "none", "null", "nan", ""}:
        return ""
    return s


def _parse_date(val: object) -> Optional[date]:
    if val in (None, "", "-"):
        return None
    if isinstance(val, (datetime, date)):
        return val.date() if isinstance(val, datetime) else val
    s = str(val).strip()
    # Try common formats like '14/08/2007 12:00:00 ص'
    for fmt in [
        "%d/%m/%Y %I:%M:%S %p",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
        "%Y-%m-%d",
    ]:
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            pass
    # Fallback: pandas to_datetime with safe handling of NaT
    try:
        ts = pd.to_datetime(s, dayfirst=True, errors="coerce")
        # If parsing failed, ts will be NaT which is considered NaN by pandas
        if pd.isna(ts):
            return None
        # If timezone-aware, convert to naive date
        try:
            return ts.date()
        except Exception:
            # As a last resort, cast to Python datetime first if possible
            try:
                return pd.Timestamp(ts).to_pydatetime().date()
            except Exception:
                return None
    except Exception:
        return None


def _digits_prefix(s: str) -> Optional[int]:
    m = re.match(r"^(\d+)", s or "")
    if m:
        try:
            return int(m.group(1))
        except Exception:
            return None
    return None


class Command(BaseCommand):
    help = (
        "Import/update students from an Excel file (idempotent by national_no). "
        "Supports multi-sheet workbooks."
    )

    def _build_nationality_map(self, xlsx_path: Optional[str]) -> dict[str, str]:
        mapping: dict[str, str] = {}
        if not xlsx_path:
            return mapping
        try:
            if not os.path.exists(xlsx_path):
                self.stdout.write(
                    self.style.WARNING(f"Nationality file not found (ignored): {xlsx_path}")
                )
                return mapping
            # Read all sheets to be safe
            book = pd.read_excel(xlsx_path, sheet_name=None, engine="openpyxl")
            for _, df in (book or {}).items():
                if df is None or df.empty:
                    continue
                cols = [str(c).strip() for c in df.columns]
                df = df.copy()
                df.columns = cols
                # Support Arabic/English header variations
                # Try to form normalized columns
                if "national_no" not in df.columns:
                    for alt in (
                        "الرقم الوطني",
                        "national id",
                        "SID",
                        "sid",
                        "student_id",
                        "id",
                    ):
                        if alt in df.columns:
                            df["national_no"] = df[alt]
                            break
                if "nationality" not in df.columns:
                    for alt in ("الجنسية", "Nationality", "nation", "country"):
                        if alt in df.columns:
                            df["nationality"] = df[alt]
                            break
                # Build mapping
                for _, row in df.iterrows():
                    nat_no = _norm_text(row.get("national_no"))
                    if not nat_no:
                        continue
                    nat_val = _norm_text(row.get("nationality"))
                    if not nat_val:
                        continue
                    # First wins; don't overwrite
                    mapping.setdefault(nat_no, nat_val)
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Failed to read nationality file: {e}"))
        return mapping

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "excel_path",
            type=str,
            help="Path to new_studants.xlsx",
        )
        parser.add_argument(
            "--nationality-xlsx",
            dest="nationality_xlsx",
            default=None,
            help=(
                "Optional path to students_03.xlsx to take Nationality values from "
                "(matched by national_no)"
            ),
        )
        parser.add_argument(
            "--wipe",
            action="store_true",
            help="Delete ALL existing students before import (use with care)",
        )
        # Arabic-friendly alias for 'import on clean' (استيراد على نظافة)
        parser.add_argument(
            "--clean",
            dest="wipe",
            action="store_true",
            help="استيراد على نظافة: يحذف كل سجلات الطلاب قبل الاستيراد",
        )
        parser.add_argument(
            "--sheet",
            dest="sheet_name",
            default=0,
            help="Sheet name or index (default 0). Use 'ALL' to process all sheets.",
        )
        parser.add_argument(
            "--all-sheets",
            action="store_true",
            help="Process all sheets in the workbook (alias of --sheet ALL)",
        )
        parser.add_argument(
            "--sheet-per-class",
            action="store_true",
            help=(
                "Treat each sheet as a class: if 'section' column is missing/empty, "
                "use the sheet name as section/class label; if 'grade' is missing, "
                "try to parse grade number from sheet name."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse and report without writing to the database",
        )
        parser.add_argument(
            "--expect-total",
            dest="expect_total",
            type=int,
            default=None,
            help=(
                "Optional: expected total number of students after import "
                "(will print a warning if it doesn't match)"
            ),
        )

    def _process_df(
        self,
        df: pd.DataFrame,
        *,
        dry: bool,
        sheet_name: str | None,
        per_sheet_class: bool,
        nat_map: dict[str, str] | None = None,
    ) -> tuple[int, int, int, int]:
        # Normalize column names by stripping spaces
        df = df.copy()
        df.columns = [str(c).strip() for c in df.columns]

        # Expected columns (case-sensitive as provided by the user example)
        col_map = {
            "national_no": "national_no",
            "studant_name": "full_name",
            "studant_englisf_name": "english_name",
            "date_of_birth": "dob",
            "needs": "needs",
            "grade": "grade_label",
            "section": "section_label",
            "stu_phone_no": "phone_no",
            "stu_email": "email",
            "parent_national_no": "parent_national_no",
            "parent_phone": "parent_phone",  # fallback/legacy
            "name_parent": "parent_name",
            "relation_parent": "parent_relation",
            "extra_phone_no": "extra_phone_no",
            "parent_email": "parent_email",
            "nationality": "nationality",
        }

        # Aliases for Arabic or alternative headers
        aliases = {
            "الجنسية": "nationality",
            # Parent phone Arabic/English aliases
            "جوال ولي الامر": "parent_phone",
            "رقم ولي الامر": "parent_phone",
            "هاتف ولي الامر": "parent_phone",
            "جوال_ولي_الامر": "parent_phone",
            "guardian_phone": "parent_phone",
            "guardian_mobile": "parent_phone",
            "parent_mobile": "parent_phone",
            "parent_phone_no": "parent_phone",  # the file uses this exact header
            # Student phone Arabic variants
            "جوال الطالب": "stu_phone_no",
            "رقم الطالب": "stu_phone_no",
            # Parent national no Arabic
            "الرقم الوطني لولي الأمر": "parent_national_no",
            # Parent name Arabic
            "اسم ولي الامر": "name_parent",
            # Parent relation Arabic
            "صلة القرابة": "relation_parent",
            # Parent email Arabic
            "ايميل ولي الامر": "parent_email",
            "البريد الالكتروني لولي الامر": "parent_email",
        }
        for src, dst in aliases.items():
            if src in df.columns and dst not in df.columns:
                df[dst] = df[src]

        missing = [c for c in col_map if c not in df.columns]
        if missing:
            self.stdout.write(
                self.style.WARNING(
                    f"Missing columns in Excel (will be treated as empty): {', '.join(missing)}"
                )
            )
            for c in missing:
                df[c] = None

        added = 0
        updated = 0
        skipped = 0
        errors = 0

        rows = df.to_dict(orient="records")

        default_section = sheet_name.strip() if (per_sheet_class and sheet_name) else ""
        default_grade_num = _digits_prefix(default_section) if default_section else None

        for row in rows:
            try:
                nat_no = _norm_text(row.get("national_no"))
                if not nat_no:
                    skipped += 1
                    continue

                # Map fields
                full_name = _norm_text(row.get("studant_name"))
                eng_name = _norm_text(row.get("studant_englisf_name"))
                needs = _to_bool_needs(row.get("needs"))
                grade_label = _norm_text(row.get("grade"))
                section_label = _norm_text(row.get("section"))

                # If sheet-per-class is enabled, fill missing section/grade from sheet name
                if per_sheet_class:
                    if not section_label:
                        section_label = default_section
                    if not grade_label and default_grade_num:
                        grade_label = str(default_grade_num)

                phone_no = _norm_text(row.get("stu_phone_no"))
                email = _norm_text(row.get("stu_email"))
                # Prefer explicit parent_national_no; fallback to legacy parent_phone if not present
                parent_national_no = _norm_text(row.get("parent_national_no")) or _norm_text(
                    row.get("parent_phone")
                )
                # Normalize guardian phones: split into individual numbers,
                # then map to primary/extra as requested
                raw_parent_phone = _norm_text(row.get("parent_phone"))
                raw_extra_phone = _norm_text(row.get("extra_phone_no"))

                def _extract_numbers(s: str) -> list[str]:
                    if not s:
                        return []
                    try:
                        nums = re.findall(r"\d{6,}", s)
                        # De-duplicate preserving order
                        seen = set()
                        out: list[str] = []
                        for n in nums:
                            if n not in seen:
                                seen.add(n)
                                out.append(n)
                        return out
                    except Exception:
                        return []

                parent_nums = _extract_numbers(raw_parent_phone)
                extra_nums = _extract_numbers(raw_extra_phone)
                parent_phone = ""
                # default to original text; will override with normalized if needed
                extra_phone_no = raw_extra_phone
                if parent_nums:
                    # Always take the first as primary
                    parent_phone = parent_nums[0]
                    # If there is a second number in the same field, place it into extra_phone_no
                    tail = parent_nums[1:]
                    if tail:
                        # Merge with any existing extra numbers
                        merged: list[str] = []
                        for n in tail + extra_nums:
                            if n not in merged:
                                merged.append(n)
                        if merged:
                            extra_phone_no = ", ".join(merged)
                        else:
                            extra_phone_no = ""
                    else:
                        # No second number; keep normalized existing extra if any
                        if extra_nums:
                            extra_phone_no = ", ".join(extra_nums)
                        else:
                            extra_phone_no = raw_extra_phone
                else:
                    # No primary found; fallback: use extra as primary if available
                    if extra_nums:
                        parent_phone = extra_nums[0]
                        # Rest of extra become extra_phone_no
                        if len(extra_nums) > 1:
                            extra_phone_no = ", ".join(extra_nums[1:])
                        else:
                            extra_phone_no = ""
                    else:
                        parent_phone = raw_parent_phone
                        extra_phone_no = raw_extra_phone
                parent_name = _norm_text(row.get("name_parent"))
                parent_relation = _norm_text(row.get("relation_parent"))
                parent_email = _norm_text(row.get("parent_email"))
                nationality = _norm_text(row.get("nationality"))
                if (not nationality) and nat_map is not None and nat_no in nat_map:
                    nationality = nat_map.get(nat_no, "")
                dob = _parse_date(row.get("date_of_birth"))

                # Find or create student by national_no (idempotent)
                stu = Student.objects.filter(national_no=nat_no).first()
                created = False
                if not stu:
                    # Fallback: if a pre-existing record uses this value as SID, reuse it
                    stu = Student.objects.filter(sid=nat_no).first()
                if not stu:
                    stu = Student(national_no=nat_no, sid=nat_no)
                    created = True

                # Update fields
                if full_name:
                    stu.full_name = full_name
                stu.english_name = eng_name
                stu.needs = needs
                stu.grade_label = grade_label
                stu.section_label = section_label
                stu.phone_no = phone_no
                stu.email = email
                stu.parent_national_no = parent_national_no
                stu.parent_phone = parent_phone
                stu.parent_name = parent_name
                stu.parent_relation = parent_relation
                stu.extra_phone_no = extra_phone_no
                stu.parent_email = parent_email
                stu.nationality = nationality
                if not stu.national_no:
                    stu.national_no = nat_no
                if dob:
                    stu.dob = dob

                # Link/maybe create Class from grade/section using standardized
                # name "<grade>-<section>"
                class_obj = None
                if section_label or grade_label:
                    # Parse grade number and section code
                    grade_num = _digits_prefix(grade_label or "")
                    sec_label = section_label or ""
                    sec_code = ""
                    try:
                        s = sec_label.strip()
                        # If pattern like "7/1" or "7-1"
                        m = re.match(r"^(\d+)[\-/](.+)$", s)
                        if m and not grade_num:
                            grade_num = int(m.group(1))
                            sec_code = m.group(2).strip()
                        else:
                            # Extract section part after first '/' or '-' if present
                            if "/" in s or "-" in s:
                                parts = re.split(r"[\-/]", s, maxsplit=1)
                                if len(parts) == 2:
                                    sec_code = parts[1].strip()
                            else:
                                sec_code = s
                        # If still no grade, try to infer from section_label leading digits
                        if not grade_num:
                            grade_num = _digits_prefix(s or "")
                    except Exception:
                        pass

                    std_name = None
                    if grade_num and sec_code:
                        std_name = f"{grade_num}-{sec_code}"

                    # Lookup order: standardized name -> by (grade, section) ->
                    # legacy names (raw, grade/section)
                    if std_name:
                        class_obj = Class.objects.filter(name=std_name).first()
                    if not class_obj and (grade_num is not None) and (sec_code != ""):
                        class_obj = Class.objects.filter(grade=grade_num, section=sec_code).first()
                    if not class_obj and sec_label:
                        class_obj = Class.objects.filter(name=sec_label).first()
                    if not class_obj and grade_num and sec_code:
                        legacy = f"{grade_num}/{sec_code}"
                        class_obj = Class.objects.filter(name=legacy).first()

                    if not class_obj:
                        class_obj = Class.objects.create(
                            name=std_name or (sec_label or str(grade_num) or ""),
                            grade=int(grade_num) if grade_num else 0,
                            section=sec_code or "",
                        )
                    else:
                        # Ensure grade/section fields are updated to parsed values when available
                        updates = []
                        if grade_num and class_obj.grade != int(grade_num):
                            class_obj.grade = int(grade_num)
                            updates.append("grade")
                        if sec_code != "" and class_obj.section != sec_code:
                            class_obj.section = sec_code
                            updates.append("section")
                        if updates:
                            class_obj.save(update_fields=updates)

                stu.class_fk = class_obj

                if dry:
                    # Do not write to DB, just count
                    if created:
                        added += 1
                    else:
                        updated += 1
                else:
                    stu.save()
                    if created:
                        added += 1
                    else:
                        updated += 1
            except Exception as e:
                errors += 1
                self.stderr.write(f"[row error] {e}")

        return added, updated, skipped, errors

    def handle(self, *args, **options):
        path = options["excel_path"]
        # Friendly check before pandas tries to open the file
        if not os.path.exists(path):
            raise CommandError(
                (
                    f"Excel file not found: {path}\n"
                    "- تأكد من كتابة المسار الكامل الصحيح للملف (مثال: "
                    "D:\\sh_school_015\\DOC\\school_DATA\\new_studants.xlsx)\n"
                    "- على PowerShell ضَع المسار بين علامات اقتباس، واستخدم شرطة خلفية "
                    "مزدوجة \\\\ داخل السلاسل Python.\n"
                    "- لا تستخدم النماذج التوضيحية مثل ...xlsx — ضع المسار الحقيقي."
                )
            )
        sheet = options.get("sheet_name", 0)
        all_sheets = bool(options.get("all_sheets"))
        per_sheet_class = bool(options.get("sheet_per_class"))
        dry = bool(options.get("dry_run"))
        wipe = bool(options.get("wipe"))
        nat_path = options.get("nationality_xlsx")

        # Optional nationality mapping
        nat_map = self._build_nationality_map(nat_path)

        # Treat --all-sheets as --sheet ALL
        if all_sheets:
            sheet = "ALL"

        total_added = total_updated = total_skipped = total_errors = 0

        # If requested, wipe students before import (not in dry-run)
        if wipe and not dry:
            with transaction.atomic():
                deleted, _ = Student.objects.all().delete()
                # Reset Student ID sequence so new IDs start from 1 after clean wipe
                try:
                    sql_list = connection.ops.sequence_reset_sql(no_style(), [Student])
                    with connection.cursor() as cursor:
                        for sql in sql_list:
                            cursor.execute(sql)
                    self.stdout.write(
                        self.style.WARNING(
                            f"Deleted {deleted} existing Student rows before import. "
                            "(Reset PK sequence)"
                        )
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Deleted {deleted} existing Student rows before import. "
                            f"(Sequence reset skipped: {e})"
                        )
                    )

        if isinstance(sheet, str) and sheet.strip().upper() == "ALL":
            # Load all sheets as dict: name -> DataFrame
            book = pd.read_excel(path, sheet_name=None, engine="openpyxl")
            if not book:
                self.stdout.write(self.style.WARNING("No sheets found in workbook."))
                return
            for sh_name, df in book.items():
                self.stdout.write(self.style.HTTP_INFO(f"[sheet] Processing: {sh_name}"))
                a, u, s, e = self._process_df(
                    df,
                    dry=dry,
                    sheet_name=sh_name,
                    per_sheet_class=per_sheet_class,
                    nat_map=nat_map,
                )
                total_added += a
                total_updated += u
                total_skipped += s
                total_errors += e
            msg = (
                "Students import (all sheets) completed. "
                f"Added={total_added}, Updated={total_updated}, "
                f"Skipped(no national_no)={total_skipped}, Errors={total_errors}"
            )
            if dry:
                self.stdout.write(self.style.WARNING("[DRY RUN] " + msg))
            else:
                self.stdout.write(self.style.SUCCESS(msg))
                # Optional final count check
                expect = options.get("expect_total")
                if expect is not None:
                    total_db = Student.objects.count()
                    if total_db != int(expect):
                        self.stdout.write(
                            self.style.WARNING(
                                f"[check] Current total students={total_db} != expected {expect}"
                            )
                        )
                    else:
                        self.stdout.write(
                            self.style.SUCCESS(f"[check] Total students match expected: {expect}")
                        )
        else:
            df = pd.read_excel(path, sheet_name=sheet, engine="openpyxl")
            a, u, s, e = self._process_df(
                df,
                dry=dry,
                sheet_name=str(sheet) if sheet is not None else None,
                per_sheet_class=per_sheet_class,
                nat_map=nat_map,
            )
            if dry:
                self.stdout.write(
                    self.style.WARNING(
                        "[DRY RUN] Students import completed. "
                        "Added={a}, Updated={u}, "
                        "Skipped(no national_no)={s}, Errors={e}"
                    ).format(a=a, u=u, s=s, e=e)
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        "Students import completed. "
                        "Added={a}, Updated={u}, "
                        "Skipped(no national_no)={s}, Errors={e}"
                    ).format(a=a, u=u, s=s, e=e)
                )
                # Optional final count check
                expect = options.get("expect_total")
                if expect is not None:
                    total_db = Student.objects.count()
                    if total_db != int(expect):
                        self.stdout.write(
                            self.style.WARNING(
                                f"[check] Current total students={total_db} != expected {expect}"
                            )
                        )
                    else:
                        self.stdout.write(
                            self.style.SUCCESS(f"[check] Total students match expected: {expect}")
                        )
