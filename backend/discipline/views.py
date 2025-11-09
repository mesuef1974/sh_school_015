from django.utils import timezone
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from typing import Dict, List
from .models import Violation, Incident, BehaviorLevel
from .serializers import ViolationSerializer, IncidentSerializer, BehaviorLevelSerializer


class IsDisciplineRole(permissions.BasePermission):
    message = "User lacks discipline access permission"

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        # Allow superusers/staff by default; otherwise require custom perm
        if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
            return True
        return user.has_perm("discipline.access")


class ViolationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Violation.objects.select_related("level").all()
    serializer_class = ViolationSerializer
    permission_classes = [IsDisciplineRole]
    filter_backends = [filters.SearchFilter]
    search_fields = ["category", "description", "code"]


class BehaviorLevelViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = BehaviorLevel.objects.all()
    serializer_class = BehaviorLevelSerializer
    permission_classes = [IsDisciplineRole]
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "description"]


class IncidentViewSet(viewsets.ModelViewSet):
    serializer_class = IncidentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["narrative", "location", "violation__category", "violation__code"]

    def get_queryset(self):
        qs = Incident.objects.select_related("violation", "student", "reporter").all()
        user = getattr(self.request, "user", None)
        if not user:
            return qs.none()
        # Non-privileged users (e.g., teachers) only see their own incidents
        if not (
            getattr(user, "is_staff", False)
            or getattr(user, "is_superuser", False)
            or user.has_perm("discipline.access")
        ):
            qs = qs.filter(reporter_id=user.id)
        # Optional status filter to support UI param
        st = (self.request.query_params.get("status") or "").strip()
        if st in {"open", "under_review", "closed"}:
            qs = qs.filter(status=st)
        return qs

    def _has(self, user, codename: str) -> bool:
        return (
            getattr(user, "is_superuser", False)
            or getattr(user, "is_staff", False)
            or user.has_perm(f"discipline.{codename}")
        )

    def _ensure_owner_or_role(self, request, incident: Incident) -> None:
        # Teachers (reporters) can submit only their own incidents unless staff/superuser
        if request.user.is_superuser or request.user.is_staff:
            return
        if incident.reporter_id != request.user.id:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("ليست من حالاتك")

    def create(self, request, *args, **kwargs):
        """Restrict creation for teachers to their own students in their classes (best‑effort).
        Staff/superusers are exempt. For incidents with severity <= 2, require that the reporter
        teaches the student on the incident date (based on TeachingAssignment and class roster).
        This is a soft guard to prevent accidental misreporting; if resolution fails, we still allow
        staff to proceed.
        """
        user = request.user
        # Permission gate
        if not self._has(user, "incident_create"):
            return Response({"detail": "لا تملك صلاحية إنشاء"}, status=status.HTTP_403_FORBIDDEN)
        # Allow staff/superuser to create without scope restriction
        if not (getattr(user, "is_staff", False) or getattr(user, "is_superuser", False)):
            try:
                # Parse payload minimally to validate scope
                student_id = int(request.data.get("student"))
                violation_id = int(request.data.get("violation"))
                occurred_at_raw = request.data.get("occurred_at")
            except Exception:
                return Response({"detail": "بيانات غير صالحة"}, status=status.HTTP_400_BAD_REQUEST)
            # Look up violation severity to decide strictness
            try:
                viol = Violation.objects.only("severity").get(id=violation_id)
                severity = int(getattr(viol, "severity", 1) or 1)
            except Exception:
                severity = 1
            # Resolve incident date (localize if needed)
            try:
                from django.utils.dateparse import parse_datetime

                dt = parse_datetime(occurred_at_raw)
                if dt is None:
                    raise ValueError
            except Exception:
                return Response({"detail": "وقت الحادثة غير صالح"}, status=status.HTTP_400_BAD_REQUEST)
            # For low severity incidents (<=2), ensure reporter has the student in any of their classes for the date
            if severity <= 2:
                try:
                    from school.models import Staff, TeachingAssignment  # type: ignore
                    from apps.attendance import selectors  # type: ignore
                    staff = Staff.objects.filter(user_id=user.id).first()
                    if not staff:
                        return Response({"detail": "لا يوجد ربط وظيفي للمعلم"}, status=status.HTTP_403_FORBIDDEN)
                    # Distinct classroom ids the teacher teaches
                    classroom_ids = (
                        TeachingAssignment.objects.filter(teacher_id=staff.id)
                        .values_list("classroom_id", flat=True)
                        .distinct()
                    )
                    # Check if student is in roster of any of those classes for that date
                    allowed = False
                    for cid in classroom_ids:
                        try:
                            qs = selectors.get_students_for_class_on_date(int(cid), dt.date())
                            if qs.filter(id=student_id).exists():
                                allowed = True
                                break
                        except Exception:
                            continue
                    if not allowed:
                        return Response({"detail": "لا يحق لك تسجيل واقعة لهذا الطالب خارج صفوفك."}, status=status.HTTP_403_FORBIDDEN)
                except Exception:
                    # If validation fails unexpectedly, block non-privileged users; allow staff/superusers or users with discipline.access
                    if not (
                        getattr(user, "is_staff", False)
                        or getattr(user, "is_superuser", False)
                        or user.has_perm("discipline.access")
                    ):
                        return Response({"detail": "تعذّر التحقق من نطاقك. الرجاء التواصل مع المشرف أو التأكد من ربط الحصص."}, status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)

    @action(detail=True, methods=["post"]) 
    def submit(self, request, pk=None):
        inc = self.get_object()
        if inc.status != "open":
            return Response({"detail": "لا يمكن الإرسال إلا من حالة open."}, status=status.HTTP_400_BAD_REQUEST)
        # Permission + ownership
        if not self._has(request.user, "incident_submit"):
            return Response({"detail": "صلاحية غير كافية للإرسال."}, status=status.HTTP_403_FORBIDDEN)
        if not (request.user.is_staff or request.user.is_superuser):
            self._ensure_owner_or_role(request, inc)
        # Compute repeat within 30 يوم
        from django.utils.timezone import now
        from datetime import timedelta
        from django.conf import settings as dj_settings
        window_days = int(getattr(dj_settings, "DISCIPLINE_REPEAT_WINDOW_D", 30))
        threshold = int(getattr(dj_settings, "DISCIPLINE_REPEAT_THRESHOLD", 2))
        recent = Incident.objects.filter(
            student_id=inc.student_id,
            violation_id=inc.violation_id,
            occurred_at__gte=now() - timedelta(days=window_days),
        ).exclude(id=inc.id).count()
        escalated = recent >= threshold  # سياسة قابلة للتهيئة
        inc.escalated_due_to_repeat = escalated
        # escalate committee if severity >=3 or escalated
        if inc.severity >= 3 or escalated:
            inc.committee_required = True
        # Auto bump severity by 1 (max 4) when escalated, if enabled via settings
        from django.conf import settings as dj_settings
        if escalated and getattr(dj_settings, "DISCIPLINE_AUTO_ESCALATE_SEVERITY", True):
            try:
                inc.severity = min(4, int(getattr(inc, "severity", 1) or 1) + 1)
            except Exception:
                inc.severity = min(4, 1 + 1)
        inc.submitted_at = timezone.now()
        inc.status = "under_review"
        inc.save(update_fields=[
            "escalated_due_to_repeat",
            "committee_required",
            "submitted_at",
            "status",
            "severity",
            "updated_at",
        ])
        return Response(self.get_serializer(inc).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"]) 
    def review(self, request, pk=None):
        inc = self.get_object()
        # Require granular permission per RBAC
        if not self._has(request.user, "incident_review"):
            return Response({"detail": "صلاحية غير كافية للمراجعة."}, status=status.HTTP_403_FORBIDDEN)
        if inc.status != "under_review":
            return Response({"detail": "لا يمكن المراجعة إلا للحالات under_review."}, status=status.HTTP_400_BAD_REQUEST)
        inc.reviewed_by = request.user
        inc.reviewed_at = timezone.now()
        inc.save(update_fields=["reviewed_by", "reviewed_at", "updated_at"])
        return Response(self.get_serializer(inc).data)

    @action(detail=True, methods=["post"], url_path="add-action")
    def add_action(self, request, pk=None):
        inc = self.get_object()
        if inc.status not in ("under_review", "open"):
            return Response({"detail": "إضافة إجراء متاحة خلال open/under_review فقط."}, status=status.HTTP_400_BAD_REQUEST)
        if not self._has(request.user, "incident_review"):
            return Response({"detail": "صلاحية غير كافية."}, status=status.HTTP_403_FORBIDDEN)
        name = str(request.data.get("name", "")).strip()
        notes = str(request.data.get("notes", "")).strip()
        if not name:
            return Response({"detail": "name مطلوب"}, status=status.HTTP_400_BAD_REQUEST)
        arr = list(inc.actions_applied or [])
        arr.append({"name": name, "notes": notes, "at": timezone.now().isoformat()})
        inc.actions_applied = arr
        inc.save(update_fields=["actions_applied", "updated_at"])
        return Response(self.get_serializer(inc).data)

    @action(detail=True, methods=["post"], url_path="add-sanction")
    def add_sanction(self, request, pk=None):
        inc = self.get_object()
        if inc.status not in ("under_review", "open"):
            return Response({"detail": "إضافة عقوبة متاحة خلال open/under_review فقط."}, status=status.HTTP_400_BAD_REQUEST)
        if not self._has(request.user, "incident_review"):
            return Response({"detail": "صلاحية غير كافية."}, status=status.HTTP_403_FORBIDDEN)
        name = str(request.data.get("name", "")).strip()
        notes = str(request.data.get("notes", "")).strip()
        if not name:
            return Response({"detail": "name مطلوب"}, status=status.HTTP_400_BAD_REQUEST)
        arr = list(inc.sanctions_applied or [])
        arr.append({"name": name, "notes": notes, "at": timezone.now().isoformat()})
        inc.sanctions_applied = arr
        inc.save(update_fields=["sanctions_applied", "updated_at"])
        return Response(self.get_serializer(inc).data)

    @action(detail=True, methods=["post"]) 
    def close(self, request, pk=None):
        inc = self.get_object()
        if inc.status == "closed":
            return Response({"detail": "هذه الواقعة مغلقة بالفعل."}, status=status.HTTP_400_BAD_REQUEST)
        if not self._has(request.user, "incident_close"):
            return Response({"detail": "صلاحية غير كافية للإغلاق."}, status=status.HTTP_403_FORBIDDEN)
        # Prevent closing severe incidents without any action/sanction
        if inc.severity >= 2 and not ((inc.actions_applied and len(inc.actions_applied) > 0) or (inc.sanctions_applied and len(inc.sanctions_applied) > 0)):
            return Response({"detail": "لا يمكن إغلاق واقعة ذات شدة ≥ 2 دون إجراء/عقوبة."}, status=status.HTTP_400_BAD_REQUEST)
        inc.closed_by = request.user
        inc.closed_at = timezone.now()
        inc.status = "closed"
        inc.save(update_fields=["closed_by", "closed_at", "status", "updated_at"])
        return Response(self.get_serializer(inc).data)

    @action(detail=True, methods=["post"]) 
    def escalate(self, request, pk=None):
        inc = self.get_object()
        if not self._has(request.user, "incident_escalate"):
            return Response({"detail": "صلاحية غير كافية للتصعيد."}, status=status.HTTP_403_FORBIDDEN)
        # Escalate severity by 1 up to max 4 and mark committee if >=3
        new_sev = min(4, int(inc.severity or 1) + 1)
        inc.severity = new_sev
        if new_sev >= 3:
            inc.committee_required = True
        inc.escalated_due_to_repeat = True
        inc.save(update_fields=["severity", "committee_required", "escalated_due_to_repeat", "updated_at"])
        return Response(self.get_serializer(inc).data)

    @action(detail=True, methods=["post"], url_path="notify-guardian")
    def notify_guardian(self, request, pk=None):
        inc = self.get_object()
        if not self._has(request.user, "incident_notify_guardian"):
            return Response({"detail": "صلاحية غير كافية للإشعار."}, status=status.HTTP_403_FORBIDDEN)
        channel = (request.data.get("channel") or "internal").strip()
        note = str(request.data.get("note") or "").strip()
        arr = list(inc.actions_applied or [])
        arr.append({
            "name": "notify_guardian",
            "channel": channel,
            "note": note,
            "at": timezone.now().isoformat(),
        })
        inc.actions_applied = arr
        inc.save(update_fields=["actions_applied", "updated_at"])
        return Response({"detail": "تم الإشعار (placeholder)", "incident": self.get_serializer(inc).data}, status=status.HTTP_202_ACCEPTED)

    @action(detail=False, methods=["get"])  # /incidents/kanban/
    def kanban(self, request):
        """Return grouped incidents by status with counts and limited items per column.
        Teachers will only see their own incidents; staff/superusers or users with discipline.access see all.
        Query params: limit (default 20, max 100), status (optional to include only one), search (inherited).
        """
        if not (request.user.is_staff or request.user.is_superuser or request.user.has_perm("discipline.access")):
            # regular users still allowed but scoped via get_queryset()
            pass
        try:
            limit = int(request.query_params.get("limit", 20))
        except Exception:
            limit = 20
        limit = max(1, min(100, limit))
        # Optional single status filter
        only = (request.query_params.get("status") or "").strip()
        statuses = ["open", "under_review", "closed"]
        if only in statuses:
            statuses = [only]
        data = {"columns": {}, "counts": {}}
        qs = self.filter_queryset(self.get_queryset())
        from collections import defaultdict

        buckets: Dict[str, List[Incident]] = defaultdict(list)
        for inc in qs.iterator():
            if inc.status in statuses:
                buckets[inc.status].append(inc)
        for st in statuses:
            items = buckets.get(st, [])
            data["counts"][st] = len(items)
            # Sort by occurred_at desc within each column
            items_sorted = sorted(items, key=lambda x: x.occurred_at, reverse=True)[:limit]
            data["columns"][st] = IncidentSerializer(items_sorted, many=True, context=self.get_serializer_context()).data
        return Response(data)

    @action(detail=False, methods=["get"])  # /incidents/summary/?days=7|30
    def summary(self, request):
        """Return minimal metrics for supervisors: totals by status and severity, top violations, overdue counts.
        days filter defaults to 7; accepts 7 or 30.
        """
        from datetime import timedelta
        from django.utils.timezone import now
        try:
            days = int(request.query_params.get("days", 7))
        except Exception:
            days = 7
        days = 30 if days >= 30 else 7
        since = now() - timedelta(days=days)

        qs = self.get_queryset().filter(occurred_at__gte=since)
        # Build aggregates
        out = {
            "since": since.isoformat(),
            "totals": {"all": qs.count()},
            "by_status": {"open": 0, "under_review": 0, "closed": 0},
            "by_severity": {"1": 0, "2": 0, "3": 0, "4": 0},
            "top_violations": [],
            "overdue": {"review": 0, "notify": 0},
        }
        # Counts by status and severity, and overdue SLA
        from collections import Counter

        status_counter = Counter()
        sev_counter = Counter()
        viol_counter = Counter()
        from django.conf import settings as dj_settings
        review_h = int(getattr(dj_settings, "DISCIPLINE_REVIEW_SLA_H", 24))
        notify_h = int(getattr(dj_settings, "DISCIPLINE_NOTIFY_SLA_H", 48))
        for inc in qs.iterator():
            status_counter[inc.status] += 1
            sev = int(getattr(inc, "severity", 1) or 1)
            sev_counter[str(min(max(sev, 1), 4))] += 1
            try:
                viol_counter[getattr(inc.violation, "code", "")] += 1
            except Exception:
                pass
            # Overdue checks for items under review
            if inc.status == "under_review" and inc.submitted_at:
                review_due = inc.submitted_at + timedelta(hours=review_h)
                notify_due = inc.submitted_at + timedelta(hours=notify_h)
                now_v = now()
                if now_v > review_due:
                    out["overdue"]["review"] += 1
                if now_v > notify_due:
                    out["overdue"]["notify"] += 1
        out["by_status"].update({k: status_counter.get(k, 0) for k in out["by_status"].keys()})
        out["by_severity"].update({str(k): sev_counter.get(str(k), 0) for k in range(1, 5)})
        # Top 5 violations with simple enrichment
        top = viol_counter.most_common(5)
        top_payload = []
        if top:
            viols = {v.code: v for v in Violation.objects.filter(code__in=[c for c, _ in top]).only("code", "category")}
            for code, cnt in top:
                v = viols.get(code)
                top_payload.append({
                    "code": code,
                    "category": getattr(v, "category", None),
                    "count": cnt,
                })
        out["top_violations"] = top_payload
        return Response(out)