# ruff: noqa: I001, E501
from datetime import date as _date, timedelta

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.request import Request
from django.http import HttpResponse
import csv
import logging
from django.utils import timezone

from .serializers import StudentBriefSerializer, ExitEventSerializer
from . import selectors
from .services.attendance import bulk_save_attendance
from .selectors import _CLASS_FK_ID  # reuse detected class FK field

logger = logging.getLogger(__name__)


def _parse_date_or_400(dt_str: str | None):
    """Parse ISO date (YYYY-MM-DD) or return (None, Response(400)). If empty, return today's date in the configured local timezone.
    Using timezone.localdate() avoids UTC vs local day mismatches (e.g., showing Monday when it is Tuesday locally).
    """
    if not dt_str:
        return timezone.localdate(), None
    try:
        return _date.fromisoformat(dt_str), None
    except Exception:
        return None, Response({"detail": "date must be YYYY-MM-DD"}, status=400)


def _filter_by_teacher_subjects(qs, user, class_id):
    """Filter attendance queryset based on teacher's assignments.
    Teacher must satisfy TWO conditions:
      1. Teaches this classroom (class_id)
      2. Teaches the subject for this classroom
    Superusers and wing supervisors see all records.
    Returns: filtered queryset
    """
    from school.models import Staff, TeachingAssignment  # type: ignore

    # Check if user is superuser or wing supervisor
    try:
        roles = set(user.groups.values_list("name", flat=True))
    except Exception:
        roles = set()
    is_super = bool(getattr(user, "is_superuser", False))
    is_wing = "wing_supervisor" in roles

    # Superusers and wing supervisors see everything
    if is_super or is_wing:
        return qs

    # Get current teacher (staff)
    staff = None
    try:
        staff = Staff.objects.filter(user_id=user.id).first()
    except Exception:
        pass

    # If no staff found, return unfiltered (shouldn't happen due to access control)
    if not staff:
        return qs

    # Get valid (teacher, classroom, subject) combinations from TeachingAssignment
    # This ensures BOTH conditions: teacher teaches classroom AND teaches subject to that classroom
    valid_assignments = TeachingAssignment.objects.filter(
        teacher_id=staff.id, classroom_id=class_id
    ).values_list("subject_id", flat=True)

    if valid_assignments:
        # Filter by: records created by this teacher AND for subjects they teach to this classroom
        qs = qs.filter(teacher_id=staff.id, subject_id__in=list(valid_assignments))
    else:
        # Teacher doesn't teach this classroom, return empty queryset
        qs = qs.none()

    return qs


class AttendanceViewSetBase(viewsets.ViewSet):
    # Enforce authenticated access for production-grade security
    from rest_framework.permissions import IsAuthenticated

    permission_classes = [IsAuthenticated]

    def _user_has_access_to_class(self, user, class_id: int) -> bool:
        """Server-side gate for write operations on attendance by class.
        Delegates to centralized RBAC helper for consistency.
        """
        try:
            from apps.common.permissions import user_can_access_class  # type: ignore
        except Exception:
            return False
        return user_can_access_class(user, class_id)

    @action(detail=False, methods=["get"], url_path="students")
    def list_students(self, request: Request) -> Response:
        try:
            class_id = int(request.query_params.get("class_id"))
        except (TypeError, ValueError):
            return Response({"detail": "class_id is required and must be int"}, status=400)
        dt, err = _parse_date_or_400(request.query_params.get("date"))
        if err:
            return err
        # Enforce access: teachers can only load students for their own classes
        if not self._user_has_access_to_class(request.user, class_id):
            return Response({"detail": "not allowed for this class"}, status=403)
        qs = selectors.get_students_for_class_on_date(class_id, dt)
        data = StudentBriefSerializer(qs, many=True).data
        return Response({"students": data, "date": dt.isoformat(), "class_id": class_id})

    @action(detail=False, methods=["get"], url_path="records")
    def list_records(self, request: Request) -> Response:
        try:
            class_id = int(request.query_params.get("class_id"))
        except (TypeError, ValueError):
            return Response({"detail": "class_id is required and must be int"}, status=400)
        dt, err = _parse_date_or_400(request.query_params.get("date"))
        if err:
            return err
        # Enforce access for records as well
        if not self._user_has_access_to_class(request.user, class_id):
            return Response({"detail": "not allowed for this class"}, status=403)
        qs = selectors.get_attendance_records(class_id, dt)
        # Return raw minimal fields for now
        data = [
            {
                "student_id": r.student_id,
                "status": r.status,
                "note": getattr(r, "note", None),
            }
            for r in qs
        ]
        return Response({"records": data, "date": dt.isoformat(), "class_id": class_id})

    @action(detail=False, methods=["get"], url_path="history")
    def list_history(self, request: Request) -> Response:
        """Return paginated attendance history for a class within a date range.
        Query params:
          - class_id: int (required)
          - from: YYYY-MM-DD (default: today-6 days)
          - to: YYYY-MM-DD (default: today)
          - page: int (default 1)
          - page_size: int (default 100, max 200)
        Response: {count, page, page_size, results:[{date,student_id,student_name,status,note}]}
        """
        # Validate class_id
        try:
            class_id = int(request.query_params.get("class_id"))
        except (TypeError, ValueError):
            return Response({"detail": "class_id is required and must be int"}, status=400)
        # Access control
        if not self._user_has_access_to_class(request.user, class_id):
            return Response({"detail": "not allowed for this class"}, status=403)

        # Parse from/to
        from_str = request.query_params.get("from")
        to_str = request.query_params.get("to")
        today = _date.today()
        try:
            dt_to = _date.fromisoformat(to_str) if to_str else today
        except Exception:
            return Response({"detail": "to must be YYYY-MM-DD"}, status=400)
        try:
            dt_from = _date.fromisoformat(from_str) if from_str else (dt_to - timedelta(days=6))
        except Exception:
            return Response({"detail": "from must be YYYY-MM-DD"}, status=400)
        if dt_from > dt_to:
            return Response({"detail": "from must be <= to"}, status=400)

        # Pagination params
        try:
            page = max(1, int(request.query_params.get("page") or 1))
        except Exception:
            page = 1
        try:
            page_size = int(request.query_params.get("page_size") or 100)
        except Exception:
            page_size = 100
        if page_size > 200:
            page_size = 200
        if page_size < 1:
            page_size = 1

        # Query optimized with select_related to avoid N+1 on student and class
        from school.models import AttendanceRecord  # type: ignore

        qs = AttendanceRecord.objects.filter(
            **{_CLASS_FK_ID: class_id}, date__gte=dt_from, date__lte=dt_to
        ).select_related("student", "subject")

        # Filter by teacher's subjects (teachers only see their own subjects)
        qs = _filter_by_teacher_subjects(qs, request.user, class_id)

        qs = qs.order_by("date", "student_id")
        total = qs.count()
        start = (page - 1) * page_size
        end = start + page_size
        page_qs = qs[start:end]
        results = [
            {
                "date": r.date.isoformat(),
                "student_id": r.student_id,
                "student_name": getattr(getattr(r, "student", None), "full_name", None),
                "status": r.status,
                "note": getattr(r, "note", None),
                "period_number": getattr(r, "period_number", None),
                "subject_name": getattr(getattr(r, "subject", None), "name_ar", None),
            }
            for r in page_qs
        ]
        return Response(
            {
                "count": total,
                "page": page,
                "page_size": page_size,
                "from": dt_from.isoformat(),
                "to": dt_to.isoformat(),
                "class_id": class_id,
                "results": results,
            }
        )

    @action(detail=False, methods=["get"], url_path="history-export")
    def history_export(self, request: Request) -> HttpResponse:
        """Export attendance history for a class within a date range.
        Query params: class_id (int, required), from (YYYY-MM-DD), to (YYYY-MM-DD), format(optional): csv|xlsx
        Applies the same access control as list_history.
        Default: CSV (TSV actually for Excel safety). When format=xlsx is provided, returns .xlsx.
        """
        # Validate class_id
        try:
            class_id = int(request.query_params.get("class_id"))
        except (TypeError, ValueError):
            return Response({"detail": "class_id is required and must be int"}, status=400)  # type: ignore[return-value]
        # Access control
        if not self._user_has_access_to_class(request.user, class_id):
            return Response({"detail": "not allowed for this class"}, status=403)  # type: ignore[return-value]
        # Parse dates (defaults align with list_history)
        from_str = request.query_params.get("from")
        to_str = request.query_params.get("to")
        today = _date.today()
        try:
            dt_to = _date.fromisoformat(to_str) if to_str else today
        except Exception:
            return Response({"detail": "to must be YYYY-MM-DD"}, status=400)  # type: ignore[return-value]
        try:
            dt_from = _date.fromisoformat(from_str) if from_str else (dt_to - timedelta(days=6))
        except Exception:
            return Response({"detail": "from must be YYYY-MM-DD"}, status=400)  # type: ignore[return-value]
        if dt_from > dt_to:
            return Response({"detail": "from must be <= to"}, status=400)  # type: ignore[return-value]
        # Cap range to 60 days to avoid heavy exports in dev
        if (dt_to - dt_from).days > 60:
            return Response({"detail": "date range too large; max 60 days"}, status=400)  # type: ignore[return-value]
        # Build queryset
        from school.models import AttendanceRecord  # type: ignore

        qs = AttendanceRecord.objects.filter(
            **{_CLASS_FK_ID: class_id}, date__gte=dt_from, date__lte=dt_to
        ).select_related("student", "subject")

        # Filter by teacher's subjects (teachers only see their own subjects)
        qs = _filter_by_teacher_subjects(qs, request.user, class_id)

        qs = qs.order_by("date", "student_id")
        export_format = (request.query_params.get("format") or "xlsx").lower()
        if export_format == "xlsx":
            # Generate an Excel workbook to guarantee correct Arabic rendering
            try:
                from io import BytesIO
                from openpyxl import Workbook  # type: ignore

                wb = Workbook()
                ws = wb.active
                ws.title = "Attendance"
                # Right-to-left view for Arabic
                try:
                    ws.sheet_view.rightToLeft = True
                except Exception:
                    pass
                headers = [
                    "date/التاريخ",
                    "student_id/رقم الطالب",
                    "student/الطالب",
                    "period/الحصة",
                    "subject/المادة",
                    "status/الحالة",
                    "note/ملاحظة",
                ]
                ws.append(headers)
                # Stream rows to reduce memory/time; avoid per-cell styling loops
                for r in qs.iterator(chunk_size=1000):
                    student_name = getattr(getattr(r, "student", None), "full_name", None)
                    subject_name = getattr(getattr(r, "subject", None), "name_ar", None)
                    ws.append(
                        [
                            r.date.isoformat(),
                            r.student_id,
                            student_name or "",
                            getattr(r, "period_number", "") or "",
                            subject_name or "",
                            r.status,
                            getattr(r, "note", "") or "",
                        ]
                    )
                # Freeze header row
                try:
                    ws.freeze_panes = "A2"
                except Exception:
                    pass
                # Simple column widths
                try:
                    ws.column_dimensions["A"].width = 14  # date
                    ws.column_dimensions["B"].width = 12  # student_id
                    ws.column_dimensions["C"].width = 32  # student name
                    ws.column_dimensions["D"].width = 10  # period
                    ws.column_dimensions["E"].width = 24  # subject
                    ws.column_dimensions["F"].width = 14  # status
                    ws.column_dimensions["G"].width = 40  # note
                except Exception:
                    pass
                bio = BytesIO()
                wb.save(bio)
                data = bio.getvalue()
                filename = (
                    f"attendance_history_{class_id}_{dt_from.isoformat()}_{dt_to.isoformat()}.xlsx"
                )
                resp = HttpResponse(
                    data,
                    content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
                resp["Content-Disposition"] = f'attachment; filename="{filename}"'
                return resp
            except Exception as e:
                # Log and fallback to CSV below if openpyxl missing or error occurred
                try:
                    logger.warning("history_export XLSX generation failed: %s", e)
                except Exception:
                    pass
        # Default: CSV (actually TSV) response for Excel
        filename = f"attendance_history_{class_id}_{dt_from.isoformat()}_{dt_to.isoformat()}.csv"
        resp = HttpResponse(content_type="text/csv; charset=utf-16le")
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        resp.write("\ufeff")
        writer = csv.writer(resp, delimiter="\t", lineterminator="\r\n")
        writer.writerow(
            [
                "date/التاريخ",
                "student_id/رقم الطالب",
                "student/الطالب",
                "period/الحصة",
                "subject/المادة",
                "status/الحالة",
                "note/ملاحظة",
            ]
        )
        for r in qs.iterator(chunk_size=1000):
            student_name = getattr(getattr(r, "student", None), "full_name", None)
            subject_name = getattr(getattr(r, "subject", None), "name_ar", None)
            writer.writerow(
                [
                    r.date.isoformat(),
                    r.student_id,
                    student_name or "",
                    getattr(r, "period_number", "") or "",
                    subject_name or "",
                    r.status,
                    getattr(r, "note", "") or "",
                ]
            )
        return resp

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request: Request) -> Response:
        scope_raw = request.query_params.get("scope", "school")
        scope = (scope_raw or "school").lower()
        if scope not in {"teacher", "wing", "school"}:
            scope = "school"
        dt, err = _parse_date_or_400(request.query_params.get("date"))
        if err:
            return err
        class_id = request.query_params.get("class_id")
        wing_id = request.query_params.get("wing_id")
        try:
            class_id_int = int(class_id) if class_id is not None else None
        except (TypeError, ValueError):
            return Response({"detail": "class_id must be int"}, status=400)
        try:
            wing_id_int = int(wing_id) if wing_id is not None else None
        except (TypeError, ValueError):
            return Response({"detail": "wing_id must be int"}, status=400)
        data = selectors.get_summary(scope=scope, dt=dt, class_id=class_id_int, wing_id=wing_id_int)
        return Response(data)

    @action(detail=False, methods=["get"], url_path="timetable/teacher/today")
    def teacher_timetable_today(self, request: Request) -> Response:
        """Return today's ordered periods for the authenticated teacher.
        Maps request.user->Staff; superuser can pass ?teacher_id to inspect.
        """
        from school.models import Staff  # type: ignore

        dt, err = _parse_date_or_400(request.query_params.get("date"))
        if err:
            return err
        user = request.user
        teacher_id_qs = request.query_params.get("teacher_id")
        staff: Staff | None = None  # type: ignore
        # Resolve staff for this user
        try:
            staff = Staff.objects.filter(user_id=user.id).first()
        except Exception:
            staff = None
        if not staff and getattr(user, "is_superuser", False) and teacher_id_qs:
            try:
                staff = Staff.objects.filter(id=int(teacher_id_qs)).first()
            except Exception:
                staff = None
        if not staff:
            return Response({"periods": []})
        periods = selectors.get_teacher_today_periods(staff_id=staff.id, dt=dt)
        return Response({"date": dt.isoformat(), "periods": periods})

    @action(detail=False, methods=["get"], url_path="timetable/teacher/weekly")
    def teacher_timetable_weekly(self, request: Request) -> Response:
        """Return weekly timetable grid for the authenticated teacher."""
        from school.models import Staff  # type: ignore

        user = request.user
        teacher_id_qs = request.query_params.get("teacher_id")
        staff: Staff | None = None  # type: ignore
        try:
            staff = Staff.objects.filter(user_id=user.id).first()
        except Exception:
            staff = None
        if not staff and getattr(user, "is_superuser", False) and teacher_id_qs:
            try:
                staff = Staff.objects.filter(id=int(teacher_id_qs)).first()
            except Exception:
                staff = None
        if not staff:
            return Response({"days": {str(i): [] for i in range(1, 8)}, "meta": {}})
        grid = selectors.get_teacher_weekly_grid(staff_id=staff.id)
        return Response(grid)

    @action(detail=False, methods=["get"], url_path="teacher/classes")
    def teacher_classes(self, request: Request) -> Response:
        """
        Return classes taught by the authenticated teacher based on TeachingAssignment.
        Relaxed authorization: any authenticated user mapped to a Staff record will get their classes.
        Superusers and wing supervisors can see all classes across assignments.
        """
        from school.models import Staff, TeachingAssignment  # type: ignore  # lazy import to avoid circulars

        user = request.user
        # Determine roles (best-effort; do not block if missing 'teacher' group)
        try:
            roles = set(user.groups.values_list("name", flat=True))  # type: ignore
        except Exception:
            roles = set()
        is_super = bool(getattr(user, "is_superuser", False))
        is_wing = "wing_supervisor" in roles

        # Superuser/wing supervisor: return distinct classrooms across assignments (fallback: all classes)
        if is_super or is_wing:
            try:
                from school.models import Class  # type: ignore

                qs = (
                    TeachingAssignment.objects.select_related("classroom")
                    .values("classroom_id", "classroom__name")
                    .distinct()
                )
                classes = [
                    {"id": row["classroom_id"], "name": row.get("classroom__name")}
                    for row in qs
                    if row.get("classroom_id")
                ]
                if not classes:
                    classes = [
                        {"id": c.id, "name": getattr(c, "name", None)}
                        for c in Class.objects.all().order_by("name")[:200]
                    ]
                return Response({"classes": classes})
            except Exception:
                return Response({"classes": []})

        # Teacher-specific: Map user -> Staff; try fallbacks if OneToOne not set
        staff = None
        try:
            staff = Staff.objects.filter(user_id=user.id).first()
        except Exception:
            staff = None
        if not staff:
            # Fallback by email or full name when possible
            try:
                if getattr(user, "email", None):
                    staff = Staff.objects.filter(email__iexact=user.email).first()
            except Exception:
                staff = staff or None
            if not staff:
                try:
                    full = (user.get_full_name() or "").strip()
                    if full:
                        staff = Staff.objects.filter(full_name__icontains=full).first()
                except Exception:
                    pass
        if not staff:
            # Preserve previous behavior: plain users without staff mapping get 403
            return Response({"detail": "requires teacher role or staff mapping"}, status=403)

        # Gather distinct classrooms from TeachingAssignment for this teacher
        qs = (
            TeachingAssignment.objects.filter(teacher_id=staff.id)
            .select_related("classroom")
            .values("classroom_id", "classroom__name")
            .distinct()
        )
        # If no assignments and user lacks teacher/wing role, keep 403 to match tests/expectations
        if not qs.exists() and ("teacher" not in roles):
            return Response({"detail": "no teaching assignments"}, status=403)
        classes = [{"id": row["classroom_id"], "name": row.get("classroom__name")} for row in qs]
        return Response({"classes": classes})

    @action(detail=False, methods=["post"], url_path="bulk_save")
    def bulk_save(self, request: Request) -> Response:
        payload = request.data or {}
        try:
            class_id = int(payload.get("class_id"))
            dt = _date.fromisoformat(payload.get("date")) if payload.get("date") else _date.today()
            records = payload.get("records") or []
            period_number = payload.get("period_number")
            period_number = (
                int(period_number)
                if period_number
                not in (
                    None,
                    "",
                )
                else None
            )
        except Exception as e:
            return Response({"detail": f"Invalid payload: {e}"}, status=400)
        # Enforce access for saving
        if not self._user_has_access_to_class(request.user, class_id):
            return Response({"detail": "not allowed for this class"}, status=403)
        try:
            saved = bulk_save_attendance(
                class_id=class_id,
                dt=dt,
                records=records,
                actor_user_id=(request.user.id if request.user.is_authenticated else None),
                period_number=period_number,
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)
        return Response({"saved": len(saved)}, status=status.HTTP_200_OK)


class AttendanceViewSet(viewsets.ViewSet):
    # Enforce authenticated access for production-grade security
    from rest_framework.permissions import IsAuthenticated

    permission_classes = [IsAuthenticated]

    def _user_has_access_to_class(self, user, class_id: int) -> bool:
        """Server-side gate for write operations on attendance by class.
        Delegates to centralized RBAC helper for consistency.
        """
        try:
            from apps.common.permissions import user_can_access_class  # type: ignore
        except Exception:
            return False
        return user_can_access_class(user, class_id)

    @action(detail=False, methods=["get"], url_path="students")
    def list_students(self, request: Request) -> Response:
        try:
            class_id = int(request.query_params.get("class_id"))
        except (TypeError, ValueError):
            return Response({"detail": "class_id is required and must be int"}, status=400)
        dt, err = _parse_date_or_400(request.query_params.get("date"))
        if err:
            return err
        # Enforce access: teachers can only load students for their own classes
        if not self._user_has_access_to_class(request.user, class_id):
            return Response({"detail": "not allowed for this class"}, status=403)
        qs = selectors.get_students_for_class_on_date(class_id, dt)
        data = StudentBriefSerializer(qs, many=True).data
        return Response({"students": data, "date": dt.isoformat(), "class_id": class_id})

    @action(detail=False, methods=["get"], url_path="records")
    def list_records(self, request: Request) -> Response:
        try:
            class_id = int(request.query_params.get("class_id"))
        except (TypeError, ValueError):
            return Response({"detail": "class_id is required and must be int"}, status=400)
        dt, err = _parse_date_or_400(request.query_params.get("date"))
        if err:
            return err
        # Enforce access for records as well
        if not self._user_has_access_to_class(request.user, class_id):
            return Response({"detail": "not allowed for this class"}, status=403)
        qs = selectors.get_attendance_records(class_id, dt)
        # Return raw minimal fields for now
        data = [
            {
                "student_id": r.student_id,
                "status": r.status,
                "note": getattr(r, "note", None),
            }
            for r in qs
        ]
        return Response({"records": data, "date": dt.isoformat(), "class_id": class_id})

    @action(detail=False, methods=["get"], url_path="history")
    def list_history(self, request: Request) -> Response:
        """Return paginated attendance history for a class within a date range.
        Query params:
          - class_id: int (required)
          - from: YYYY-MM-DD (default: today-6 days)
          - to: YYYY-MM-DD (default: today)
          - page: int (default 1)
          - page_size: int (default 100, max 200)
        Response: {count, page, page_size, results:[{date,student_id,student_name,status,note}]}
        """
        # Validate class_id
        try:
            class_id = int(request.query_params.get("class_id"))
        except (TypeError, ValueError):
            return Response({"detail": "class_id is required and must be int"}, status=400)
        # Access control
        if not self._user_has_access_to_class(request.user, class_id):
            return Response({"detail": "not allowed for this class"}, status=403)

        # Parse from/to
        from_str = request.query_params.get("from")
        to_str = request.query_params.get("to")
        today = _date.today()
        try:
            dt_to = _date.fromisoformat(to_str) if to_str else today
        except Exception:
            return Response({"detail": "to must be YYYY-MM-DD"}, status=400)
        try:
            dt_from = _date.fromisoformat(from_str) if from_str else (dt_to - timedelta(days=6))
        except Exception:
            return Response({"detail": "from must be YYYY-MM-DD"}, status=400)
        if dt_from > dt_to:
            return Response({"detail": "from must be <= to"}, status=400)

        # Pagination params
        try:
            page = max(1, int(request.query_params.get("page") or 1))
        except Exception:
            page = 1
        try:
            page_size = int(request.query_params.get("page_size") or 100)
        except Exception:
            page_size = 100
        if page_size > 200:
            page_size = 200
        if page_size < 1:
            page_size = 1

        # Query optimized with select_related to avoid N+1 on student and class
        from school.models import AttendanceRecord  # type: ignore

        qs = AttendanceRecord.objects.filter(
            **{_CLASS_FK_ID: class_id}, date__gte=dt_from, date__lte=dt_to
        ).select_related("student", "subject")

        # Filter by teacher's subjects (teachers only see their own subjects)
        qs = _filter_by_teacher_subjects(qs, request.user, class_id)

        qs = qs.order_by("date", "student_id")
        total = qs.count()
        start = (page - 1) * page_size
        end = start + page_size
        page_qs = qs[start:end]
        results = [
            {
                "date": r.date.isoformat(),
                "student_id": r.student_id,
                "student_name": getattr(getattr(r, "student", None), "full_name", None),
                "status": r.status,
                "note": getattr(r, "note", None),
                "period_number": getattr(r, "period_number", None),
                "subject_name": getattr(getattr(r, "subject", None), "name_ar", None),
            }
            for r in page_qs
        ]
        return Response(
            {
                "count": total,
                "page": page,
                "page_size": page_size,
                "from": dt_from.isoformat(),
                "to": dt_to.isoformat(),
                "class_id": class_id,
                "results": results,
            }
        )

    @action(detail=False, methods=["get"], url_path="history-export")
    def history_export(self, request: Request) -> HttpResponse:
        """Export attendance history for a class within a date range.
        Query params: class_id (int, required), from (YYYY-MM-DD), to (YYYY-MM-DD), format(optional): csv|xlsx
        Applies the same access control as list_history.
        Default: CSV (TSV actually for Excel safety). When format=xlsx is provided, returns .xlsx.
        """
        # Validate class_id
        try:
            class_id = int(request.query_params.get("class_id"))
        except (TypeError, ValueError):
            return Response({"detail": "class_id is required and must be int"}, status=400)  # type: ignore[return-value]
        # Access control
        if not self._user_has_access_to_class(request.user, class_id):
            return Response({"detail": "not allowed for this class"}, status=403)  # type: ignore[return-value]
        # Parse dates (defaults align with list_history)
        from_str = request.query_params.get("from")
        to_str = request.query_params.get("to")
        today = _date.today()
        try:
            dt_to = _date.fromisoformat(to_str) if to_str else today
        except Exception:
            return Response({"detail": "to must be YYYY-MM-DD"}, status=400)  # type: ignore[return-value]
        try:
            dt_from = _date.fromisoformat(from_str) if from_str else (dt_to - timedelta(days=6))
        except Exception:
            return Response({"detail": "from must be YYYY-MM-DD"}, status=400)  # type: ignore[return-value]
        if dt_from > dt_to:
            return Response({"detail": "from must be <= to"}, status=400)  # type: ignore[return-value]
        # Cap range to 60 days to avoid heavy exports in dev
        if (dt_to - dt_from).days > 60:
            return Response({"detail": "date range too large; max 60 days"}, status=400)  # type: ignore[return-value]
        # Build queryset
        from school.models import AttendanceRecord  # type: ignore

        qs = AttendanceRecord.objects.filter(
            **{_CLASS_FK_ID: class_id}, date__gte=dt_from, date__lte=dt_to
        ).select_related("student", "subject")

        # Filter by teacher's subjects (teachers only see their own subjects)
        qs = _filter_by_teacher_subjects(qs, request.user, class_id)

        qs = qs.order_by("date", "student_id")
        export_format = (request.query_params.get("format") or "xlsx").lower()
        if export_format == "xlsx":
            # Generate an Excel workbook to guarantee correct Arabic rendering
            try:
                from io import BytesIO
                from openpyxl import Workbook  # type: ignore

                wb = Workbook()
                ws = wb.active
                ws.title = "Attendance"
                # Right-to-left view for Arabic
                try:
                    ws.sheet_view.rightToLeft = True
                except Exception:
                    pass
                headers = [
                    "date/التاريخ",
                    "student_id/رقم الطالب",
                    "student/الطالب",
                    "period/الحصة",
                    "subject/المادة",
                    "status/الحالة",
                    "note/ملاحظة",
                ]
                ws.append(headers)
                # Stream rows to reduce memory/time; avoid per-cell styling loops
                for r in qs.iterator(chunk_size=1000):
                    student_name = getattr(getattr(r, "student", None), "full_name", None)
                    subject_name = getattr(getattr(r, "subject", None), "name_ar", None)
                    ws.append(
                        [
                            r.date.isoformat(),
                            r.student_id,
                            student_name or "",
                            getattr(r, "period_number", "") or "",
                            subject_name or "",
                            r.status,
                            getattr(r, "note", "") or "",
                        ]
                    )
                # Freeze header row
                try:
                    ws.freeze_panes = "A2"
                except Exception:
                    pass
                # Simple column widths
                try:
                    ws.column_dimensions["A"].width = 14  # date
                    ws.column_dimensions["B"].width = 12  # student_id
                    ws.column_dimensions["C"].width = 32  # student name
                    ws.column_dimensions["D"].width = 10  # period
                    ws.column_dimensions["E"].width = 24  # subject
                    ws.column_dimensions["F"].width = 14  # status
                    ws.column_dimensions["G"].width = 40  # note
                except Exception:
                    pass
                bio = BytesIO()
                wb.save(bio)
                data = bio.getvalue()
                filename = (
                    f"attendance_history_{class_id}_{dt_from.isoformat()}_{dt_to.isoformat()}.xlsx"
                )
                resp = HttpResponse(
                    data,
                    content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
                resp["Content-Disposition"] = f'attachment; filename="{filename}"'
                return resp
            except Exception as e:
                # Log and fallback to CSV below if openpyxl missing or error occurred
                try:
                    logger.warning("history_export XLSX generation failed: %s", e)
                except Exception:
                    pass
        # Default: CSV (actually TSV) response for Excel
        filename = f"attendance_history_{class_id}_{dt_from.isoformat()}_{dt_to.isoformat()}.csv"
        resp = HttpResponse(content_type="text/csv; charset=utf-16le")
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        resp.write("\ufeff")
        writer = csv.writer(resp, delimiter="\t", lineterminator="\r\n")
        writer.writerow(
            [
                "date/التاريخ",
                "student_id/رقم الطالب",
                "student/الطالب",
                "period/الحصة",
                "subject/المادة",
                "status/الحالة",
                "note/ملاحظة",
            ]
        )
        for r in qs.iterator(chunk_size=1000):
            student_name = getattr(getattr(r, "student", None), "full_name", None)
            subject_name = getattr(getattr(r, "subject", None), "name_ar", None)
            writer.writerow(
                [
                    r.date.isoformat(),
                    r.student_id,
                    student_name or "",
                    getattr(r, "period_number", "") or "",
                    subject_name or "",
                    r.status,
                    getattr(r, "note", "") or "",
                ]
            )
        return resp

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request: Request) -> Response:
        scope_raw = request.query_params.get("scope", "school")
        scope = (scope_raw or "school").lower()
        if scope not in {"teacher", "wing", "school"}:
            scope = "school"
        dt, err = _parse_date_or_400(request.query_params.get("date"))
        if err:
            return err
        class_id = request.query_params.get("class_id")
        wing_id = request.query_params.get("wing_id")
        try:
            class_id_int = int(class_id) if class_id is not None else None
        except (TypeError, ValueError):
            return Response({"detail": "class_id must be int"}, status=400)
        try:
            wing_id_int = int(wing_id) if wing_id is not None else None
        except (TypeError, ValueError):
            return Response({"detail": "wing_id must be int"}, status=400)
        data = selectors.get_summary(scope=scope, dt=dt, class_id=class_id_int, wing_id=wing_id_int)
        return Response(data)

    @action(detail=False, methods=["get"], url_path="timetable/teacher/today")
    def teacher_timetable_today(self, request: Request) -> Response:
        """Return today's ordered periods for the authenticated teacher.
        Maps request.user->Staff; superuser can pass ?teacher_id to inspect.
        """
        from school.models import Staff  # type: ignore

        dt, err = _parse_date_or_400(request.query_params.get("date"))
        if err:
            return err
        user = request.user
        teacher_id_qs = request.query_params.get("teacher_id")
        staff: Staff | None = None  # type: ignore
        # Resolve staff for this user
        try:
            staff = Staff.objects.filter(user_id=user.id).first()
        except Exception:
            staff = None
        if not staff and getattr(user, "is_superuser", False) and teacher_id_qs:
            try:
                staff = Staff.objects.filter(id=int(teacher_id_qs)).first()
            except Exception:
                staff = None
        if not staff:
            return Response({"periods": []})
        periods = selectors.get_teacher_today_periods(staff_id=staff.id, dt=dt)
        return Response({"date": dt.isoformat(), "periods": periods})

    @action(detail=False, methods=["get"], url_path="timetable/teacher/weekly")
    def teacher_timetable_weekly(self, request: Request) -> Response:
        """Return weekly timetable grid for the authenticated teacher."""
        from school.models import Staff  # type: ignore

        user = request.user
        teacher_id_qs = request.query_params.get("teacher_id")
        staff: Staff | None = None  # type: ignore
        try:
            staff = Staff.objects.filter(user_id=user.id).first()
        except Exception:
            staff = None
        if not staff and getattr(user, "is_superuser", False) and teacher_id_qs:
            try:
                staff = Staff.objects.filter(id=int(teacher_id_qs)).first()
            except Exception:
                staff = None
        if not staff:
            return Response({"days": {str(i): [] for i in range(1, 8)}, "meta": {}})
        grid = selectors.get_teacher_weekly_grid(staff_id=staff.id)
        return Response(grid)

    @action(detail=False, methods=["get"], url_path="teacher/classes")
    def teacher_classes(self, request: Request) -> Response:
        """
        Return classes taught by the authenticated teacher based on TeachingAssignment.
        Relaxed authorization: any authenticated user mapped to a Staff record will get their classes.
        Superusers and wing supervisors can see all classes across assignments.
        """
        from school.models import Staff, TeachingAssignment  # type: ignore  # lazy import to avoid circulars

        user = request.user
        # Determine roles (best-effort; do not block if missing 'teacher' group)
        try:
            roles = set(user.groups.values_list("name", flat=True))  # type: ignore
        except Exception:
            roles = set()
        is_super = bool(getattr(user, "is_superuser", False))
        is_wing = "wing_supervisor" in roles

        # Superuser/wing supervisor: return distinct classrooms across assignments (fallback: all classes)
        if is_super or is_wing:
            try:
                from school.models import Class  # type: ignore

                qs = (
                    TeachingAssignment.objects.select_related("classroom")
                    .values("classroom_id", "classroom__name")
                    .distinct()
                )
                classes = [
                    {"id": row["classroom_id"], "name": row.get("classroom__name")}
                    for row in qs
                    if row.get("classroom_id")
                ]
                if not classes:
                    classes = [
                        {"id": c.id, "name": getattr(c, "name", None)}
                        for c in Class.objects.all().order_by("name")[:200]
                    ]
                return Response({"classes": classes})
            except Exception:
                return Response({"classes": []})

        # Teacher-specific: Map user -> Staff; try fallbacks if OneToOne not set
        staff = None
        try:
            staff = Staff.objects.filter(user_id=user.id).first()
        except Exception:
            staff = None
        if not staff:
            # Fallback by email or full name when possible
            try:
                if getattr(user, "email", None):
                    staff = Staff.objects.filter(email__iexact=user.email).first()
            except Exception:
                staff = staff or None
            if not staff:
                try:
                    full = (user.get_full_name() or "").strip()
                    if full:
                        staff = Staff.objects.filter(full_name__icontains=full).first()
                except Exception:
                    pass
        if not staff:
            # Preserve previous behavior: plain users without staff mapping get 403
            return Response({"detail": "requires teacher role or staff mapping"}, status=403)

        # Gather distinct classrooms from TeachingAssignment for this teacher
        qs = (
            TeachingAssignment.objects.filter(teacher_id=staff.id)
            .select_related("classroom")
            .values("classroom_id", "classroom__name")
            .distinct()
        )
        # If no assignments and user lacks teacher/wing role, keep 403 to match tests/expectations
        if not qs.exists() and ("teacher" not in roles):
            return Response({"detail": "no teaching assignments"}, status=403)
        classes = [{"id": row["classroom_id"], "name": row.get("classroom__name")} for row in qs]
        return Response({"classes": classes})

    @action(detail=False, methods=["post"], url_path="bulk_save")
    def bulk_save(self, request: Request) -> Response:
        payload = request.data or {}
        try:
            class_id = int(payload.get("class_id"))
            dt = _date.fromisoformat(payload.get("date")) if payload.get("date") else _date.today()
            records = payload.get("records") or []
            period_number = payload.get("period_number")
            period_number = (
                int(period_number)
                if period_number
                not in (
                    None,
                    "",
                )
                else None
            )
        except Exception as e:
            return Response({"detail": f"Invalid payload: {e}"}, status=400)
        # Enforce access for saving
        if not self._user_has_access_to_class(request.user, class_id):
            return Response({"detail": "not allowed for this class"}, status=403)
        try:
            saved = bulk_save_attendance(
                class_id=class_id,
                dt=dt,
                records=records,
                actor_user_id=(request.user.id if request.user.is_authenticated else None),
                period_number=period_number,
            )
        except ValueError as e:
            msg = str(e)
            # Map technical messages to user-friendly Arabic guidance
            if msg == "no current term configured":
                msg_ar = "لا توجد فترة دراسية حالية مفعلة"
            elif msg == "date is not a working school day":
                msg_ar = "التاريخ المحدد ليس يوم دوام مدرسي"
            elif msg == "multiple timetable periods found; select a period in the UI":
                msg_ar = "يوجد أكثر من حصة محتملة لليوم — يرجى اختيار الحصة قبل الحفظ"
            elif msg == "no matching timetable entry for this class/teacher on the selected date":
                msg_ar = "لا توجد حصة مطابقة لهذا الصف/المعلم في هذا اليوم"
            elif msg == "could not resolve timetable for provided period_number":
                msg_ar = "تعذر تحديد الحصة المطلوبة — تحقق من الجدول أو رقم الحصة"
            else:
                msg_ar = msg
            return Response({"detail": msg_ar}, status=400)
        return Response({"saved": len(saved)}, status=status.HTTP_200_OK)


# ---- V2 overrides to fix period_number filtering and expose exit_reasons ----


class AttendanceViewSetV2(AttendanceViewSet):
    @action(detail=False, methods=["get"], url_path="teacher/classes")
    def teacher_classes(self, request: Request) -> Response:
        """
        V2 override: Return classes taught by the authenticated teacher.
        If the user lacks a Staff mapping but is in the 'teacher' group, return an empty list (200) instead of 403.
        """
        from school.models import Staff, TeachingAssignment  # type: ignore

        user = request.user
        # Roles
        try:
            roles = set(user.groups.values_list("name", flat=True))  # type: ignore
        except Exception:
            roles = set()
        is_super = bool(getattr(user, "is_superuser", False))
        is_wing = "wing_supervisor" in roles

        if is_super or is_wing:
            try:
                from school.models import Class  # type: ignore

                qs = (
                    TeachingAssignment.objects.select_related("classroom")
                    .values("classroom_id", "classroom__name")
                    .distinct()
                )
                classes = [
                    {"id": row["classroom_id"], "name": row.get("classroom__name")}
                    for row in qs
                    if row.get("classroom_id")
                ]
                if not classes:
                    classes = [
                        {"id": c.id, "name": getattr(c, "name", None)}
                        for c in Class.objects.all().order_by("name")[:200]
                    ]
                return Response({"classes": classes})
            except Exception:
                return Response({"classes": []})

        # Staff mapping
        staff = None
        try:
            staff = Staff.objects.filter(user_id=user.id).first()
        except Exception:
            staff = None
        if not staff:
            try:
                if getattr(user, "email", None):
                    staff = Staff.objects.filter(email__iexact=user.email).first()
            except Exception:
                staff = staff or None
            if not staff:
                try:
                    full = (user.get_full_name() or "").strip()
                    if full:
                        staff = Staff.objects.filter(full_name__icontains=full).first()
                except Exception:
                    pass
        if not staff:
            if "teacher" in roles:
                return Response({"classes": []})
            return Response({"detail": "requires teacher role or staff mapping"}, status=403)

        qs = (
            TeachingAssignment.objects.filter(teacher_id=staff.id)
            .select_related("classroom")
            .values("classroom_id", "classroom__name")
            .distinct()
        )
        # If no assignments and user lacks teacher/wing role, keep 403 to match earlier behavior
        if not qs.exists() and ("teacher" not in roles):
            return Response({"detail": "no teaching assignments"}, status=403)
        classes = [{"id": row["classroom_id"], "name": row.get("classroom__name")} for row in qs]
        return Response({"classes": classes})
    @action(detail=False, methods=["get"], url_path="history-strict")
    def list_history_strict(self, request: Request) -> Response:
        """Strict history: in addition to classroom filter, ensure student's current class matches.
        Same shape as /history but guarantees results only from the selected class.
        """
        # Validate class_id
        try:
            class_id = int(request.query_params.get("class_id"))
        except (TypeError, ValueError):
            return Response({"detail": "class_id is required and must be int"}, status=400)
        # Access control
        if not self._user_has_access_to_class(request.user, class_id):
            return Response({"detail": "not allowed for this class"}, status=403)
        # Parse dates
        from_str = request.query_params.get("from")
        to_str = request.query_params.get("to")
        today = _date.today()
        try:
            dt_to = _date.fromisoformat(to_str) if to_str else today
        except Exception:
            return Response({"detail": "to must be YYYY-MM-DD"}, status=400)
        try:
            dt_from = _date.fromisoformat(from_str) if from_str else (dt_to - timedelta(days=6))
        except Exception:
            return Response({"detail": "from must be YYYY-MM-DD"}, status=400)
        if dt_from > dt_to:
            return Response({"detail": "from must be <= to"}, status=400)
        # Pagination
        try:
            page = max(1, int(request.query_params.get("page") or 1))
        except Exception:
            page = 1
        try:
            page_size = int(request.query_params.get("page_size") or 100)
        except Exception:
            page_size = 100
        if page_size > 200:
            page_size = 200
        if page_size < 1:
            page_size = 1
        # Query
        from school.models import AttendanceRecord  # type: ignore

        qs = (
            AttendanceRecord.objects.filter(
                **{_CLASS_FK_ID: class_id}, date__gte=dt_from, date__lte=dt_to
            )
            .filter(student__class_fk_id=class_id)
            .select_related("student", "subject")
        )

        # Filter by teacher's subjects (teachers only see their own subjects)
        qs = _filter_by_teacher_subjects(qs, request.user, class_id)

        qs = qs.order_by("date", "student_id")
        total = qs.count()
        start = (page - 1) * page_size
        end = start + page_size
        page_qs = qs[start:end]
        results = [
            {
                "date": r.date.isoformat(),
                "student_id": r.student_id,
                "student_name": getattr(getattr(r, "student", None), "full_name", None),
                "status": r.status,
                "note": getattr(r, "note", None),
                "period_number": getattr(r, "period_number", None),
                "subject_name": getattr(getattr(r, "subject", None), "name_ar", None),
            }
            for r in page_qs
        ]
        return Response(
            {
                "count": total,
                "page": page,
                "page_size": page_size,
                "from": dt_from.isoformat(),
                "to": dt_to.isoformat(),
                "class_id": class_id,
                "results": results,
            }
        )

    @action(detail=False, methods=["get"], url_path="records")
    def list_records(self, request: Request) -> Response:  # type: ignore[override]
        try:
            class_id = int(request.query_params.get("class_id"))
        except (TypeError, ValueError):
            return Response({"detail": "class_id is required and must be int"}, status=400)
        dt, err = _parse_date_or_400(request.query_params.get("date"))
        if err:
            return err
        # Optional period filter
        period_qs = request.query_params.get("period_number")
        try:
            period_number = int(period_qs) if period_qs not in (None, "") else None
        except Exception:
            return Response({"detail": "period_number must be int"}, status=400)
        # Access control
        if not self._user_has_access_to_class(request.user, class_id):
            return Response({"detail": "not allowed for this class"}, status=403)
        qs = selectors.get_attendance_records(class_id, dt, period_number=period_number)
        data = []

        def _reason_label(code: str) -> str:
            m = {
                "admin": "إدارة",
                "wing": "مشرف الجناح",
                "nurse": "الممرض",
                "restroom": "دورة المياه",
            }
            return m.get((code or "").strip().lower(), code)

        for r in qs:
            note_val = getattr(r, "note", None)
            exit_reasons_val = getattr(r, "exit_reasons", None)
            if (not note_val) and getattr(r, "status", None) == "excused" and exit_reasons_val:
                try:
                    first = str(exit_reasons_val).split(",")[0].strip()
                    label = _reason_label(first) if first else None
                except Exception:
                    label = None
                note_val = "إذن خروج" + (f" — {label}" if label else "")
            data.append(
                {
                    "student_id": r.student_id,
                    "status": r.status,
                    "note": note_val,
                    "exit_reasons": exit_reasons_val,
                }
            )
        return Response(
            {
                "records": data,
                "date": dt.isoformat(),
                "class_id": class_id,
                "period_number": period_number,
            }
        )


class WingSupervisorViewSet(viewsets.ViewSet):
    """APIs for Wing Supervisors: overview KPIs and missing attendance entries for today (or a given date).
    Scopes data to the wings supervised by the current user. Superusers see all wings.
    """
    from rest_framework.permissions import IsAuthenticated
    permission_classes = [IsAuthenticated]

    def _get_staff_and_wing_ids(self, user):
        try:
            from school.models import Staff, Wing  # type: ignore
        except Exception:
            return None, []
        staff = None
        try:
            staff = Staff.objects.filter(user_id=user.id).first()
        except Exception:
            staff = None
        wing_ids: list[int] = []
        try:
            if getattr(user, "is_superuser", False):
                wing_ids = list(Wing.objects.values_list("id", flat=True))
            elif staff is not None:
                wing_ids = list(Wing.objects.filter(supervisor=staff).values_list("id", flat=True))
        except Exception:
            wing_ids = []
        return staff, wing_ids

    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request: Request) -> Response:
        """Diagnostic endpoint: return current user's roles, staff id, and supervised wings.
        Helps debug cases where the Wing dashboard appears empty due to missing wing assignment.
        """
        # roles (Django groups)
        try:
            roles = list(request.user.groups.values_list("name", flat=True))  # type: ignore
        except Exception:
            roles = []
        staff, wing_ids = self._get_staff_and_wing_ids(request.user)
        # Wing names (best-effort)
        wing_names: list[str] = []
        try:
            from school.models import Wing  # type: ignore

            wing_names = list(Wing.objects.filter(id__in=wing_ids).values_list("name", flat=True))
        except Exception:
            wing_names = []
        return Response(
            {
                "user": {
                    "id": getattr(request.user, "id", None),
                    "username": getattr(request.user, "username", None),
                    "full_name": getattr(request.user, "get_full_name", lambda: None)(),
                    "is_superuser": bool(getattr(request.user, "is_superuser", False)),
                },
                "roles": roles,
                "staff": {"id": getattr(staff, "id", None), "full_name": getattr(staff, "full_name", None)},
                "wings": {"ids": wing_ids, "names": wing_names},
                "has_wing_supervisor_role": ("wing_supervisor" in roles) or bool(getattr(request.user, "is_superuser", False)),
            }
        )

    @action(detail=False, methods=["get"], url_path="overview")
    def overview(self, request: Request) -> Response:
        from . import selectors  # lazy import to avoid circulars
        dt, err = _parse_date_or_400(request.query_params.get("date"))
        if err:
            return err
        staff, wing_ids = self._get_staff_and_wing_ids(request.user)
        if not wing_ids:
            # Graceful empty state
            return Response(
                {
                    "date": dt.isoformat(),
                    "scope": "wing",
                    "kpis": {
                        "present_pct": 0.0,
                        "absent": 0,
                        "late": 0,
                        "excused": 0,
                        "runaway": 0,
                        "present": 0,
                        "total": 0,
                        "exit_events_total": 0,
                        "exit_events_open": 0,
                    },
                    "top_classes": [],
                    "worst_classes": [],
                }
            )
        # Aggregate summaries across multiple wings if needed
        summary = selectors.get_summary(scope="wing", dt=dt, wing_id=wing_ids[0])
        if len(wing_ids) > 1:
            for wid in wing_ids[1:]:
                s2 = selectors.get_summary(scope="wing", dt=dt, wing_id=wid)
                for k in [
                    "absent",
                    "late",
                    "excused",
                    "runaway",
                    "present",
                    "total",
                    "exit_events_total",
                    "exit_events_open",
                ]:
                    summary["kpis"][k] += s2["kpis"][k]
            k = summary["kpis"]
            k["present_pct"] = float(round((k["present"] / k["total"]) * 100, 1)) if k["total"] else 0.0
            summary["scope"] = "wings"
        return Response(summary)

    @action(detail=False, methods=["get"], url_path="missing")
    def missing(self, request: Request) -> Response:
        dt, err = _parse_date_or_400(request.query_params.get("date"))
        if err:
            return err
        try:
            from school.models import Class, AttendanceRecord, TimetableEntry, Term  # type: ignore
            from common.day_utils import iso_to_school_dow
        except Exception:
            return Response({"date": dt.isoformat(), "items": []})

        staff, wing_ids = self._get_staff_and_wing_ids(request.user)
        if not wing_ids:
            return Response({"date": dt.isoformat(), "items": []})

        term = Term.objects.filter(is_current=True).first()
        if not term:
            return Response({"date": dt.isoformat(), "items": []})

        dow = iso_to_school_dow(dt)
        class_ids = list(Class.objects.filter(wing_id__in=wing_ids).values_list("id", flat=True))
        if not class_ids:
            return Response({"date": dt.isoformat(), "items": []})

        tt = (
            TimetableEntry.objects.filter(classroom_id__in=class_ids, day_of_week=dow, term=term)
            .select_related("classroom", "subject", "teacher")
            .order_by("classroom_id", "period_number")
        )
        # Determine class-periods already recorded
        rec = (
            AttendanceRecord.objects.filter(date=dt, classroom_id__in=class_ids)
            .values("classroom_id", "period_number")
            .distinct()
        )
        done = {(r["classroom_id"], r["period_number"]) for r in rec}

        items = []
        for e in tt:
            key = (e.classroom_id, e.period_number)
            if key in done:
                continue
            items.append(
                {
                    "class_id": e.classroom_id,
                    "class_name": getattr(e.classroom, "name", None),
                    "period_number": e.period_number,
                    "subject_id": e.subject_id,
                    "subject_name": getattr(e.subject, "name", None),
                    "teacher_id": e.teacher_id,
                    "teacher_name": getattr(e.teacher, "full_name", None),
                }
            )
        return Response({"date": dt.isoformat(), "count": len(items), "items": items})


    @action(detail=False, methods=["get"], url_path="timetable")
    def wing_timetable(self, request: Request) -> Response:
        """Return wing timetable. Supports ?wing_id, ?date=YYYY-MM-DD, and ?mode=daily|weekly (default daily).
        Data is scoped to the current user's supervised wings unless superuser.
        Includes a lightweight meta object to explain empty states (diagnostics only).
        """
        try:
            from school.models import Class, TimetableEntry, Term  # type: ignore
            from common.day_utils import iso_to_school_dow
        except Exception:
            return Response({"days": {}, "date": None, "items": [], "meta": {"error": "import_failed"}})

        meta: dict[str, object] = {}
        # Determine staff and allowed wings
        staff, allowed_wings = self._get_staff_and_wing_ids(request.user)
        meta["allowed_wings_count"] = len(allowed_wings)
        # wing_id selection
        wing_qs = request.query_params.get("wing_id")
        try:
            wing_id = int(wing_qs) if wing_qs not in (None, "") else (allowed_wings[0] if allowed_wings else None)
        except Exception:
            return Response({"detail": "wing_id must be int"}, status=400)
        if not wing_id:
            meta["reason"] = "no_wing"
            return Response({"date": None, "days": {}, "items": [], "meta": meta})
        if allowed_wings and wing_id not in allowed_wings and not getattr(request.user, "is_superuser", False):
            return Response({"detail": "not allowed for this wing"}, status=403)

        term = Term.objects.filter(is_current=True).first()
        if not term:
            meta["reason"] = "no_term"
            return Response({"date": None, "days": {}, "items": [], "meta": meta})

        # Parse date and mode
        dt, err = _parse_date_or_400(request.query_params.get("date"))
        if err:
            return err
        mode = (request.query_params.get("mode") or "daily").lower()
        if mode not in {"daily", "weekly"}:
            mode = "daily"

        # Resolve classes of this wing
        class_ids = list(Class.objects.filter(wing_id=wing_id).values_list("id", flat=True))
        if not class_ids:
            meta["reason"] = "no_classes"
            return Response({"date": dt.isoformat() if dt else None, "days": {}, "items": [], "meta": meta})

        # Subject color helper
        def subject_color(subj_id: int) -> str:
            try:
                h = (int(subj_id) * 47) % 360
                return f"hsl({h}, 60%, 85%)"
            except Exception:
                return "#eef5ff"

        if mode == "weekly":
            # Build period time maps per school day using PeriodTemplate/TemplateSlot (1=Sun..7=Sat)
            times_per_day: dict[int, dict[int, tuple]] = {d: {} for d in range(1, 8)}
            period_times: dict[int, tuple] = {}
            try:
                from school.models import PeriodTemplate, TemplateSlot  # type: ignore

                for sd in range(1, 8):  # Sun..Sat
                    tpl_ids = list(
                        PeriodTemplate.objects.filter(day_of_week=sd).values_list("id", flat=True)
                    )
                    if not tpl_ids:
                        continue
                    slots = (
                        TemplateSlot.objects.filter(template_id__in=tpl_ids, kind="lesson")
                        .exclude(number__isnull=True)
                        .order_by("number", "start_time")
                    )
                    td: dict[int, tuple] = {}
                    for s in slots:
                        td[int(s.number)] = (s.start_time, s.end_time)
                    if td:
                        times_per_day[sd] = td
                # Fallback: fill empty days with first non-empty day's map
                fallback_map = None
                for d in range(1, 8):
                    if times_per_day.get(d):
                        fallback_map = times_per_day[d]
                        break
                if fallback_map:
                    for d in range(1, 8):
                        if not times_per_day.get(d):
                            times_per_day[d] = fallback_map
                # Representative period_times (preserve existing field for backward compatibility)
                for d in range(1, 8):
                    if times_per_day.get(d):
                        period_times = dict(times_per_day[d])
                        break
            except Exception:
                pass

            # Build week days structure including Fri/Sat (may remain empty)
            days = {i: [] for i in [1, 2, 3, 4, 5, 6, 7]}
            qs = (
                TimetableEntry.objects.filter(classroom_id__in=class_ids, term=term)
                .select_related("classroom", "subject", "teacher")
                .order_by("day_of_week", "period_number", "classroom__name")
            )
            for e in qs:
                if e.day_of_week not in days:
                    continue
                st_et = times_per_day.get(int(e.day_of_week), {}).get(int(e.period_number)) or period_times.get(int(e.period_number))
                days[e.day_of_week].append(
                    {
                        "class_id": e.classroom_id,
                        "class_name": getattr(e.classroom, "name", None),
                        "period_number": e.period_number,
                        "subject_id": e.subject_id,
                        "subject_name": getattr(e.subject, "name_ar", None) or getattr(e.subject, "name", None),
                        "teacher_id": e.teacher_id,
                        "teacher_name": getattr(e.teacher, "full_name", None),
                        "color": subject_color(e.subject_id),
                        **({"start_time": st_et[0], "end_time": st_et[1]} if st_et else {}),
                    }
                )
            # Convert keys to strings for JSON stability and expose per-day period times
            meta["period_times_by_day"] = {str(d): {int(k): v for k, v in (times_per_day.get(d) or {}).items()} for d in range(1, 8)}
            meta["period_times"] = {int(k): v for k, v in period_times.items()} if period_times else {}
            return Response({
                "mode": "weekly",
                "term_id": getattr(term, "id", None),
                "wing_id": wing_id,
                "days": {str(k): v for k, v in days.items()},
                "meta": meta,
            })

        # Daily mode
        dow = iso_to_school_dow(dt)
        # Build period times for all school days and pick the active day's map with fallback
        period_times_by_day: dict[int, dict[int, tuple]] = {d: {} for d in range(1, 8)}
        try:
            from school.models import PeriodTemplate, TemplateSlot  # type: ignore
            for sd in range(1, 8):
                tpl_ids = list(PeriodTemplate.objects.filter(day_of_week=sd).values_list("id", flat=True))
                if not tpl_ids:
                    continue
                slots = (
                    TemplateSlot.objects.filter(template_id__in=tpl_ids, kind="lesson")
                    .exclude(number__isnull=True)
                    .order_by("number", "start_time")
                )
                td: dict[int, tuple] = {}
                for s in slots:
                    td[int(s.number)] = (s.start_time, s.end_time)
                if td:
                    period_times_by_day[sd] = td
            # Fallback: use first non-empty day's map when selected day is empty
            fallback_map = None
            for d2 in range(1, 8):
                if period_times_by_day.get(d2):
                    fallback_map = period_times_by_day[d2]
                    break
            if fallback_map and not period_times_by_day.get(dow):
                period_times_by_day[dow] = fallback_map
        except Exception:
            pass
        period_times = period_times_by_day.get(dow, {})

        qs = (
            TimetableEntry.objects.filter(classroom_id__in=class_ids, day_of_week=dow, term=term)
            .select_related("classroom", "subject", "teacher")
            .order_by("period_number", "classroom__name")
        )
        items = []
        for e in qs:
            st_et = period_times.get(int(e.period_number))
            items.append(
                {
                    "class_id": e.classroom_id,
                    "class_name": getattr(e.classroom, "name", None),
                    "period_number": e.period_number,
                    "subject_id": e.subject_id,
                    "subject_name": getattr(e.subject, "name_ar", None) or getattr(e.subject, "name", None),
                    "teacher_id": e.teacher_id,
                    "teacher_name": getattr(e.teacher, "full_name", None),
                    "color": subject_color(e.subject_id),
                    **({"start_time": st_et[0], "end_time": st_et[1]} if st_et else {}),
                }
            )
        if not items:
            meta["reason"] = "no_entries_today"
        # Expose both the effective map and all-day maps for the UI
        meta["period_times_by_day"] = {str(d): {int(k): v for k, v in (period_times_by_day.get(d) or {}).items()} for d in range(1, 8)}
        meta["period_times"] = {int(k): v for k, v in period_times.items()} if period_times else {}
        return Response({
            "mode": "daily",
            "date": dt.isoformat(),
            "dow": dow,
            "term_id": getattr(term, "id", None),
            "wing_id": wing_id,
            "items": items,
            "meta": meta,
        })

class ExitEventViewSet(viewsets.ModelViewSet):
    from rest_framework.permissions import IsAuthenticated

    permission_classes = [IsAuthenticated]
    serializer_class = ExitEventSerializer
    queryset = None  # set in get_queryset to apply permissions

    def get_queryset(self):
        from school.models import ExitEvent  # type: ignore

        qs = ExitEvent.objects.all()
        # Optional filtering
        student_id = self.request.query_params.get("student_id")
        class_id = self.request.query_params.get("class_id")
        date = self.request.query_params.get("date")
        if student_id:
            try:
                qs = qs.filter(student_id=int(student_id))
            except Exception:
                pass
        if class_id:
            try:
                qs = qs.filter(classroom_id=int(class_id))
            except Exception:
                pass
        if date:
            try:
                qs = qs.filter(date=date)
            except Exception:
                pass
        return qs

    def create(self, request: Request, *args, **kwargs):
        from school.models import ExitEvent  # type: ignore
        from django.utils import timezone

        # Ensure date is present; default to today if omitted
        data = request.data.copy()
        req_date = data.get("date") or timezone.localdate().isoformat()
        data["date"] = req_date

        # Debug: log incoming data
        logger.info(f"ExitEvent create - incoming data: {data}")

        # Validate the data using serializer (handles field normalization)
        ser = ExitEventSerializer(data=data)
        if not ser.is_valid():
            # Return detailed validation errors for debugging
            logger.error(f"ExitEvent validation failed: {ser.errors}")
            return Response({"detail": "بيانات غير صالحة", "errors": ser.errors}, status=400)

        # Debug: log validated data
        logger.info(f"ExitEvent validated_data: {ser.validated_data}")
        logger.info(
            f"ExitEvent validated_data types: {[(k, type(v).__name__) for k, v in ser.validated_data.items()]}"
        )

        # Get student instance from validated data (PrimaryKeyRelatedField returns the instance)
        student = ser.validated_data.get("student")
        if not student:
            return Response({"detail": "student is required"}, status=400)

        logger.info(f"Student object: {student}, type: {type(student)}")

        # Block any action for inactive students
        try:
            if getattr(student, "active", True) is False:
                return Response({"detail": "لا يمكن إجراء أي إجراء على طالب غير فعال"}, status=400)
        except Exception:
            pass

        # Only block if an open session exists for the same student on the same date
        open_exists = ExitEvent.objects.filter(
            student=student, date=req_date, returned_at__isnull=True
        ).exists()
        if open_exists:
            return Response(
                {
                    "detail": "يوجد جلسة خروج مفتوحة لهذا الطالب في نفس اليوم",
                    "date": req_date,
                },
                status=400,
            )

        # Save the exit event
        obj = ser.save(started_by=getattr(request, "user", None))
        return Response(
            {"id": obj.id, "started_at": timezone.localtime(obj.started_at).isoformat()}, status=201
        )

    @action(detail=True, methods=["patch"], url_path="return")
    def return_now(self, request: Request, pk=None):
        from school.models import ExitEvent  # type: ignore

        try:
            obj = ExitEvent.objects.get(pk=pk)
        except ExitEvent.DoesNotExist:
            return Response({"detail": "not found"}, status=404)
        obj.close(user=getattr(request, "user", None))
        return Response(
            {
                "id": obj.id,
                "returned_at": (
                    timezone.localtime(obj.returned_at).isoformat() if obj.returned_at else None
                ),
                "duration_seconds": obj.duration_seconds,
            }
        )

    @action(detail=False, methods=["get"], url_path="open")
    def open_events(self, request: Request):
        from school.models import ExitEvent  # type: ignore

        qs = ExitEvent.objects.filter(returned_at__isnull=True)
        class_id = request.query_params.get("class_id")
        date = request.query_params.get("date")
        if class_id:
            try:
                qs = qs.filter(classroom_id=int(class_id))
            except Exception:
                pass
        if date:
            qs = qs.filter(date=date)
        data = [
            {
                "id": e.id,
                "student_id": e.student_id,
                "student_name": getattr(getattr(e, "student", None), "full_name", None),
                "started_at": timezone.localtime(e.started_at).isoformat(),
                "reason": e.reason,
            }
            for e in qs
        ]
        return Response(data)