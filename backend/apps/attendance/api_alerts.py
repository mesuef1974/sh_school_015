from __future__ import annotations
from datetime import date as _date

from django.db import transaction
from django.http import HttpResponse
from django.utils.dateparse import parse_date
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from school.models import Student, AcademicYear, Wing  # type: ignore
from .models_alerts import AbsenceAlert, AlertNumberSequence
from .serializers_alerts import AbsenceAlertSerializer
from .services.absence_days import compute_absence_days
from .services.word_renderer import render_alert_docx


class IsWingSupervisorOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(getattr(request.user, "is_authenticated", False))

    def has_object_permission(self, request, view, obj):
        if getattr(request.user, "is_superuser", False):
            return True
        # Allow access if user supervises this wing (best-effort lookup through Wing.supervisor)
        try:
            from school.models import Staff  # type: ignore

            staff = Staff.objects.filter(user_id=request.user.id).first()
            if staff and obj.wing_id:
                return Wing.objects.filter(id=obj.wing_id, supervisor_id=staff.id).exists()
        except Exception:
            return False
        return False


class AbsenceAlertViewSet(viewsets.ModelViewSet):
    queryset = AbsenceAlert.objects.all().order_by("-created_at")
    serializer_class = AbsenceAlertSerializer
    permission_classes = [IsWingSupervisorOrAdmin]

    def get_queryset(self):
        qs = super().get_queryset()
        # Optional filters for professional workflow: student, status, from/to by period_start/period_end overlap
        student = self.request.query_params.get("student")
        status_q = self.request.query_params.get("status")
        date_from = self.request.query_params.get("from")
        date_to = self.request.query_params.get("to")
        try:
            if student:
                qs = qs.filter(student_id=int(student))
        except Exception:
            pass
        if status_q:
            qs = qs.filter(status=status_q)
        # Overlap if (period_end >= from) and (period_start <= to)
        try:
            if date_from:
                from django.utils.dateparse import parse_date as _pd

                df = _pd(date_from)
                if df:
                    qs = qs.filter(period_end__gte=df)
            if date_to:
                from django.utils.dateparse import parse_date as _pd

                dt = _pd(date_to)
                if dt:
                    qs = qs.filter(period_start__lte=dt)
        except Exception:
            pass
        if getattr(self.request.user, "is_superuser", False):
            return qs
        # Scope to wings supervised by the user
        try:
            from school.models import Staff  # type: ignore

            staff = Staff.objects.filter(user_id=self.request.user.id).first()
            if staff:
                wing_ids = Wing.objects.filter(supervisor_id=staff.id).values_list("id", flat=True)
                return qs.filter(wing_id__in=list(wing_ids))
        except Exception:
            pass
        return qs.none()

    @transaction.atomic
    def create(self, request: Request, *args, **kwargs):
        data = request.data.copy()
        # Normalize student
        student_id = int(data.get("student") or data.get("student_id"))
        student = Student.objects.select_related("class_fk", "wing").get(pk=student_id)

        # Wing access control
        if not getattr(request.user, "is_superuser", False):
            try:
                from school.models import Staff  # type: ignore

                staff = Staff.objects.filter(user_id=request.user.id).first()
                if staff and student.wing_id:
                    if not Wing.objects.filter(id=student.wing_id, supervisor_id=staff.id).exists():
                        return Response({"detail": "لا يمكنك إنشاء تنبيه لطالب خارج جناحك"}, status=403)
            except Exception:
                return Response({"detail": "لا تملك صلاحية"}, status=403)

        # Dates
        start_date = parse_date(data.get("period_start"))
        end_date = parse_date(data.get("period_end"))
        if start_date is None or end_date is None:
            return Response({"detail": "تواريخ غير صالحة"}, status=400)
        if start_date > end_date:
            return Response({"detail": "نطاق التواريخ غير صحيح"}, status=400)

        # Compute O/X according to policy
        excused, unexcused = compute_absence_days(student.id, start_date, end_date)

        # Current academic year from DB
        try:
            cy = AcademicYear.objects.get(is_current=True)
        except AcademicYear.DoesNotExist:
            today = timezone.localdate()
            cy = AcademicYear.objects.filter(start_date__lte=today, end_date__gte=today).first()
            if not cy:
                return Response({"detail": "لم يتم تعريف العام الدراسي الحالي"}, status=500)

        number = AlertNumberSequence.next_number(cy.name)

        payload = {
            "number": number,
            "academic_year": cy.name,
            "student": student.id,
            "class_name": getattr(student, "class_name", getattr(student, "class_fk", None).name if getattr(student, "class_fk", None) else ""),
            "parent_name": getattr(student, "guardian_name", getattr(student, "parent_name", "")),
            "parent_mobile": getattr(student, "guardian_mobile", getattr(student, "parent_mobile", "")),
            "period_start": start_date,
            "period_end": end_date,
            "excused_days": excused,
            "unexcused_days": unexcused,
            "status": "issued",
            "created_by": request.user.id,
            "wing": getattr(student, "wing_id", None),
        }

        serializer = self.get_serializer(data=payload)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=["get"], url_path="docx")
    def docx(self, request: Request, pk=None):
        alert = self.get_object()
        try:
            content = render_alert_docx(alert)
        except FileNotFoundError as e:
            return Response({"detail": str(e)}, status=404)
        except Exception as e:
            return Response({"detail": f"تعذر توليد الملف: {e}"}, status=500)
        fname = f"absence-alert-{alert.academic_year}-{alert.number}.docx"
        resp = HttpResponse(
            content,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        resp["Content-Disposition"] = f"attachment; filename=\"{fname}\""
        return resp


class AbsenceComputeViewSet(viewsets.ViewSet):
    permission_classes = [IsWingSupervisorOrAdmin]

    @action(detail=False, methods=["get"], url_path="compute-days")
    def compute_days(self, request: Request) -> Response:
        try:
            student_id = int(request.query_params.get("student"))
            start_date = parse_date(request.query_params.get("from"))
            end_date = parse_date(request.query_params.get("to"))
        except Exception:
            return Response({"detail": "مدخلات غير صالحة"}, status=400)
        if not start_date or not end_date:
            return Response({"detail": "تواريخ غير صالحة"}, status=400)

        student = Student.objects.select_related("wing").get(pk=student_id)
        if not getattr(request.user, "is_superuser", False):
            try:
                from school.models import Staff  # type: ignore

                staff = Staff.objects.filter(user_id=request.user.id).first()
                if staff and student.wing_id:
                    if not Wing.objects.filter(id=student.wing_id, supervisor_id=staff.id).exists():
                        return Response({"detail": "لا يمكنك الوصول لطلاب خارج جناحك"}, status=403)
            except Exception:
                return Response({"detail": "لا تملك صلاحية"}, status=403)

        o, x = compute_absence_days(student_id, start_date, end_date)
        return Response({"excused_days": o, "unexcused_days": x, "student": student_id, "from": start_date, "to": end_date})