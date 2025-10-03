from django import forms
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.db import IntegrityError
from .models import (
    Class,
    Student,
    Staff,
    Subject,
    TeachingAssignment,
    ClassSubject,
    CalendarTemplate,
    CalendarSlot,
)
from .serializers import (
    ClassSerializer,
    StudentSerializer,
    StaffSerializer,
    SubjectSerializer,
    TeachingAssignmentSerializer,
    ClassSubjectSerializer,
    CalendarTemplateSerializer,
    CalendarSlotSerializer,
)
from openpyxl import load_workbook
import re
from django.db import connection
from django.core.paginator import Paginator
from django.http import Http404


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
    queryset = TeachingAssignment.objects.select_related(
        "teacher", "classroom", "subject"
    ).all()
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
            f.name
            for f in Class._meta.fields
            if f.editable and f.name != Class._meta.pk.name
        ]


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = [
            f.name
            for f in Student._meta.fields
            if f.editable and f.name != Student._meta.pk.name
        ]


class StaffForm(forms.ModelForm):
    class Meta:
        model = Staff
        fields = [
            f.name
            for f in Staff._meta.fields
            if f.editable and f.name != Staff._meta.pk.name
        ]


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = [
            f.name
            for f in Subject._meta.fields
            if f.editable and f.name != Subject._meta.pk.name
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
    # Handle manual add
    if request.method == "POST" and request.POST.get("action") == "add":
        form = TeachingAssignmentForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect(reverse("teacher_loads_dashboard"))
    else:
        form = TeachingAssignmentForm()

    # Handle Excel upload
    if request.method == "POST" and request.POST.get("action") == "upload":
        up_form = ExcelUploadForm(request.POST, request.FILES)
        if up_form.is_valid():
            _import_excel_file(up_form.cleaned_data["file"])  # ignore summary here
            return redirect(reverse("teacher_loads_dashboard"))
    elif request.method == "POST" and request.POST.get("action") == "upload_default":
        # Import from the known default path on the server
        from pathlib import Path

        repo_root = Path(__file__).resolve().parents[2]
        default_path = repo_root / "DOC" / "school_DATA" / "schasual.xlsx"
        try:
            with open(default_path, "rb") as f:
                _import_excel_file(f)
        except FileNotFoundError:
            pass
        return redirect(reverse("teacher_loads_dashboard"))
    else:
        up_form = ExcelUploadForm()

    # Filters
    teacher_q = request.GET.get("teacher")
    grade_q = request.GET.get("grade")
    section_q = request.GET.get("section")
    subject_q = request.GET.get("subject")

    qs = TeachingAssignment.objects.select_related(
        "teacher", "classroom", "subject"
    ).all()
    if teacher_q:
        qs = qs.filter(teacher_id=teacher_q)
    if grade_q:
        qs = qs.filter(classroom__grade=grade_q)
    if section_q:
        qs = qs.filter(classroom__section=section_q)
    if subject_q:
        qs = qs.filter(subject_id=subject_q)

    context = {
        "form": form,
        "upload_form": up_form,
        "assignments": qs.order_by(
            "teacher__full_name", "classroom__grade", "classroom__section"
        ),
        "teachers": Staff.objects.all(),
        "classes": Class.objects.all(),
        "subjects": Subject.objects.all(),
        "grades": sorted({c.grade for c in Class.objects.all()}),
        "sections": sorted({(c.section or "") for c in Class.objects.all()}),
        "title": "لوحة الأنصبة — إدخال ورفع Excel",
    }
    return render(request, "school/teacher_loads_dashboard.html", context)


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


def _import_excel_file(file_obj):
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

    for ws in wb.worksheets:
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
                continue

            # Subject
            if subj_norm:
                subj_obj = subject_by_norm.get(subj_norm)
                if not subj_obj:
                    subj_obj = Subject.objects.create(name_ar=subjv)
                    subject_by_norm[subj_norm] = subj_obj
            else:
                continue

            # Ensure the subject is assigned to the class
            ClassSubject.objects.get_or_create(classroom=classroom, subject=subj_obj)

            TeachingAssignment.objects.update_or_create(
                teacher=teacher,
                classroom=classroom,
                subject=subj_obj,
                defaults={"no_classes_weekly": weekly or subj_obj.weekly_default or 0},
            )

    return True


@login_required
def data_overview(request):
    # Denylist sensitive tables by prefix or exact names
    deny_exact = {"django_session"}
    deny_prefixes = ("auth_", "django_", "admin_")

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema='public' AND table_type='BASE TABLE'
            ORDER BY table_name
            """
        )
        tables = [row[0] for row in cursor.fetchall()]

    visible_tables = [
        t
        for t in tables
        if t not in deny_exact and not any(t.startswith(p) for p in deny_prefixes)
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


@login_required
def data_table_detail(request, table):
    # Security: allow only public tables and apply same deny rules
    deny_exact = {"django_session"}
    deny_prefixes = ("auth_", "django_", "admin_")

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema='public' AND table_type='BASE TABLE'
            """
        )
        all_tables = {row[0] for row in cursor.fetchall()}

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
        columns = [Model._meta.pk.name] + [
            f.name for f in fields if f.name != Model._meta.pk.name
        ]

        # Handle POST actions
        if request.method == "POST":
            # Helper to rebuild querystring preserving filters
            def _qs_keep(req, drop_keys=None):
                drop_keys = set(drop_keys or [])
                from urllib.parse import parse_qsl, urlencode

                pairs = [
                    (k, v)
                    for k, v in parse_qsl(
                        req.META.get("QUERY_STRING", ""), keep_blank_values=True
                    )
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
                            messages.error(
                                request, f"تعذر الحفظ بسبب قيود البيانات: {e}"
                            )
                            return redirect(request.path + _qs_keep(request))
                        # Preserve current page filters
                        return redirect(
                            request.path + _qs_keep(request, drop_keys=["edit"])
                        )
            elif action == "delete":
                pk = request.POST.get("id")
                obj = Model.objects.filter(pk=pk).first()
                if obj is not None:
                    try:
                        obj.delete()
                        messages.success(request, "تم حذف السجل.")
                    except (ProtectedError, IntegrityError) as e:
                        messages.error(
                            request, f"لا يمكن حذف السجل لارتباطه بسجلات أخرى: {e}"
                        )
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
                if getattr(f, "get_internal_type", lambda: "")()
                in ("CharField", "TextField")
            ]
            query = Q()
            for name in text_fields:
                query |= Q(**{f"{name}__icontains": q})
            if query:
                qs = qs.filter(query)
        if order:
            if order.lstrip("-") in columns:
                qs = qs.order_by(order)
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
    # Read columns
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema='public' AND table_name=%s
            ORDER BY ordinal_position
            """,
            [table],
        )
        columns = [r[0] for r in cursor.fetchall()]

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


# --- Calendar (API + HTML) ---


class CalendarTemplateViewSet(ReadOnlyModelViewSet):
    queryset = CalendarTemplate.objects.all().prefetch_related("slots")
    serializer_class = CalendarTemplateSerializer


class CalendarSlotViewSet(ReadOnlyModelViewSet):
    queryset = CalendarSlot.objects.select_related("template").all()
    serializer_class = CalendarSlotSerializer


@login_required
def calendar_list(request):
    templates = CalendarTemplate.objects.all().order_by("name")
    return render(request, "school/calendar_list.html", {"templates": templates})


@login_required
def calendar_template_detail(request, pk: int):
    tmpl = get_object_or_404(CalendarTemplate, pk=pk)
    slots = tmpl.slots.all().order_by("day", "order", "start_time")
    return render(
        request,
        "school/calendar_detail.html",
        {"template": tmpl, "slots": slots},
    )


# --- Timetable (Weekly grid MVP) ---
DAYS_ORDER = ["Sun", "Mon", "Tue", "Wed", "Thu"]


@login_required
def timetable_select(request):
    """Select a class and a calendar template to view the weekly timetable.
    Read-only MVP: displays the time grid only.
    """
    classes = Class.objects.all().order_by("grade", "section", "name")
    templates = CalendarTemplate.objects.all().order_by("name")

    # Allow simple GET selection as well
    class_id = request.GET.get("class_id")
    template_id = request.GET.get("template_id")
    if request.method == "POST":
        class_id = request.POST.get("class_id")
        template_id = request.POST.get("template_id")
    if class_id and template_id:
        try:
            cid = int(class_id)
            tid = int(template_id)
            return redirect(reverse("timetable_class_week", args=[cid, tid]))
        except Exception:
            pass

    return render(
        request,
        "school/timetable_select.html",
        {"classes": classes, "templates": templates},
    )


@login_required
def timetable_class_week(request, class_id: int, template_id: int):
    classroom = get_object_or_404(Class, pk=class_id)
    tmpl = get_object_or_404(CalendarTemplate, pk=template_id)

    # Build day->list[slot] where slots are expanded for 'ALL' days
    raw_slots = list(tmpl.slots.all().order_by("day", "order", "start_time"))
    day_slots = {d: [] for d in DAYS_ORDER}
    for s in raw_slots:
        if (s.day or "").upper() == "ALL":
            for d in DAYS_ORDER:
                day_slots[d].append(s)
        else:
            if s.day in day_slots:
                day_slots[s.day].append(s)

    # Normalize per-day ordering
    for d in day_slots:
        day_slots[d] = sorted(
            day_slots[d], key=lambda x: (x.order, x.start_time, x.period_index)
        )

    # Determine the unique period rows based on order/start_time from first non-empty day
    period_rows = []
    for d in DAYS_ORDER:
        if day_slots[d]:
            for s in day_slots[d]:
                key = (s.period_index, s.start_time, s.end_time, s.block, s.order)
                if key not in period_rows:
                    period_rows.append(key)
            break

    context = {
        "classroom": classroom,
        "template": tmpl,
        "days": DAYS_ORDER,
        "day_slots": day_slots,
        "period_rows": period_rows,
    }
    return render(request, "school/timetable_week.html", context)


# EOF
