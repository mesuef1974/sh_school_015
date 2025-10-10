from django import forms
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.db import IntegrityError, connection, transaction
from django.core.paginator import Paginator
from django.http import Http404, StreamingHttpResponse
from .models import (
    Class,
    Student,
    Staff,
    Subject,
    TeachingAssignment,
    ClassSubject,
)
from .serializers import (
    ClassSerializer,
    StudentSerializer,
    StaffSerializer,
    SubjectSerializer,
    TeachingAssignmentSerializer,
    ClassSubjectSerializer,
)
import re
from openpyxl import load_workbook
from .services.imports import import_teacher_loads


class ClassViewSet(ModelViewSet):
    queryset = Class.objects.all()
    serializer_class = ClassSerializer
    permission_classes = [IsAuthenticated]


class StudentViewSet(ModelViewSet):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    permission_classes = [IsAuthenticated]


class StaffViewSet(ModelViewSet):
    queryset = Staff.objects.all()
    serializer_class = StaffSerializer
    permission_classes = [IsAuthenticated]


class SubjectViewSet(ModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    permission_classes = [IsAuthenticated]


class ClassSubjectViewSet(ModelViewSet):
    queryset = ClassSubject.objects.select_related("classroom", "subject").all()
    serializer_class = ClassSubjectSerializer
    permission_classes = [IsAuthenticated]


class TeachingAssignmentViewSet(ModelViewSet):
    queryset = TeachingAssignment.objects.select_related("teacher", "classroom", "subject").all()
    serializer_class = TeachingAssignmentSerializer
    permission_classes = [IsAuthenticated]


class TeachingAssignmentForm(forms.ModelForm):
    class Meta:
        model = TeachingAssignment
        fields = ["teacher", "classroom", "subject", "no_classes_weekly", "notes"]


# Generic CRUD forms for editable tables
class ClassForm(forms.ModelForm):
    class Meta:
        model = Class
        # Include common fields; adjust as per actual model fields in project
        fields = [
            f.name for f in Class._meta.fields if f.editable and f.name != Class._meta.pk.name
        ]


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = [
            f.name for f in Student._meta.fields if f.editable and f.name != Student._meta.pk.name
        ]


class StaffForm(forms.ModelForm):
    class Meta:
        model = Staff
        fields = [
            f.name for f in Staff._meta.fields if f.editable and f.name != Staff._meta.pk.name
        ]


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = [
            f.name for f in Subject._meta.fields if f.editable and f.name != Subject._meta.pk.name
        ]


class ClassSubjectForm(forms.ModelForm):
    class Meta:
        model = ClassSubject
        fields = [
            f.name
            for f in ClassSubject._meta.fields
            if f.editable and f.name != ClassSubject._meta.pk.name
        ]


class ExcelUploadForm(forms.Form):
    file = forms.FileField(label="ملف Excel للأنصبة (schasual.xlsx)")


@login_required
def teacher_loads_dashboard(request):
    from django.conf import settings
    from django.utils import timezone
    from django.db.models import Sum, Count, F, Q

    # Handle manual add
    if request.method == "POST" and request.POST.get("action") == "add":
        form = TeachingAssignmentForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect(reverse("teacher_loads_dashboard"))
    else:
        form = TeachingAssignmentForm()

    # Handle Excel upload (gated by feature flag)
    imports_disabled = getattr(settings, "DISABLE_IMPORTS", False)
    if request.method == "POST" and request.POST.get("action") == "upload_async":
        # Enqueue background import via RQ
        if imports_disabled:
            messages.warning(request, "تم تعطيل الاستيراد مؤقتًا بواسطة إعداد النظام.")
            return redirect(reverse("teacher_loads_dashboard"))
        up_form = ExcelUploadForm(request.POST, request.FILES)
        if up_form.is_valid():
            from django_rq import get_queue
            from .tasks.jobs_rq import enqueue_import_teacher_loads

            dry_run_flag = (
                request.POST.get("dry_run") or request.GET.get("dry_run") or ""
            ).strip() in ("1", "true", "True")
            file_obj = up_form.cleaned_data["file"]
            file_bytes = file_obj.read()
            q = get_queue("default")
            job = enqueue_import_teacher_loads(q, file_bytes, dry_run=dry_run_flag)
            messages.info(
                request,
                ("[Dry-run] " if dry_run_flag else "")
                + f"تم إرسال مهمة الاستيراد إلى الخلفية. رقم المهمة: {job.id}",
            )
            return redirect(reverse("job_status", kwargs={"job_id": job.id}))
    elif request.method == "POST" and request.POST.get("action") == "upload":
        if imports_disabled:
            messages.warning(request, "تم تعطيل الاستيراد مؤقتًا بواسطة إعداد النظام.")
            return redirect(reverse("teacher_loads_dashboard"))
        up_form = ExcelUploadForm(request.POST, request.FILES)
        if up_form.is_valid():
            dry_run_flag = (
                request.POST.get("dry_run") or request.GET.get("dry_run") or ""
            ).strip() in ("1", "true", "True")
            summary = import_teacher_loads(up_form.cleaned_data["file"], dry_run=dry_run_flag)
            messages.info(
                request,
                (
                    ("[Dry-run] " if dry_run_flag else "")
                    + (
                        f"تمت معالجة {summary['rows_processed']} صفاً عبر {summary['worksheets']} ورقة. "
                        f"مواد جديدة: {summary['subjects_created']}, مواد-صفوف جديدة: {summary['classsubjects_created']}, "
                        f"أنصبة مضافة: {summary['assignments_created']}, أنصبة محدّثة: {summary['assignments_updated']}. "
                        f"تخطّي: معلّم غير معروف={summary['skipped_no_teacher']}, صف غير معروف={summary['skipped_no_class']}, مادة غير معروفة={summary['skipped_no_subject']}."
                    )
                ),
            )
            return redirect(reverse("teacher_loads_dashboard"))
    elif request.method == "POST" and request.POST.get("action") == "upload_default":
        if imports_disabled:
            messages.warning(request, "تم تعطيل الاستيراد مؤقتًا بواسطة إعداد النظام.")
            return redirect(reverse("teacher_loads_dashboard"))
        # Import from the known default path on the server
        from pathlib import Path

        repo_root = Path(__file__).resolve().parents[2]
        default_path = repo_root / "DOC" / "school_DATA" / "schasual.xlsx"
        dry_run_flag = (
            request.POST.get("dry_run") or request.GET.get("dry_run") or ""
        ).strip() in ("1", "true", "True")
        try:
            with open(default_path, "rb") as f:
                summary = import_teacher_loads(f, dry_run=dry_run_flag)
                messages.info(
                    request,
                    (
                        ("[Dry-run] " if dry_run_flag else "")
                        + (
                            f"تمت معالجة {summary['rows_processed']} صفاً عبر {summary['worksheets']} ورقة. "
                            f"مواد جديدة: {summary['subjects_created']}, مواد-صفوف جديدة: {summary['classsubjects_created']}, "
                            f"أنصبة مضافة: {summary['assignments_created']}, أنصبة محدّثة: {summary['assignments_updated']}. "
                            f"تخطّي: معلّم غير معروف={summary['skipped_no_teacher']}, صف غير معروف={summary['skipped_no_class']}, مادة غير معروفة={summary['skipped_no_subject']}."
                        )
                    ),
                )
        except FileNotFoundError:
            messages.error(request, f"لم يتم العثور على الملف: {default_path}")
        return redirect(reverse("teacher_loads_dashboard"))
    else:
        up_form = ExcelUploadForm()

    # Filters and search
    teacher_q = request.GET.get("teacher")
    grade_q = request.GET.get("grade")
    section_q = request.GET.get("section")
    subject_q = request.GET.get("subject")
    q_text = (request.GET.get("q") or "").strip()

    # Build base query string for sorting/links
    from urllib.parse import urlencode

    params = {}
    if teacher_q:
        params["teacher"] = teacher_q
    if grade_q:
        params["grade"] = grade_q
    if section_q:
        params["section"] = section_q
    if subject_q:
        params["subject"] = subject_q
    if q_text:
        params["q"] = q_text
    base_query = urlencode(params, doseq=True)
    base_prefix = "?" + base_query + ("&" if base_query else "")

    qs = TeachingAssignment.objects.select_related("teacher", "classroom", "subject").all()
    if teacher_q:
        qs = qs.filter(teacher_id=teacher_q)
    if grade_q:
        qs = qs.filter(classroom__grade=grade_q)
    if section_q:
        qs = qs.filter(classroom__section=section_q)
    if subject_q:
        qs = qs.filter(subject_id=subject_q)
    if q_text:
        qs = qs.filter(
            Q(teacher__full_name__icontains=q_text)
            | Q(subject__name_ar__icontains=q_text)
            | Q(classroom__name__icontains=q_text)
            | Q(classroom__section__icontains=q_text)
            | Q(classroom__grade__icontains=q_text)
        )

    # Sorting (safe mapping)
    sort_key = (request.GET.get("sort") or "").strip()
    sort_dir = (request.GET.get("dir") or "asc").lower()
    allowed = {
        "teacher": "teacher__full_name",
        "grade": "classroom__grade",
        "section": "classroom__section",
        "subject": "subject__name_ar",
        "weekly": "no_classes_weekly",
    }
    if sort_key in allowed:
        field = allowed[sort_key]
        if sort_dir == "desc":
            qs = qs.order_by(f"-{field}")
        else:
            qs = qs.order_by(field)
    else:
        # Default order
        qs = qs.order_by("teacher__full_name", "classroom__grade", "classroom__section")

    # KPI stats
    today = timezone.localdate()
    total_assignments = TeachingAssignment.objects.count()
    todays_assignments = TeachingAssignment.objects.filter(created_at__date=today).count()

    # Determine latest update timestamp across assignments
    latest_dt = (
        TeachingAssignment.objects.order_by("-updated_at")
        .values_list("updated_at", flat=True)
        .first()
        or TeachingAssignment.objects.order_by("-created_at")
        .values_list("created_at", flat=True)
        .first()
    )
    latest_date = latest_dt.date() if latest_dt else None

    # Top teachers by weekly load (sum no_classes_weekly) for latest snapshot if available
    ta_qs_for_charts = TeachingAssignment.objects.all()

    agg = (
        ta_qs_for_charts.values("teacher__full_name")
        .annotate(total=Sum("no_classes_weekly"))
        .order_by("-total")[:10]
    )
    top_teachers_labels = [a["teacher__full_name"] for a in agg]
    top_teachers_values = [a["total"] or 0 for a in agg]

    # Coverage: ClassSubjects that have at least one assignment vs gaps with none
    cs = ClassSubject.objects.values("classroom_id", "subject_id", "classroom__grade").annotate(
        assignments_count=Count(
            "classroom__assignments",
            filter=Q(classroom__assignments__subject=F("subject_id")),
        )
    )
    covered = 0
    gaps = 0
    # Per-grade coverage tallies
    per_grade = {}
    for x in cs:
        cnt = x.get("assignments_count") or 0
        grade = x.get("classroom__grade")
        if grade is None:
            continue
        if grade not in per_grade:
            per_grade[grade] = {"covered": 0, "gaps": 0}
        if cnt > 0:
            covered += 1
            per_grade[grade]["covered"] += 1
        else:
            gaps += 1
            per_grade[grade]["gaps"] += 1

    # Prepare arrays for stacked bar chart by grade
    grades_sorted = sorted(per_grade.keys())
    coverage_by_grade_labels = [str(g) for g in grades_sorted]
    coverage_by_grade_covered = [per_grade[g]["covered"] for g in grades_sorted]
    coverage_by_grade_gaps = [per_grade[g]["gaps"] for g in grades_sorted]

    # Compute KPI: total weekly assignments (sum of no_classes_weekly)
    weekly_total = (
        TeachingAssignment.objects.aggregate(total=Sum("no_classes_weekly")).get("total") or 0
    )
    gaps_count = gaps  # reuse computed total gaps from coverage aggregation

    # Build a concrete list of gaps (ClassSubject with no assignment) for display box
    gaps_qs = (
        ClassSubject.objects.select_related("classroom", "subject")
        .annotate(
            assignments_count=Count(
                "classroom__assignments",
                filter=Q(classroom__assignments__subject=F("subject_id")),
            )
        )
        .filter(assignments_count=0)
        .order_by("classroom__grade", "classroom__section", "subject__name_ar", "id")
    )
    # Keep it compact: cap at first 100 rows for the dashboard box
    gaps_items = [
        {
            "grade": cs.classroom.grade,
            "section": (cs.classroom.section or ""),
            "subject": cs.subject.name_ar,
        }
        for cs in gaps_qs[:100]
    ]

    # Compute next sort direction per column to avoid template boolean expressions
    _current_sort = sort_key or ""
    _current_dir = sort_dir or "asc"

    def _next_dir(col: str) -> str:
        return "desc" if (_current_sort == col and _current_dir == "asc") else "asc"

    context = {
        "form": form,
        "upload_form": up_form,
        "assignments": qs,
        "teachers": Staff.objects.all(),
        "classes": Class.objects.all(),
        "subjects": Subject.objects.all(),
        "grades": sorted({c.grade for c in Class.objects.all()}),
        "sections": sorted({(c.section or "") for c in Class.objects.all()}),
        "title": "لوحة الأنصبة — إدخال ورفع Excel",
        "show_imports": not imports_disabled,
        # current filters/search/sort
        "q_text": q_text,
        "teacher_q": teacher_q,
        "grade_q": grade_q,
        "section_q": section_q,
        "subject_q": subject_q,
        "sort_key": sort_key,
        "sort_dir": sort_dir,
        "base_query": base_query,
        "base_prefix": base_prefix,
        # precomputed next sort dirs
        "ndir_teacher": _next_dir("teacher"),
        "ndir_grade": _next_dir("grade"),
        "ndir_section": _next_dir("section"),
        "ndir_subject": _next_dir("subject"),
        "ndir_weekly": _next_dir("weekly"),
        # KPIs
        "kpi_total_assignments": total_assignments,
        "kpi_todays_assignments": todays_assignments,
        "kpi_weekly_total": weekly_total,
        "kpi_gaps_count": gaps_count,
        # latest snapshot info for charts
        "charts_latest_date": latest_date,
        # Charts data
        "chart_top_teachers_labels": top_teachers_labels,
        "chart_top_teachers_values": top_teachers_values,
        "chart_coverage": {"covered": covered, "gaps": gaps},
        "chart_coverage_by_grade_labels": coverage_by_grade_labels,
        "chart_coverage_by_grade_covered": coverage_by_grade_covered,
        "chart_coverage_by_grade_gaps": coverage_by_grade_gaps,
        # gaps box data
        "gaps_items": gaps_items,
    }
    # HTMX partial update for assignments table
    if request.headers.get("HX-Request"):
        return render(request, "school/_assignments_table.html", context)
    return render(request, "school/teacher_loads_dashboard.html", context)


@login_required
def teacher_class_matrix(request):
    """Matrix: rows=teachers, columns=classes, cells=sum of weekly lessons teacher gives to that class.
    Professional RTL table with sticky headers.
    """
    # Get classes (columns) sorted by grade then section then id
    classes = Class.objects.all().order_by("grade", "section", "id")
    class_list = list(classes)

    # Get teachers (rows) who have at least one assignment
    # Order teachers by specialization (primary subject) then by name
    from django.db.models import Subquery, OuterRef, Min

    primary_subquery = Subquery(
        TeachingAssignment.objects.filter(teacher_id=OuterRef("pk"))
        .values("teacher_id")
        .annotate(primary=Min("subject__name_ar"))
        .values("primary")[:1]
    )

    teachers = (
        Staff.objects.filter(assignments__isnull=False)
        .distinct()
        .annotate(primary_subject=primary_subquery)
        .order_by("primary_subject", "full_name", "id")
    )
    teacher_list = list(teachers)

    # Build mapping (teacher_id, class_id) -> total weekly lessons
    from django.db.models import Sum

    agg = TeachingAssignment.objects.values("teacher_id", "classroom_id").annotate(
        total=Sum("no_classes_weekly")
    )
    matrix = {(a["teacher_id"], a["classroom_id"]): (a["total"] or 0) for a in agg}

    # Precompute rows (cells ordered by class_list) and row totals
    cells_by_teacher = {}
    row_totals = {}
    for t in teacher_list:
        row = []
        s = 0
        for c in class_list:
            v = matrix.get((t.id, c.id), 0) or 0
            row.append(v)
            s += v
        cells_by_teacher[t.id] = row
        row_totals[t.id] = s

    # Column totals in class order
    col_totals_list = []
    for idx, c in enumerate(class_list):
        s = 0
        for t in teacher_list:
            s += cells_by_teacher[t.id][idx]
        col_totals_list.append(s)

    grand_total = sum(row_totals.values())

    # Labels for columns: grade-section (e.g., 7-A)
    def _cls_label(c: Class) -> str:  # type: ignore[name-defined]
        sec = (c.section or "").strip()
        if sec:
            return f"{c.grade}-{sec}"
        return str(c.grade)

    # Build rows for easier templating
    rows = []
    for t in teacher_list:
        rows.append(
            {
                "teacher": t,
                "cells": cells_by_teacher[t.id],
                "total": row_totals[t.id],
            }
        )

    # Coverage gaps across ClassSubject pairs: count pairs with no assignment
    from django.db.models import Count, F, Q as _Q

    cs = ClassSubject.objects.values("classroom_id", "subject_id").annotate(
        assignments_count=Count(
            "classroom__assignments",
            filter=_Q(classroom__assignments__subject=F("subject_id")),
        )
    )
    gaps_count = 0
    for x in cs:
        if not (x.get("assignments_count") or 0):
            gaps_count += 1

    context = {
        "title": "مصفوفة الأنصبة — معلّم × صف",
        "rows": rows,
        "classes": class_list,
        "cls_label": _cls_label,
        "col_totals_list": col_totals_list,
        "grand_total": grand_total,
        "gaps_count": gaps_count,
    }

    return render(request, "school/teacher_class_matrix.html", context)


def _normalize_ar_text(s: str) -> str:
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
    return s


def _import_excel_file(file_obj, dry_run: bool = False):
    wb = load_workbook(filename=file_obj, data_only=True)

    # Build teacher index (normalized)
    teacher_index = {}
    for t in Staff.objects.all():
        key = _normalize_ar_text(t.full_name).replace(" ", "").lower()
        if key:
            teacher_index.setdefault(key, t)

    # Build class index by (grade, section) and by name
    classes = Class.objects.all()
    class_by_grade_section = {(c.grade, (c.section or "").strip()): c for c in classes}
    class_by_name = {_normalize_ar_text(c.name): c for c in classes}

    # Subject index
    subject_by_norm = {_normalize_ar_text(s.name_ar): s for s in Subject.objects.all()}

    summary = {
        "subjects_created": 0,
        "classsubjects_created": 0,
        "assignments_created": 0,
        "assignments_updated": 0,
        "skipped_no_teacher": 0,
        "skipped_no_class": 0,
        "skipped_no_subject": 0,
        "worksheets": 0,
        "rows_processed": 0,
    }

    # Use a savepoint so we can rollback for dry_run without affecting outer transactions
    sid = transaction.savepoint()
    try:
        for ws in wb.worksheets:
            summary["worksheets"] += 1
            # Try detect headers positions
            header_row = None
            col_map = {
                "teacher": None,
                "grade": None,
                "section": None,
                "subject": None,
                "weekly": None,
            }
            for r in range(1, 11):
                try:
                    vals = [
                        c if c is not None else ""
                        for c in next(ws.iter_rows(min_row=r, max_row=r, values_only=True))
                    ]
                except StopIteration:
                    break
                normed = [_normalize_ar_text(v).replace(" ", "").lower() for v in vals]
                tokens = {
                    "teacher": {
                        "teachername",
                        "teacher",
                        "اسمالمعلم",
                        "اسمالمعلّم",
                        "المعلم",
                    },
                    "grade": {"grade", "الصف", "المرحلة", "الصفالدراسي"},
                    "section": {"section", "الشعبة", "الفصل"},
                    "subject": {"class", "subject", "المادة", "المواد"},
                    "weekly": {
                        "no.classesw",
                        "weekly",
                        "weeklyclasses",
                        "الحصصالاسبوعية",
                        "الحصصالأسبوعية",
                        "حصصالاسبوع",
                    },
                }
                for i, v in enumerate(normed):
                    for k, opts in tokens.items():
                        if v in opts and col_map[k] is None:
                            col_map[k] = i
                if any(col_map.values()):
                    header_row = r
                    break
            if header_row is None:
                header_row = 1
                col_map = {
                    "teacher": 0,
                    "grade": 1,
                    "section": 2,
                    "subject": 3,
                    "weekly": 4,
                }

            current_teacher = None
            for row in ws.iter_rows(min_row=header_row + 1, values_only=True):
                if not row:
                    continue
                summary["rows_processed"] += 1
                # Carry-forward teacher if grouped
                tv = (
                    row[col_map["teacher"]]
                    if col_map["teacher"] is not None and col_map["teacher"] < len(row)
                    else None
                )
                teacher_display = str(tv).strip() if tv not in (None, "") else None
                if teacher_display:
                    current_teacher = teacher_display
                if not current_teacher:
                    summary["skipped_no_teacher"] += 1
                    continue

                gv = (
                    row[col_map["grade"]]
                    if col_map["grade"] is not None and col_map["grade"] < len(row)
                    else None
                )
                sv = (
                    row[col_map["section"]]
                    if col_map["section"] is not None and col_map["section"] < len(row)
                    else None
                )
                subjv = (
                    row[col_map["subject"]]
                    if col_map["subject"] is not None and col_map["subject"] < len(row)
                    else None
                )
                wv = (
                    row[col_map["weekly"]]
                    if col_map["weekly"] is not None and col_map["weekly"] < len(row)
                    else None
                )

                # Normalize
                t_key = _normalize_ar_text(current_teacher).replace(" ", "").lower()
                teacher = teacher_index.get(t_key)
                if not teacher:
                    summary["skipped_no_teacher"] += 1
                    continue

                def to_int_safe(x):
                    try:
                        return int(str(x).strip().split()[0])
                    except Exception:
                        return None

                grade = to_int_safe(gv)
                section = None
                if sv not in (None, ""):
                    section = re.sub(r"[^0-9A-Za-zأ-ي]", "", str(sv)).strip()
                subj_norm = _normalize_ar_text(subjv)
                weekly = to_int_safe(wv) or 0

                # Map class
                classroom = None
                if grade is not None:
                    classroom = class_by_grade_section.get((grade, section or ""))
                if classroom is None and subj_norm:
                    if grade is not None and section is not None:
                        key = f"{grade}{section}"
                        for cname, cobj in class_by_name.items():
                            if key in re.sub(r"\D", "", cname):
                                classroom = cobj
                                break
                if classroom is None:
                    summary["skipped_no_class"] += 1
                    continue

                # Subject
                if subj_norm:
                    subj_obj = subject_by_norm.get(subj_norm)
                    if not subj_obj:
                        subj_obj = Subject.objects.create(name_ar=subjv)
                        subject_by_norm[subj_norm] = subj_obj
                        summary["subjects_created"] += 1
                else:
                    summary["skipped_no_subject"] += 1
                    continue

                # Ensure the subject is assigned to the class
                _, cs_created = ClassSubject.objects.get_or_create(
                    classroom=classroom, subject=subj_obj
                )
                if cs_created:
                    summary["classsubjects_created"] += 1

                # Create/update teaching assignment
                _, created = TeachingAssignment.objects.update_or_create(
                    teacher=teacher,
                    classroom=classroom,
                    subject=subj_obj,
                    defaults={"no_classes_weekly": weekly or subj_obj.weekly_default or 0},
                )
                if created:
                    summary["assignments_created"] += 1
                else:
                    summary["assignments_updated"] += 1

        # Rollback changes if dry_run requested
        if dry_run:
            transaction.savepoint_rollback(sid)
        else:
            transaction.savepoint_commit(sid)
    except Exception:
        # In case of unexpected error, rollback to be safe
        transaction.savepoint_rollback(sid)
        raise

    return summary


def _staff_only(user):
    return user.is_authenticated and user.is_staff


@login_required
def job_status(request, job_id: str):
    """Simple job status page for background imports."""
    try:
        import django_rq
        from rq.job import Job
    except Exception:
        raise Http404("RQ not available")

    conn = django_rq.get_connection("default")
    try:
        job = Job.fetch(job_id, connection=conn)
    except Exception:
        raise Http404("Job not found")

    state = job.get_status(refresh=True)
    summary = (job.meta or {}).get("summary") if hasattr(job, "meta") else None
    context = {
        "title": f"حالة المهمة {job_id}",
        "job_id": job_id,
        "state": state,
        "summary": summary,
    }
    return render(request, "school/job_status.html", context)


@user_passes_test(_staff_only)
@login_required
def data_overview(request):
    # Denylist sensitive tables by prefix or exact names
    deny_exact = {"django_session"}
    deny_prefixes = ("auth_", "django_", "admin_")

    with connection.cursor() as cursor:
        introspection = connection.introspection
        tables = introspection.table_names()

    visible_tables = [
        t for t in tables if t not in deny_exact and not any(t.startswith(p) for p in deny_prefixes)
    ]

    # Get row counts efficiently
    table_stats = []
    with connection.cursor() as cursor:
        for t in visible_tables:
            try:
                cursor.execute(f'SELECT COUNT(*) FROM "{t}"')
                cnt = cursor.fetchone()[0]
            except Exception:
                cnt = None
            table_stats.append({"name": t, "count": cnt})

    context = {
        "title": "معاينة البيانات — كل الجداول",
        "tables": table_stats,
    }
    return render(request, "data/overview.html", context)


@user_passes_test(_staff_only)
@login_required
def data_table_detail(request, table):
    # Security: allow only public tables and apply same deny rules
    deny_exact = {"django_session"}
    deny_prefixes = ("auth_", "django_", "admin_")

    with connection.cursor() as cursor:
        introspection = connection.introspection
        all_tables = set(introspection.table_names())

    if (
        table not in all_tables
        or table in deny_exact
        or any(table.startswith(p) for p in deny_prefixes)
    ):
        raise Http404("Table not found")

    # Registry of editable tables
    MODEL_REGISTRY = {
        Class._meta.db_table: (Class, ClassForm),
        Student._meta.db_table: (Student, StudentForm),
        Staff._meta.db_table: (Staff, StaffForm),
        Subject._meta.db_table: (Subject, SubjectForm),
        ClassSubject._meta.db_table: (ClassSubject, ClassSubjectForm),
        TeachingAssignment._meta.db_table: (TeachingAssignment, TeachingAssignmentForm),
    }

    editable = table in MODEL_REGISTRY

    # Common query params
    q = (request.GET.get("q") or "").strip()
    order = request.GET.get("order") or ""
    page = int(request.GET.get("page") or 1)
    per_page = int(request.GET.get("per_page") or 25)

    if editable:
        Model, FormClass = MODEL_REGISTRY[table]
        # Build columns, include pk first for actions
        fields = [f for f in Model._meta.fields if f.editable or f.primary_key]
        columns = [Model._meta.pk.name] + [f.name for f in fields if f.name != Model._meta.pk.name]

        # Handle POST actions
        if request.method == "POST":
            # Helper to rebuild querystring preserving filters
            def _qs_keep(req, drop_keys=None):
                drop_keys = set(drop_keys or [])
                from urllib.parse import parse_qsl, urlencode

                pairs = [
                    (k, v)
                    for k, v in parse_qsl(req.META.get("QUERY_STRING", ""), keep_blank_values=True)
                    if k not in drop_keys
                ]
                return ("?" + urlencode(pairs, doseq=True)) if pairs else ""

            action = request.POST.get("action")
            if action == "create":
                form = FormClass(request.POST)
                if form.is_valid():
                    try:
                        form.save()
                        messages.success(request, "تمت الإضافة بنجاح.")
                    except IntegrityError as e:
                        messages.error(request, f"تعذر الحفظ بسبب قيود البيانات: {e}")
                        return redirect(request.path + _qs_keep(request))
                    return redirect(request.path + _qs_keep(request, drop_keys=["add"]))
            elif action == "update":
                pk = request.POST.get("id")
                instance = Model.objects.filter(pk=pk).first()
                if instance is not None:
                    form = FormClass(request.POST, instance=instance)
                    if form.is_valid():
                        try:
                            form.save()
                            messages.success(request, "تم حفظ التعديلات.")
                        except IntegrityError as e:
                            messages.error(request, f"تعذر الحفظ بسبب قيود البيانات: {e}")
                            return redirect(request.path + _qs_keep(request))
                        # Preserve current page filters
                        return redirect(request.path + _qs_keep(request, drop_keys=["edit"]))
            elif action == "delete":
                pk = request.POST.get("id")
                obj = Model.objects.filter(pk=pk).first()
                if obj is not None:
                    try:
                        obj.delete()
                        messages.success(request, "تم حذف السجل.")
                    except (ProtectedError, IntegrityError) as e:
                        messages.error(request, f"لا يمكن حذف السجل لارتباطه بسجلات أخرى: {e}")
                return redirect(request.path + _qs_keep(request))

        # Build queryset (use select_related for FK fields and keep objects for better display)
        qs = Model.objects.all()
        # Select related for FK fields to optimize display
        fk_fields = [
            f.name
            for f in Model._meta.fields
            if getattr(f, "is_relation", False) and getattr(f, "many_to_one", False)
        ]
        if fk_fields:
            qs = qs.select_related(*fk_fields)
        if q:
            # Apply search across textual fields
            text_fields = [
                f.name
                for f in Model._meta.fields
                if getattr(f, "get_internal_type", lambda: "")() in ("CharField", "TextField")
            ]
            query = Q()
            for name in text_fields:
                query |= Q(**{f"{name}__icontains": q})
            if query:
                qs = qs.filter(query)
        if order:
            if order.lstrip("-") in columns:
                qs = qs.order_by(order)
        else:
            # Ensure deterministic ordering for pagination to avoid UnorderedObjectListWarning
            qs = qs.order_by(Model._meta.pk.name)
        total_count = qs.count()
        paginator = Paginator(qs, per_page)
        page_obj = paginator.get_page(page)

        add_mode = request.GET.get("add") == "1"
        edit_id = request.GET.get("edit")
        create_form = FormClass() if add_mode else None
        edit_form = None
        if edit_id:
            inst = Model.objects.filter(pk=edit_id).first()
            if inst is not None:
                edit_form = FormClass(instance=inst)

        context = {
            "title": f"جدول: {table}",
            "table": table,
            "columns": columns,
            "page_obj": page_obj,
            "q": q,
            "order": order,
            "per_page": per_page,
            "per_page_options": [10, 25, 50, 100],
            "total_count": total_count,
            "editable": True,
            "create_form": create_form,
            "edit_form": edit_form,
            "edit_id": edit_id,
        }
        return render(request, "data/table_detail.html", context)

    # Fallback read-only for non-registered tables (raw SQL path)
    # Read columns (vendor-agnostic)
    with connection.cursor() as cursor:
        description = connection.introspection.get_table_description(cursor, table)
        columns = [col.name for col in description]

    order_sql = ""
    if order and order.lstrip("-") in columns:
        col = order.lstrip("-")
        direction = "DESC" if order.startswith("-") else "ASC"
        order_sql = f' ORDER BY "{col}" {direction}'

    where_sql = ""
    params = []
    if q:
        like_params = []
        for col in columns:
            like_params.append(f'CAST("{col}" AS TEXT) ILIKE %s')
            params.append(f"%{q}%")
        where_sql = " WHERE " + " OR ".join(like_params)

    sql = f'SELECT * FROM "{table}"' + where_sql + order_sql
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        rows = cursor.fetchall()

    paginator = Paginator(rows, per_page)
    page_obj = paginator.get_page(page)

    context = {
        "title": f"جدول: {table}",
        "table": table,
        "columns": columns,
        "page_obj": page_obj,
        "q": q,
        "order": order,
        "per_page": per_page,
        "per_page_options": [10, 25, 50, 100],
        "total_count": len(rows),
        "editable": False,
    }
    return render(request, "data/table_detail.html", context)


@user_passes_test(_staff_only)
@login_required
def export_table_csv(request, table):
    # Registry of exportable tables (same as editable set)
    MODEL_REGISTRY = {
        Class._meta.db_table: Class,
        Student._meta.db_table: Student,
        Staff._meta.db_table: Staff,
        Subject._meta.db_table: Subject,
        ClassSubject._meta.db_table: ClassSubject,
        TeachingAssignment._meta.db_table: TeachingAssignment,
    }
    Model = MODEL_REGISTRY.get(table)
    if not Model:
        raise Http404("Table not found")

    fields = [f.name for f in Model._meta.concrete_fields]

    def row_iter():
        # Header
        yield ",".join(fields) + "\n"
        # Stream rows to avoid memory blowup
        for obj in Model.objects.all().iterator():
            vals = []
            for f in fields:
                v = getattr(obj, f)
                if v is None:
                    vals.append("")
                else:
                    s = str(v)
                    # Basic CSV escaping for commas and quotes
                    if any(ch in s for ch in [",", '"', "\n", "\r"]):
                        s = '"' + s.replace('"', '""') + '"'
                    vals.append(s)
            yield ",".join(vals) + "\n"

    resp = StreamingHttpResponse(row_iter(), content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="{table}.csv"'
    return resp


# Timetable and calendar features have been fully removed from this module.
# Any previous views or utilities related to calendars or weekly timetables were
# deleted to ensure a safe and final cleanup as requested.
