from datetime import date as _date

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.request import Request

from .serializers import StudentBriefSerializer
from . import selectors
from .services.attendance import bulk_save_attendance


def _parse_date_or_400(dt_str: str | None):
    """Parse ISO date (YYYY-MM-DD) or return (None, Response(400)). If empty, return today."""
    if not dt_str:
        return _date.today(), None
    try:
        return _date.fromisoformat(dt_str), None
    except Exception:
        return None, Response({"detail": "date must be YYYY-MM-DD"}, status=400)


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
        except Exception as e:
            return Response({"detail": f"Invalid payload: {e}"}, status=400)
        # Enforce access for saving
        if not self._user_has_access_to_class(request.user, class_id):
            return Response({"detail": "not allowed for this class"}, status=403)
        saved = bulk_save_attendance(
            class_id=class_id,
            dt=dt,
            records=records,
            actor_user_id=request.user.id if request.user.is_authenticated else None,
        )
        return Response({"saved": len(saved)}, status=status.HTTP_200_OK)
