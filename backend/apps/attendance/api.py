# ruff: noqa: I001, E501
import csv
import logging
from datetime import date as _date
from datetime import timedelta

from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from . import selectors
from .selectors import _CLASS_FK_ID  # reuse detected class FK field
from .serializers import ExitEventSerializer, StudentBriefSerializer
from .services.attendance import bulk_save_attendance

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
    valid_assignments = TeachingAssignment.objects.filter(teacher_id=staff.id, classroom_id=class_id).values_list(
        "subject_id", flat=True
    )

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
                filename = f"attendance_history_{class_id}_{dt_from.isoformat()}_{dt_to.isoformat()}.xlsx"
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

    @action(detail=False, methods=["post"], url_path="submit")
    def submit_for_review(self, request: Request) -> Response:
        """Mark all attendance records for the given class/date (and optional period)
        as submitted without closing them. Records remain editable until a wing supervisor approves.
        Submission is indicated by a '[SUBMITTED @ ts]' tag in note and keeping locked=False.
        Payload: { class_id:int, date:YYYY-MM-DD, period_number?:int|null }
        """
        payload = request.data or {}
        try:
            class_id = int(payload.get("class_id"))
            dt = _date.fromisoformat(payload.get("date")) if payload.get("date") else _date.today()
            period_number = payload.get("period_number")
            period_number = int(period_number) if period_number not in (None, "") else None
        except Exception as e:
            return Response({"detail": f"Invalid payload: {e}"}, status=400)
        # access control
        if not self._user_has_access_to_class(request.user, class_id):
            return Response({"detail": "not allowed for this class"}, status=403)
        try:
            from django.utils import timezone
            from school.models import AttendanceRecord, Term  # type: ignore

            # resolve term best-effort similar to services
            term = Term.objects.filter(start_date__lte=dt, end_date__gte=dt).order_by("-start_date").first()
            if not term:
                term = Term.objects.order_by("-start_date").first()
            qs = AttendanceRecord.objects.filter(classroom_id=class_id, date=dt, term=term)
            if period_number:
                qs = qs.filter(period_number=period_number)
            now = timezone.now().strftime("%Y-%m-%d %H:%M")
            tag = f"[SUBMITTED @ {now}]"
            submitted = 0
            for r in qs:
                note = (getattr(r, "note", "") or "").strip()
                # Avoid duplicate tag
                if "[SUBMITTED" not in note:
                    r.note = f"{tag} {note}".strip()[:300]
                # Keep open/editable until supervisor approval
                r.locked = False
                # Ensure source reflects teacher submission unless already supervisor
                if getattr(r, "source", "teacher") != "supervisor":
                    r.source = "teacher"
                try:
                    r.save(update_fields=["note", "locked", "source", "updated_at"])
                    submitted += 1
                except Exception:
                    continue
            return Response(
                {
                    "submitted": int(submitted),
                    "class_id": class_id,
                    "date": dt.isoformat(),
                    "period_number": period_number,
                }
            )
        except Exception as e:
            return Response({"detail": f"failed to submit: {e}"}, status=500)


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
                filename = f"attendance_history_{class_id}_{dt_from.isoformat()}_{dt_to.isoformat()}.xlsx"
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
            AttendanceRecord.objects.filter(**{_CLASS_FK_ID: class_id}, date__gte=dt_from, date__lte=dt_to)
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
    Also exposes a minimal approvals workflow over teacher-submitted attendance, where
    submission is modeled by the `locked` flag on AttendanceRecord.

    Additionally, exposes a daily aggregated absence status per student (الحالة العامة اليومية)
    using the same first-two-periods policy used by alerts.
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
        """Return current Wing Supervisor context: roles, staff, supervised wings, and primary wing details.
        This augments the previous diagnostic payload with `primary_wing` fields used in page headers.
        """
        # roles (Django groups)
        try:
            roles = list(request.user.groups.values_list("name", flat=True))  # type: ignore
        except Exception:
            roles = []
        staff, wing_ids = self._get_staff_and_wing_ids(request.user)
        # Wing names and primary wing info (best-effort)
        wing_names: list[str] = []
        primary_wing = None
        try:
            from school.models import Wing  # type: ignore

            wings_qs = Wing.objects.filter(id__in=wing_ids)
            wing_names = list(wings_qs.values_list("name", flat=True))
            # Choose the first as primary (sorted by id for stability)
            primary = wings_qs.order_by("id").first()
            if primary is not None:
                # Derive a numeric label: try to extract digits from name, otherwise fallback to id
                import re

                m = re.search(r"(\d+)", primary.name or "")
                wing_number = int(m.group(1)) if m else int(getattr(primary, "id", 0) or 0)
                supervisor_full_name = None
                try:
                    supervisor_full_name = getattr(getattr(primary, "supervisor", None), "full_name", None)
                except Exception:
                    supervisor_full_name = None
                primary_wing = {
                    "id": getattr(primary, "id", None),
                    "name": getattr(primary, "name", None),
                    "number": wing_number,
                    "supervisor_full_name": supervisor_full_name,
                }
        except Exception:
            wing_names = []
            primary_wing = None
        return Response(
            {
                "user": {
                    "id": getattr(request.user, "id", None),
                    "username": getattr(request.user, "username", None),
                    "full_name": getattr(request.user, "get_full_name", lambda: None)(),
                    "is_superuser": bool(getattr(request.user, "is_superuser", False)),
                },
                "roles": roles,
                "staff": {
                    "id": getattr(staff, "id", None),
                    "full_name": getattr(staff, "full_name", None),
                },
                "wings": {"ids": wing_ids, "names": wing_names},
                "primary_wing": primary_wing,
                "has_wing_supervisor_role": ("wing_supervisor" in roles)
                or bool(getattr(request.user, "is_superuser", False)),
            }
        )

    @action(detail=False, methods=["get"], url_path="students")
    def students(self, request: Request) -> Response:
        """List students scoped to the supervisor's wing(s) for use in pickers and tables.
        Optional filters:
          - q: search in full_name (icontains) or sid (startswith)
          - class_id: restrict to a specific class
        Returns fields useful for wing supervisor views: id, sid, full_name, class_id, class_name,
        parent_name, parent_phone, extra_phone_no, phone_no, active, needs
        """
        staff, wing_ids = self._get_staff_and_wing_ids(request.user)
        if not wing_ids and not getattr(request.user, "is_superuser", False):
            return Response({"items": []})
        q = (request.query_params.get("q") or "").strip()
        class_id = request.query_params.get("class_id")
        try:
            class_id_int = int(class_id) if class_id else None
        except Exception:
            class_id_int = None
        try:
            from django.db.models import Q
            from school.models import Student  # type: ignore

            qs = Student.objects.select_related("class_fk")
            if wing_ids and not getattr(request.user, "is_superuser", False):
                qs = qs.filter(class_fk__wing_id__in=wing_ids)
            if class_id_int:
                qs = qs.filter(class_fk_id=class_id_int)
            if q:
                qs = qs.filter(Q(full_name__icontains=q) | Q(sid__startswith=q))
            qs = qs.order_by("class_fk_id", "full_name")[:300]
            items = [
                {
                    "id": s.id,
                    "sid": getattr(s, "sid", None),
                    "full_name": getattr(s, "full_name", None),
                    "class_id": getattr(s, "class_fk_id", None),
                    "class_name": getattr(getattr(s, "class_fk", None), "name", None),
                    # Extra info for wing supervisor
                    "parent_name": getattr(s, "parent_name", None),
                    "parent_phone": getattr(s, "parent_phone", None),
                    "extra_phone_no": getattr(s, "extra_phone_no", None),
                    "phone_no": getattr(s, "phone_no", None),
                    "active": bool(getattr(s, "active", False)),
                    "needs": bool(getattr(s, "needs", False)),
                }
                for s in qs
            ]
            return Response({"items": items})
        except Exception as e:
            return Response({"detail": f"failed: {e}"}, status=500)

    @action(detail=False, methods=["get"], url_path="classes")
    def classes(self, request: Request) -> Response:
        """List classes scoped to the supervisor's wing(s) with basic info.
        Optional filter: q (search in name or section)
        Returns: { items: [{id, name, grade, section, wing_id, wing_name, students_count}] }
        """
        staff, wing_ids = self._get_staff_and_wing_ids(request.user)
        if not wing_ids and not getattr(request.user, "is_superuser", False):
            return Response({"items": []})
        q = (request.query_params.get("q") or "").strip()
        try:
            from django.db.models import Q
            from school.models import Class  # type: ignore

            qs = Class.objects.select_related("wing")
            if wing_ids and not getattr(request.user, "is_superuser", False):
                qs = qs.filter(wing_id__in=wing_ids)
            if q:
                qs = qs.filter(Q(name__icontains=q) | Q(section__icontains=q))
            # Order: grade asc, name asc for predictability
            try:
                qs = qs.order_by("grade", "name")
            except Exception:
                qs = qs.order_by("name")
            items = [
                {
                    "id": c.id,
                    "name": getattr(c, "name", None),
                    "grade": getattr(c, "grade", None),
                    "section": getattr(c, "section", None),
                    "wing_id": getattr(c, "wing_id", None),
                    "wing_name": getattr(getattr(c, "wing", None), "name", None),
                    "students_count": getattr(c, "students_count", 0),
                }
                for c in qs[:300]
            ]
            return Response({"items": items})
        except Exception as e:
            return Response({"detail": f"failed: {e}"}, status=500)

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

    @action(detail=False, methods=["get"], url_path="daily-absences")
    def daily_absences(self, request: Request) -> Response:
        """Return general daily absence status per student for the supervisor's wing(s).
        Uses first-two-periods rule consistent with Absence Alerts policy.
        Query params: date=YYYY-MM-DD (default today), class_id?:int
        Response shape:
        {
            date: str,
            counts: { excused: int, unexcused: int, none: int },
            items: [
                { student_id, student_name, class_id, class_name, state: 'excused'|'unexcused'|'none',
                  p1?: str|null, p2?: str|null }
            ]
        }
        """
        from school.models import AttendanceRecord, Term, AttendancePolicy, SchoolHoliday  # type: ignore

        dt, err = _parse_date_or_400(request.query_params.get("date"))
        if err:
            return err
        class_id_qs = request.query_params.get("class_id")
        try:
            class_id_int = int(class_id_qs) if class_id_qs else None
        except Exception:
            class_id_int = None

        # Wing scoping
        staff, wing_ids = self._get_staff_and_wing_ids(request.user)
        if not wing_ids and not getattr(request.user, "is_superuser", False):
            return Response(
                {
                    "date": dt.isoformat(),
                    "counts": {"excused": 0, "unexcused": 0, "none": 0},
                    "items": [],
                }
            )

        # Holiday check
        try:
            if SchoolHoliday.objects.filter(date=dt).exists():
                return Response(
                    {
                        "date": dt.isoformat(),
                        "counts": {"excused": 0, "unexcused": 0, "none": 0},
                        "items": [],
                    }
                )
        except Exception:
            pass

        # Determine policy for the date
        try:
            term = Term.objects.filter(start_date__lte=dt, end_date__gte=dt).order_by("-start_date").first()
            pol = AttendancePolicy.objects.filter(term=term).order_by("-id").first() if term else None
            first_two = set((pol.first_two_periods_numbers or [1, 2])) if pol else {1, 2}
            working_days = set(pol.working_days or [1, 2, 3, 4, 5]) if pol else {1, 2, 3, 4, 5}
        except Exception:
            first_two = {1, 2}
            working_days = {1, 2, 3, 4, 5}

        # Fetch first-two-periods records for the date and supervised wings
        qs = (
            AttendanceRecord.objects.filter(date=dt, period_number__in=list(first_two))
            .select_related("student", "classroom")
            .order_by("classroom_id", "student_id", "period_number")
        )
        if class_id_int:
            qs = qs.filter(classroom_id=class_id_int)
        if wing_ids and not getattr(request.user, "is_superuser", False):
            try:
                qs = qs.filter(classroom__wing_id__in=wing_ids)
            except Exception:
                pass

        per_student: dict[int, dict] = {}
        # Map period numbers to p1/p2 labels deterministically
        map_slots = {}
        p_sorted = sorted(first_two)
        if len(p_sorted) >= 1:
            map_slots[p_sorted[0]] = "p1"
        if len(p_sorted) >= 2:
            map_slots[p_sorted[1]] = "p2"

        for r in qs[:10000]:  # safety cap
            sid = r.student_id
            if sid not in per_student:
                per_student[sid] = {
                    "student_id": sid,
                    "student_name": getattr(getattr(r, "student", None), "full_name", None),
                    "class_id": getattr(r, "classroom_id", None),
                    "class_name": getattr(getattr(r, "classroom", None), "name", None),
                    "p1": None,
                    "p2": None,
                }
            key = map_slots.get(getattr(r, "period_number", None))
            if key:
                per_student[sid][key] = getattr(r, "status", None)

        # Classify according to policy
        UNEXCUSED = {"absent", "runaway"}
        EXCUSED = {"excused"}
        NEUTRAL = {"present", "late", "left_early"}

        items = []
        counts = {"excused": 0, "unexcused": 0, "none": 0}
        for rec in per_student.values():
            s1 = rec.get("p1")
            s2 = rec.get("p2")
            # If working day filter can be applied via any row's day_of_week, but rows already limited to date.
            state = "none"
            if s1 is not None and s2 is not None:
                if s1 in NEUTRAL or s2 in NEUTRAL:
                    state = "none"
                elif (s1 in UNEXCUSED) or (s2 in UNEXCUSED):
                    state = "unexcused"
                elif (s1 in EXCUSED) and (s2 in EXCUSED):
                    state = "excused"
                else:
                    state = "none"
            rec_out = {**rec, "state": state}
            items.append(rec_out)
            counts[state] = counts.get(state, 0) + 1

        # Sort with priority: unexcused, excused, none; then by class and name
        prio = {"unexcused": 0, "excused": 1, "none": 2}
        items.sort(
            key=lambda x: (
                prio.get(x.get("state"), 9),
                x.get("class_name") or "",
                x.get("student_name") or "",
            )
        )
        return Response({"date": dt.isoformat(), "counts": counts, "items": items})

    @action(detail=False, methods=["get"], url_path="daily-absences/export")
    def daily_absences_export(self, request: Request) -> HttpResponse:
        """Export the general daily absence classification as CSV (UTF-8 with BOM).
        Query params: date=YYYY-MM-DD, class_id?:int
        Columns: student_id, student_name, class_id, class_name, p1, p2, state
        """
        # Reuse the logic from daily_absences to build items
        resp_json = self.daily_absences(request).data  # type: ignore
        # If daily_absences returned a DRF Response with error status, forward as is
        if isinstance(resp_json, Response):
            return resp_json  # type: ignore
        items = resp_json.get("items", []) if isinstance(resp_json, dict) else []
        # Build CSV
        import io

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["student_id", "student_name", "class_id", "class_name", "p1", "p2", "state"])
        for it in items:
            writer.writerow(
                [
                    it.get("student_id"),
                    (it.get("student_name") or ""),
                    it.get("class_id"),
                    (it.get("class_name") or ""),
                    (it.get("p1") or ""),
                    (it.get("p2") or ""),
                    (it.get("state") or ""),
                ]
            )
        csv_text = output.getvalue()
        # Prepend BOM for Excel compatibility
        bom = "\ufeff"
        content = (bom + csv_text).encode("utf-8")
        resp = HttpResponse(content, content_type="text/csv; charset=utf-8")
        dt_str = resp_json.get("date") if isinstance(resp_json, dict) else timezone.localdate().isoformat()
        resp["Content-Disposition"] = f"attachment; filename=wing-daily-absences-{dt_str}.csv"
        return resp

    @action(detail=False, methods=["get"], url_path="pending")
    def pending(self, request: Request) -> Response:
        """List submitted attendance items awaiting supervisor decision.
        Submission is indicated by a '[SUBMITTED @ ts]' tag in note OR legacy locked=True without supervisor source.
        Results are scoped to the wings supervised by the current user (or all if superuser).
        Query params: date=YYYY-MM-DD (default today), class_id?:int
        """
        dt, err = _parse_date_or_400(request.query_params.get("date"))
        if err:
            return err
        class_id_qs = request.query_params.get("class_id")
        try:
            class_id_int = int(class_id_qs) if class_id_qs else None
        except Exception:
            class_id_int = None
        staff, wing_ids = self._get_staff_and_wing_ids(request.user)
        if not wing_ids and not getattr(request.user, "is_superuser", False):
            return Response({"date": dt.isoformat(), "count": 0, "items": []})
        try:
            from django.db.models import Q
            from school.models import AttendanceRecord  # type: ignore

            qs = (
                AttendanceRecord.objects.filter(date=dt)
                .select_related("student", "classroom", "subject", "teacher")
                .order_by("classroom_id", "period_number", "student_id")
            )
            # Pending criteria: marked submitted in note OR legacy locked but not yet approved by supervisor
            qs = qs.filter(Q(note__icontains="[SUBMITTED") | (Q(locked=True) & ~Q(source="supervisor")))
            if class_id_int:
                qs = qs.filter(classroom_id=class_id_int)
            if wing_ids and not getattr(request.user, "is_superuser", False):
                qs = qs.filter(classroom__wing_id__in=wing_ids)
            items = []
            for r in qs[:2000]:  # safety cap
                items.append(
                    {
                        "id": r.id,
                        "student_id": r.student_id,
                        "student_name": getattr(getattr(r, "student", None), "full_name", None),
                        "class_id": getattr(r, "classroom_id", None),
                        "class_name": getattr(getattr(r, "classroom", None), "name", None),
                        "period_number": getattr(r, "period_number", None),
                        "status": getattr(r, "status", None),
                        "note": getattr(r, "note", None),
                        "subject_name": getattr(getattr(r, "subject", None), "name_ar", None),
                        "teacher_name": getattr(getattr(r, "teacher", None), "full_name", None),
                    }
                )
            return Response({"date": dt.isoformat(), "count": len(items), "items": items})
        except Exception as e:
            return Response({"detail": f"failed: {e}"}, status=500)

    @action(detail=False, methods=["post"], url_path="decide")
    def approvals_decide(self, request: Request) -> Response:
        """Approve or reject a batch of attendance records by IDs.
        Payload: { action: 'approve'|'reject', ids: number[], comment?: string }
        Approve keeps records locked and annotates note; reject unlocks records for teacher correction.
        """
        payload = request.data or {}
        action = (payload.get("action") or "").strip().lower()
        ids = payload.get("ids") or []
        if action not in ("approve", "reject"):
            return Response({"detail": "action must be approve|reject"}, status=400)
        if not isinstance(ids, list) or not ids:
            return Response({"detail": "ids must be a non-empty list"}, status=400)
        comment = (payload.get("comment") or "").strip()
        staff, wing_ids = self._get_staff_and_wing_ids(request.user)
        if not wing_ids and not getattr(request.user, "is_superuser", False):
            return Response({"detail": "no wing scope"}, status=403)
        try:
            from django.utils import timezone
            from school.models import AttendanceRecord  # type: ignore

            now = timezone.now().strftime("%Y-%m-%d %H:%M")
            reviewer = getattr(staff, "full_name", None) or getattr(request.user, "username", "")
            prefix = "APPROVED" if action == "approve" else "REJECTED"
            updated = 0
            qs = AttendanceRecord.objects.filter(id__in=ids)
            if wing_ids and not getattr(request.user, "is_superuser", False):
                qs = qs.filter(classroom__wing_id__in=wing_ids)
            import re

            submitted_re = re.compile(r"\[SUBMITTED[^\]]*\]\s*", re.IGNORECASE)
            for r in qs:
                raw_note = (getattr(r, "note", "") or "").strip()
                # Strip any previous submission markers to avoid lingering in pending
                cleaned_note = submitted_re.sub("", raw_note).strip()
                tag = f"[{prefix} by {reviewer} @ {now}]"
                new_note = f"{tag} {comment} | {cleaned_note}".strip().strip("|")[:300]
                r.note = new_note
                if action == "reject":
                    r.locked = False  # allow teacher to edit and resubmit
                    # Keep source as teacher for rejected items
                    if getattr(r, "source", "teacher") != "supervisor":
                        r.source = "teacher"
                else:
                    r.locked = True  # close on approval
                    r.source = "supervisor"
                try:
                    r.save(update_fields=["note", "locked", "source", "updated_at"])
                    updated += 1
                except Exception:
                    continue
            return Response({"updated": updated, "action": action})
        except Exception as e:
            return Response({"detail": f"failed: {e}"}, status=500)

    @action(detail=False, methods=["post"], url_path="set-excused")
    def set_excused(self, request: Request) -> Response:
        """Mark selected attendance records as 'excused' (إذن خروج) by Wing Supervisor.
        Accepts optional evidence upload (image/PDF) to support converting absence to excused when proof is provided.
        Payload (JSON or multipart/form-data):
          - ids: number[] (required)
          - comment?: string
          - evidence: file (optional, jpg/png/jpeg/webp/pdf, <= 5MB)
          - evidence_note?: string (optional)
        Only records within the supervisor's wing(s) are affected.
        """
        payload = request.data or {}
        ids = payload.get("ids") or []
        # Support ids as JSON string (from multipart forms)
        if isinstance(ids, str):
            try:
                import json as _json
                ids = _json.loads(ids)
            except Exception:
                ids = []
        if not isinstance(ids, list) or not ids:
            return Response({"detail": "ids must be a non-empty list"}, status=400)
        comment = (payload.get("comment") or "").strip()
        evidence_note = (payload.get("evidence_note") or "").strip()
        staff, wing_ids = self._get_staff_and_wing_ids(request.user)
        if not wing_ids and not getattr(request.user, "is_superuser", False):
            return Response({"detail": "no wing scope"}, status=403)
        try:
            from django.utils import timezone
            from school.models import AttendanceRecord  # type: ignore
            from apps.attendance.models import AttendanceEvidence  # type: ignore

            now = timezone.now().strftime("%Y-%m-%d %H:%M")
            reviewer = getattr(staff, "full_name", None) or getattr(request.user, "username", "")
            updated = 0
            evidence_file = request.FILES.get("evidence")
            saved_evidence = []
            # Validate file if present
            if evidence_file is not None:
                allowed = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
                ctype = getattr(evidence_file, "content_type", "") or ""
                size = getattr(evidence_file, "size", 0) or 0
                if ctype not in allowed:
                    return Response({"detail": "unsupported evidence content-type"}, status=400)
                if size > 5 * 1024 * 1024:
                    return Response({"detail": "evidence file too large (max 5MB)"}, status=400)

            qs = AttendanceRecord.objects.filter(id__in=ids)
            if wing_ids and not getattr(request.user, "is_superuser", False):
                qs = qs.filter(classroom__wing_id__in=wing_ids)
            for r in qs:
                r.status = "excused"
                tag = f"[EXCUSED by {reviewer} @ {now}]"
                raw_note = (getattr(r, "note", "") or "").strip()
                new_note = f"{tag} {comment} | {raw_note}".strip().strip("|")[:300]
                r.note = new_note
                r.locked = True
                r.source = "supervisor"
                try:
                    r.save(update_fields=["status", "note", "locked", "source", "updated_at"])
                    updated += 1
                except Exception:
                    continue
                # Save evidence (duplicate file per record if multiple ids are provided)
                if evidence_file is not None:
                    try:
                        ev = AttendanceEvidence(
                            record=r,
                            file=evidence_file,
                            content_type=getattr(evidence_file, "content_type", "") or "",
                            original_name=getattr(evidence_file, "name", "") or "",
                            note=evidence_note[:300],
                            uploaded_by=getattr(request, "user", None),
                        )
                        ev.save()
                        saved_evidence.append({"record": r.id, "evidence_id": ev.id})
                    except Exception:
                        # Evidence failure should not rollback status change; continue
                        pass
            return Response({"updated": updated, "action": "set_excused", "evidence_saved": len(saved_evidence), "evidence": saved_evidence})
        except Exception as e:
            return Response({"detail": f"failed: {e}"}, status=500)

    @action(detail=False, methods=["get"], url_path="entered")
    def entered(self, request: Request) -> Response:
        """Return class-periods that already have supervisor-entered, locked attendance
        for the current wing(s) on the given date. Mirrors the shape of `missing`.
        """
        dt, err = _parse_date_or_400(request.query_params.get("date"))
        if err:
            return err
        try:
            from school.models import AttendanceRecord, Class, Term, TimetableEntry  # type: ignore

            try:
                from backend.common.day_utils import iso_to_school_dow
            except Exception:
                from common.day_utils import iso_to_school_dow  # type: ignore
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
        # Determine class-periods already recorded by supervisor (locked)
        rec = (
            AttendanceRecord.objects.filter(date=dt, classroom_id__in=class_ids, source="supervisor", locked=True)
            .values("classroom_id", "period_number")
            .distinct()
        )
        done = {(r["classroom_id"], r["period_number"]) for r in rec}

        items = []
        for e in tt:
            key = (e.classroom_id, e.period_number)
            if key not in done:
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

    @action(detail=False, methods=["get"], url_path="entered/export")
    def entered_export(self, request: Request) -> HttpResponse:
        """Export entered class-periods (supervisor-entered, locked) as CSV.
        Columns: class_id, class_name, period_number, subject_id, subject_name, teacher_id, teacher_name
        """
        # Build JSON by reusing existing logic
        data = self.entered(request).data  # type: ignore
        if isinstance(data, Response):
            return data  # type: ignore
        items = data.get("items", []) if isinstance(data, dict) else []
        import io

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "class_id",
                "class_name",
                "period_number",
                "subject_id",
                "subject_name",
                "teacher_id",
                "teacher_name",
            ]
        )
        for it in items:
            writer.writerow(
                [
                    it.get("class_id"),
                    (it.get("class_name") or ""),
                    it.get("period_number"),
                    it.get("subject_id"),
                    (it.get("subject_name") or ""),
                    it.get("teacher_id"),
                    (it.get("teacher_name") or ""),
                ]
            )
        csv_text = output.getvalue()
        content = ("\ufeff" + csv_text).encode("utf-8")
        resp = HttpResponse(content, content_type="text/csv; charset=utf-8")
        dt_str = data.get("date") if isinstance(data, dict) else timezone.localdate().isoformat()
        resp["Content-Disposition"] = f"attachment; filename=wing-entered-{dt_str}.csv"
        return resp

    @action(detail=False, methods=["get"], url_path="missing")
    def missing(self, request: Request) -> Response:
        dt, err = _parse_date_or_400(request.query_params.get("date"))
        if err:
            return err
        try:
            from school.models import AttendanceRecord, Class, Term, TimetableEntry  # type: ignore

            try:
                from backend.common.day_utils import iso_to_school_dow
            except Exception:
                from common.day_utils import iso_to_school_dow  # type: ignore
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
            AttendanceRecord.objects.filter(date=dt, classroom_id__in=class_ids, source="supervisor", locked=True)
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

    @action(detail=False, methods=["get"], url_path="missing/export")
    def missing_export(self, request: Request) -> HttpResponse:
        """Export missing class-periods (not yet supervisor-entered) as CSV.
        Columns: class_id, class_name, period_number, subject_id, subject_name, teacher_id, teacher_name
        """
        data = self.missing(request).data  # type: ignore
        if isinstance(data, Response):
            return data  # type: ignore
        items = data.get("items", []) if isinstance(data, dict) else []
        import io

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "class_id",
                "class_name",
                "period_number",
                "subject_id",
                "subject_name",
                "teacher_id",
                "teacher_name",
            ]
        )
        for it in items:
            writer.writerow(
                [
                    it.get("class_id"),
                    (it.get("class_name") or ""),
                    it.get("period_number"),
                    it.get("subject_id"),
                    (it.get("subject_name") or ""),
                    it.get("teacher_id"),
                    (it.get("teacher_name") or ""),
                ]
            )
        csv_text = output.getvalue()
        content = ("\ufeff" + csv_text).encode("utf-8")
        resp = HttpResponse(content, content_type="text/csv; charset=utf-8")
        dt_str = data.get("date") if isinstance(data, dict) else timezone.localdate().isoformat()
        resp["Content-Disposition"] = f"attachment; filename=wing-missing-{dt_str}.csv"
        return resp

    @action(detail=False, methods=["get"], url_path="timetable")
    def wing_timetable(self, request: Request) -> Response:
        """Return wing timetable. Supports ?wing_id, ?date=YYYY-MM-DD, and ?mode=daily|weekly (default daily).
        Data is scoped to the current user's supervised wings unless superuser.
        Includes a lightweight meta object to explain empty states (diagnostics only).
        """
        try:
            from school.models import Class, Term, TimetableEntry  # type: ignore

            try:
                from backend.common.day_utils import iso_to_school_dow
            except Exception:
                from common.day_utils import iso_to_school_dow  # type: ignore
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
                st_et = times_per_day.get(int(e.day_of_week), {}).get(int(e.period_number)) or period_times.get(
                    int(e.period_number)
                )
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
            meta["period_times_by_day"] = {
                str(d): {int(k): v for k, v in (times_per_day.get(d) or {}).items()} for d in range(1, 8)
            }
            meta["period_times"] = {int(k): v for k, v in period_times.items()} if period_times else {}
            return Response(
                {
                    "mode": "weekly",
                    "term_id": getattr(term, "id", None),
                    "wing_id": wing_id,
                    "days": {str(k): v for k, v in days.items()},
                    "meta": meta,
                }
            )

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
        meta["period_times_by_day"] = {
            str(d): {int(k): v for k, v in (period_times_by_day.get(d) or {}).items()} for d in range(1, 8)
        }
        meta["period_times"] = {int(k): v for k, v in period_times.items()} if period_times else {}
        return Response(
            {
                "mode": "daily",
                "date": dt.isoformat(),
                "dow": dow,
                "term_id": getattr(term, "id", None),
                "wing_id": wing_id,
                "items": items,
                "meta": meta,
            }
        )


class ExitEventViewSet(viewsets.ModelViewSet):
    from rest_framework.permissions import IsAuthenticated

    permission_classes = [IsAuthenticated]
    serializer_class = ExitEventSerializer
    queryset = None  # set in get_queryset to apply permissions

    def _is_wing_or_super(self, user) -> bool:
        try:
            roles = set(user.groups.values_list("name", flat=True))  # type: ignore
        except Exception:
            roles = set()
        return bool(getattr(user, "is_superuser", False) or ("wing_supervisor" in roles))

    def get_queryset(self):
        from school.models import ExitEvent  # type: ignore

        qs = ExitEvent.objects.all()
        # Optional filtering
        student_id = self.request.query_params.get("student_id")
        class_id = self.request.query_params.get("class_id")
        date = self.request.query_params.get("date")
        review_status = self.request.query_params.get("review_status")
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
        if review_status:
            qs = qs.filter(review_status=review_status)
        return qs

    def create(self, request: Request, *args, **kwargs):
        from django.utils import timezone
        from school.models import ExitEvent  # type: ignore

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
        logger.info(f"ExitEvent validated_data types: {[(k, type(v).__name__) for k, v in ser.validated_data.items()]}")

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
        open_exists = ExitEvent.objects.filter(student=student, date=req_date, returned_at__isnull=True).exists()
        if open_exists:
            return Response(
                {
                    "detail": "يوجد جلسة خروج مفتوحة لهذا الطالب في نفس اليوم",
                    "date": req_date,
                },
                status=400,
            )

        # Save the exit event and mark as submitted for supervisor review by default
        obj = ser.save(started_by=getattr(request, "user", None))
        try:
            if obj.review_status is None:
                obj.review_status = "submitted"
                obj.save(update_fields=["review_status"])
        except Exception:
            pass
        return Response({"id": obj.id, "started_at": timezone.localtime(obj.started_at).isoformat()}, status=201)

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
                "returned_at": (timezone.localtime(obj.returned_at).isoformat() if obj.returned_at else None),
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

    @action(detail=False, methods=["get"], url_path="pending")
    def pending(self, request: Request):
        # List exit events awaiting supervisor approval
        from school.models import ExitEvent  # type: ignore

        qs = ExitEvent.objects.filter(review_status="submitted")
        date = request.query_params.get("date")
        class_id = request.query_params.get("class_id")
        if date:
            qs = qs.filter(date=date)
        if class_id:
            try:
                qs = qs.filter(classroom_id=int(class_id))
            except Exception:
                pass
        # TODO: Optionally restrict by supervisor wing coverage in future
        ser = ExitEventSerializer(qs, many=True)
        return Response({"count": qs.count(), "items": ser.data})

    @action(detail=False, methods=["post"], url_path="decide")
    def decide(self, request: Request):
        from django.utils import timezone
        from school.models import ExitEvent  # type: ignore

        if not self._is_wing_or_super(request.user):
            return Response({"detail": "forbidden"}, status=403)
        payload = request.data or {}
        action = (payload.get("action") or "").strip().lower()
        ids = payload.get("ids") or []
        comment = (payload.get("comment") or payload.get("review_comment") or "").strip()
        if action not in ("approve", "reject"):
            return Response({"detail": "invalid action"}, status=400)
        if not isinstance(ids, list) or not ids:
            return Response({"detail": "ids is required (list)"}, status=400)
        updated = 0
        for _id in ids:
            try:
                obj = ExitEvent.objects.get(pk=int(_id))
            except Exception:
                continue
            # Idempotent: skip if already decided
            if obj.review_status in ("approved", "rejected"):
                continue
            obj.review_status = "approved" if action == "approve" else "rejected"
            obj.reviewer = request.user
            obj.reviewed_at = timezone.now()
            if comment:
                # Append to any existing comment with separator
                obj.review_comment = obj.review_comment or ""
                obj.review_comment = (obj.review_comment + ("\n" if obj.review_comment else "") + comment)[:300]
            obj.save(update_fields=["review_status", "reviewer", "reviewed_at", "review_comment"])
            updated += 1
        return Response({"updated": updated, "action": action})