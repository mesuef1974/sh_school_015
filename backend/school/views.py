from django import forms
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.urls import reverse
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from .models import Class, Student, Staff, Subject, TeachingAssignment, ClassSubject
from .serializers import (
    ClassSerializer,
    StudentSerializer,
    StaffSerializer,
    SubjectSerializer,
    TeachingAssignmentSerializer,
    ClassSubjectSerializer,
)
from openpyxl import load_workbook
import re


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
