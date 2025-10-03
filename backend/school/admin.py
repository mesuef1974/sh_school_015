from django.contrib import admin, messages
from django.urls import path
from django.shortcuts import render, redirect
from django import forms
from .models import Class, Student, Staff, Subject, TeachingAssignment, ClassSubject
from openpyxl import load_workbook
import re


class ClassSubjectInline(admin.TabularInline):
    model = ClassSubject
    extra = 1
    autocomplete_fields = ("subject",)
    fields = ("subject", "weekly_default")


@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "grade", "section")
    search_fields = ("name",)
    list_filter = ("grade", "section")
    inlines = [ClassSubjectInline]


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("id", "sid", "full_name", "class_fk", "active")
    search_fields = ("sid", "full_name")
    list_filter = ("active", "class_fk")


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ("id", "full_name", "role", "user")
    search_fields = ("full_name",)
    list_filter = ("role",)


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("id", "name_ar", "code", "weekly_default", "is_active")
    search_fields = ("name_ar", "code")
    list_filter = ("is_active",)
    inlines = []  # filled below


class ClassSubjectBySubjectInline(admin.TabularInline):
    model = ClassSubject
    extra = 1
    autocomplete_fields = ("classroom",)
    fields = ("classroom", "weekly_default")


# Attach inline after its definition
SubjectAdmin.inlines = [ClassSubjectBySubjectInline]


class TeachingAssignmentForm(forms.ModelForm):
    class Meta:
        model = TeachingAssignment
        fields = ["teacher", "classroom", "subject", "no_classes_weekly", "notes"]


@admin.register(TeachingAssignment)
class TeachingAssignmentAdmin(admin.ModelAdmin):
    form = TeachingAssignmentForm
    list_display = (
        "id",
        "teacher",
        "classroom",
        "subject",
        "no_classes_weekly",
        "updated_at",
    )
    search_fields = (
        "teacher__full_name",
        "classroom__name",
        "subject__name_ar",
    )
    list_filter = ("classroom__grade", "classroom__section", "subject", "teacher")
    autocomplete_fields = ("teacher", "classroom", "subject")
    actions = ["export_summary"]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "subject":
            classroom_id = None
            try:
                classroom_id = request.GET.get("classroom") or request.POST.get(
                    "classroom"
                )
            except Exception:
                classroom_id = None
            # Try resolve object_id when editing existing assignment
            if (
                not classroom_id
                and hasattr(request, "resolver_match")
                and request.resolver_match
            ):
                obj_id = (
                    request.resolver_match.kwargs.get("object_id")
                    if hasattr(request.resolver_match, "kwargs")
                    else None
                )
                if obj_id:
                    try:
                        obj = TeachingAssignment.objects.get(pk=obj_id)
                        classroom_id = obj.classroom_id
                    except TeachingAssignment.DoesNotExist:
                        pass
            if classroom_id:
                subject_ids = ClassSubject.objects.filter(
                    classroom_id=classroom_id
                ).values_list("subject_id", flat=True)
                kwargs["queryset"] = Subject.objects.filter(id__in=list(subject_ids))
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "import-excel/",
                self.admin_site.admin_view(self.import_excel_view),
                name="teachingassignment_import_excel",
            ),
        ]
        return custom + urls

    def export_summary(self, request, queryset):
        from django.http import HttpResponse
        import csv

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = (
            'attachment; filename="teacher_loads_summary.csv"'
        )
        writer = csv.writer(response)
        writer.writerow(["المعلم", "الصف", "المادة", "حصص/أسبوع"])
        for a in queryset.select_related("teacher", "classroom", "subject"):
            writer.writerow(
                [
                    a.teacher.full_name,
                    a.classroom.name,
                    a.subject.name_ar,
                    a.no_classes_weekly,
                ]
            )
        return response

    export_summary.short_description = "تصدير الملخص CSV"

    # ===== Excel Import =====
    class ImportExcelForm(forms.Form):
        file = forms.FileField(label="ملف Excel للأنصبة (schasual.xlsx)")

    def import_excel_view(self, request):
        if request.method == "POST":
            form = self.ImportExcelForm(request.POST, request.FILES)
            if form.is_valid():
                f = form.cleaned_data["file"]
                try:
                    count, created_subjects = self._import_excel_file(f)
                    messages.success(
                        request,
                        f"تم استيراد {count} سجل. تم إنشاء مواد جديدة: {created_subjects}",
                    )
                    return redirect("..")
                except Exception as e:
                    messages.error(request, f"خطأ أثناء الاستيراد: {e}")
        else:
            form = self.ImportExcelForm()
        context = {
            **self.admin_site.each_context(request),
            "form": form,
            "title": "استيراد الأنصبة من Excel",
        }
        return render(request, "admin/teachingassignment_import.html", context)

    @staticmethod
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

    def _import_excel_file(self, file_obj):
        wb = load_workbook(filename=file_obj, data_only=True)
        created_subjects = 0
        created_assignments = 0

        # Build teacher index (normalized)
        teacher_index = {}
        for t in Staff.objects.all():
            key = self._normalize_ar_text(t.full_name).replace(" ", "").lower()
            if key:
                teacher_index.setdefault(key, t)

        # Build class index by (grade, section) and by name
        classes = Class.objects.all()
        class_by_grade_section = {
            (c.grade, (c.section or "").strip()): c for c in classes
        }
        class_by_name = {self._normalize_ar_text(c.name): c for c in classes}

        # Subject index
        subject_by_norm = {
            self._normalize_ar_text(s.name_ar): s for s in Subject.objects.all()
        }

        total_rows = 0
        for ws in wb.worksheets:
            # Try detect headers positions
            # Heuristic columns: teacher_name, grade, section, class(subject), no.classes/week
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
                        for c in next(
                            ws.iter_rows(min_row=r, max_row=r, values_only=True)
                        )
                    ]
                except StopIteration:
                    break
                normed = [
                    self._normalize_ar_text(v).replace(" ", "").lower() for v in vals
                ]
                tokens = {
                    "teacher": {
                        "teachername",
                        "teacher",
                        "اسمالمعلم",
                        "اسمالمعلّم",
                        "اسمالمعلم",
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
                total_rows += 1
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
                t_key = (
                    self._normalize_ar_text(current_teacher).replace(" ", "").lower()
                )
                teacher = teacher_index.get(t_key)
                if not teacher:
                    # skip if teacher not found
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
                subj_norm = self._normalize_ar_text(subjv)
                weekly = to_int_safe(wv) or 0

                # Map class
                classroom = None
                if grade is not None:
                    classroom = class_by_grade_section.get((grade, section or ""))
                if classroom is None and subj_norm:
                    # fallback by name token present in class name
                    # e.g., Class name like "12-1" or "12/1" already set in DB
                    if grade is not None and section is not None:
                        key = f"{grade}{section}"
                        for cname, cobj in class_by_name.items():
                            if key in re.sub(r"\D", "", cname):
                                classroom = cobj
                                break
                if classroom is None:
                    # final fallback: try by normalized name equality if provided in sheet
                    pass

                if classroom is None:
                    continue

                # Subject
                if subj_norm:
                    subj_obj = subject_by_norm.get(subj_norm)
                    if not subj_obj:
                        subj_obj = Subject.objects.create(name_ar=subjv)
                        subject_by_norm[subj_norm] = subj_obj
                        created_subjects += 1
                else:
                    continue

                # Ensure the subject is assigned to the class
                ClassSubject.objects.get_or_create(
                    classroom=classroom, subject=subj_obj
                )

                obj, created = TeachingAssignment.objects.update_or_create(
                    teacher=teacher,
                    classroom=classroom,
                    subject=subj_obj,
                    defaults={
                        "no_classes_weekly": weekly or subj_obj.weekly_default or 0
                    },
                )
                if created:
                    created_assignments += 1

        return created_assignments, created_subjects
