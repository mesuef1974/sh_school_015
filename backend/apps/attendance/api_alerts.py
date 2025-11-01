from __future__ import annotations

from django.db import transaction
from django.http import HttpResponse, FileResponse
from django.utils import timezone
from apps.common.date_utils import parse_ui_or_iso_date
from django.core.files.base import ContentFile
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
import hashlib
from pathlib import Path

from school.models import Student, AcademicYear, Wing  # type: ignore
from .models_alerts import AbsenceAlert, AlertNumberSequence, AbsenceAlertDocument
from .serializers_alerts import AbsenceAlertSerializer
from .services.absence_days import compute_absence_days
from .services.word_renderer import render_alert_docx, current_template_info


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
                df = parse_ui_or_iso_date(date_from)
                if df:
                    qs = qs.filter(period_end__gte=df)
            if date_to:
                dt = parse_ui_or_iso_date(date_to)
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

        # Dates (accept UI DD/MM/YYYY or ISO YYYY-MM-DD)
        start_date = parse_ui_or_iso_date(data.get("period_start"))
        end_date = parse_ui_or_iso_date(data.get("period_end"))
        if start_date is None or end_date is None:
            return Response({"detail": "تواريخ غير صالحة (يرجى استخدام DD/MM/YYYY أو YYYY-MM-DD)"}, status=400)
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
            "class_name": getattr(
                student,
                "class_name",
                (getattr(student, "class_fk", None).name if getattr(student, "class_fk", None) else ""),
            ),
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
        # Optional persist=1 to archive the generated file as the latest version
        if request.query_params.get("persist") in ("1", "true", "yes"):  # archive
            sha = hashlib.sha256(content).hexdigest()
            from .services.word_renderer import TEMPLATE_PATH, FALLBACK_TEMPLATE_PATH
            tpath = TEMPLATE_PATH if Path(TEMPLATE_PATH).exists() else FALLBACK_TEMPLATE_PATH
            thash = hashlib.sha256(Path(tpath).read_bytes()).hexdigest() if Path(tpath).exists() else ""
            doc = AbsenceAlertDocument.objects.create(
                alert=alert,
                created_by=request.user,
                size=len(content),
                sha256=sha,
                template_name=str(tpath),
                template_hash=thash,
            )
            # Save file content into FileField
            doc.file.save(fname, ContentFile(content), save=True)
        resp = HttpResponse(
            content,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        # Diagnostics: expose which template path/hash were used
        try:
            tpath, thash = current_template_info()
            resp["X-Docx-Template-Path"] = tpath
            if thash:
                resp["X-Docx-Template-Hash"] = thash
        except Exception:
            pass
        resp["Content-Disposition"] = f'attachment; filename="{fname}"'
        return resp

    @action(detail=True, methods=["post"], url_path="docx/save")
    def docx_save(self, request: Request, pk=None):
        alert = self.get_object()
        try:
            content = render_alert_docx(alert)
        except FileNotFoundError as e:
            return Response({"detail": str(e)}, status=404)
        except Exception as e:
            return Response({"detail": f"تعذر توليد الملف: {e}"}, status=500)
        sha = hashlib.sha256(content).hexdigest()
        from .services.word_renderer import TEMPLATE_PATH, FALLBACK_TEMPLATE_PATH
        tpath = TEMPLATE_PATH if Path(TEMPLATE_PATH).exists() else FALLBACK_TEMPLATE_PATH
        thash = hashlib.sha256(Path(tpath).read_bytes()).hexdigest() if Path(tpath).exists() else ""
        fname = f"absence-alert-{alert.academic_year}-{alert.number}.docx"
        doc = AbsenceAlertDocument.objects.create(
            alert=alert,
            created_by=request.user,
            size=len(content),
            sha256=sha,
            template_name=str(tpath),
            template_hash=thash,
        )
        doc.file.save(fname, ContentFile(content), save=True)
        return Response({
            "id": doc.id,
            "size": doc.size,
            "sha256": doc.sha256,
            "created_at": doc.created_at,
            "template_name": doc.template_name,
        }, status=201)

    @action(detail=True, methods=["get"], url_path="docx/latest")
    def docx_latest(self, request: Request, pk=None):
        alert = self.get_object()
        doc = alert.documents.order_by("-created_at").first()
        if not doc or not doc.file:
            return Response({"detail": "لا يوجد ملف محفوظ لهذا التنبيه"}, status=404)
        response = FileResponse(doc.file.open("rb"), content_type=doc.mime)
        response["Content-Disposition"] = f'attachment; filename="{doc.file.name.split('/')[-1]}"'
        return response

    @action(detail=True, methods=["get"], url_path="docx/list")
    def docx_list(self, request: Request, pk=None):
        alert = self.get_object()
        items = [
            {
                "id": d.id,
                "name": d.file.name.split('/')[-1] if d.file else None,
                "size": d.size,
                "sha256": d.sha256,
                "template_name": d.template_name,
                "template_hash": d.template_hash,
                "created_at": d.created_at,
                "created_by": getattr(d.created_by, "get_full_name", lambda: str(d.created_by))(),
            }
            for d in alert.documents.order_by("-created_at").all()
        ]
        return Response({"count": len(items), "items": items})


class AbsenceComputeViewSet(viewsets.ViewSet):
    permission_classes = [IsWingSupervisorOrAdmin]

    @action(detail=False, methods=["get"], url_path="compute-days")
    def compute_days(self, request: Request) -> Response:
        try:
            student_id = int(request.query_params.get("student"))
            start_date = parse_ui_or_iso_date(request.query_params.get("from"))
            end_date = parse_ui_or_iso_date(request.query_params.get("to"))
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
        return Response(
            {
                "excused_days": o,
                "unexcused_days": x,
                "student": student_id,
                "from": start_date,
                "to": end_date,
            }
        )