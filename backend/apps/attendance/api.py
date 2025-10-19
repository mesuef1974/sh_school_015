from datetime import date as _date, timedelta

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.request import Request
from django.http import HttpResponse
import csv
import logging

from .serializers import StudentBriefSerializer
from . import selectors
from .services.attendance import bulk_save_attendance
from .selectors import _CLASS_FK_ID  # reuse detected class FK field

logger = logging.getLogger(__name__)


def _parse_date_or_400(dt_str: str | None):
    """Parse ISO date (YYYY-MM-DD) or return (None, Response(400)). If empty, return today."""
    if not dt_str:
        return _date.today(), None
    try:
        return _date.fromisoformat(dt_str), None
    except Exception:
        return None, Response({"detail": "date must be YYYY-MM-DD"}, status=400)


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

        qs = (
            AttendanceRecord.objects.filter(
                **{_CLASS_FK_ID: class_id}, date__gte=dt_from, date__lte=dt_to
            )
            .select_related("student")
            .order_by("date", "student_id")
        )
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

        qs = (
            AttendanceRecord.objects.filter(
                **{_CLASS_FK_ID: class_id}, date__gte=dt_from, date__lte=dt_to
            )
            .select_related("student")
            .order_by("date", "student_id")
        )
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
                    "status/الحالة",
                    "note/ملاحظة",
                ]
                ws.append(headers)
                # Stream rows to reduce memory/time; avoid per-cell styling loops
                for r in qs.iterator(chunk_size=1000):
                    student_name = getattr(getattr(r, "student", None), "full_name", None)
                    ws.append(
                        [
                            r.date.isoformat(),
                            r.student_id,
                            student_name or "",
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
                    ws.column_dimensions["A"].width = 14
                    ws.column_dimensions["B"].width = 12
                    ws.column_dimensions["C"].width = 32
                    ws.column_dimensions["D"].width = 14
                    ws.column_dimensions["E"].width = 40
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
                "status/الحالة",
                "note/ملاحظة",
            ]
        )
        for r in qs.iterator(chunk_size=1000):
            student_name = getattr(getattr(r, "student", None), "full_name", None)
            writer.writerow(
                [
                    r.date.isoformat(),
                    r.student_id,
                    student_name or "",
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
                actor_user_id=request.user.id if request.user.is_authenticated else None,
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

        qs = (
            AttendanceRecord.objects.filter(
                **{_CLASS_FK_ID: class_id}, date__gte=dt_from, date__lte=dt_to
            )
            .select_related("student")
            .order_by("date", "student_id")
        )
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

        qs = (
            AttendanceRecord.objects.filter(
                **{_CLASS_FK_ID: class_id}, date__gte=dt_from, date__lte=dt_to
            )
            .select_related("student")
            .order_by("date", "student_id")
        )
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
                    "status/الحالة",
                    "note/ملاحظة",
                ]
                ws.append(headers)
                # Stream rows to reduce memory/time; avoid per-cell styling loops
                for r in qs.iterator(chunk_size=1000):
                    student_name = getattr(getattr(r, "student", None), "full_name", None)
                    ws.append(
                        [
                            r.date.isoformat(),
                            r.student_id,
                            student_name or "",
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
                    ws.column_dimensions["A"].width = 14
                    ws.column_dimensions["B"].width = 12
                    ws.column_dimensions["C"].width = 32
                    ws.column_dimensions["D"].width = 14
                    ws.column_dimensions["E"].width = 40
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
                "status/الحالة",
                "note/ملاحظة",
            ]
        )
        for r in qs.iterator(chunk_size=1000):
            student_name = getattr(getattr(r, "student", None), "full_name", None)
            writer.writerow(
                [
                    r.date.isoformat(),
                    r.student_id,
                    student_name or "",
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
                actor_user_id=request.user.id if request.user.is_authenticated else None,
                period_number=period_number,
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)
        return Response({"saved": len(saved)}, status=status.HTTP_200_OK)


# ---- V2 overrides to fix period_number filtering and expose exit_reasons ----


class AttendanceViewSetV2(AttendanceViewSet):
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
            .select_related("student")
            .order_by("date", "student_id")
        )
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
                "restroom": "حمام",
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
