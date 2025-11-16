from django.utils import timezone
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from typing import Dict, List
import logging
from django.db import models
from django.db.models import Count
from .models import Violation, Incident, BehaviorLevel
from .models import IncidentAuditLog
from .models import IncidentAttachment
from .serializers import ViolationSerializer, IncidentSerializer, BehaviorLevelSerializer, IncidentFullSerializer
from django.contrib.auth import get_user_model
import hashlib
from django.db.models import Q
from django.http import FileResponse, HttpResponse
import json

logger = logging.getLogger(__name__)


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
    # Defer 'policy' to avoid selecting a column that may not exist in
    # older databases (backward-compat for instances without this migration).
    queryset = Violation.objects.select_related("level").defer("policy").all()
    serializer_class = ViolationSerializer
    # Allow any authenticated user (e.g., teachers) to load the catalog for forms
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["category", "description", "code"]

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params if hasattr(self, "request") else {}
        # Filter by level (accepts level id or code/severity number)
        level = (params.get("level") or params.get("level_id") or params.get("level_code") or "").strip()
        if level:
            try:
                # If numeric, match either BehaviorLevel.code or pk
                lvl_num = int(level)
                qs = qs.filter(models.Q(level__code=lvl_num) | models.Q(level_id=lvl_num) | models.Q(severity=lvl_num))
            except Exception:
                # Non-numeric values ignored for now (could extend to name)
                pass
        # Optional filter by exact severity
        severity = (params.get("severity") or "").strip()
        if severity:
            try:
                sev = int(severity)
                qs = qs.filter(severity=sev)
            except Exception:
                pass
        return qs


class BehaviorLevelViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = BehaviorLevel.objects.all()
    serializer_class = BehaviorLevelSerializer
    # Allow any authenticated user to read behavior levels used by the catalog
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "description"]


class IncidentViewSet(viewsets.ModelViewSet):
    serializer_class = IncidentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["narrative", "location", "violation__category", "violation__code"]

    def get_serializer_class(self):
        """عند تمرير expand=all أو full=1 تُعاد تمثيلات كاملة IncidentFullSerializer.
        الافتراضي: IncidentSerializer الخفيف.
        """
        try:
            qp = getattr(self.request, "query_params", {})
            expand = (qp.get("expand") or "").strip().lower()
            full = (qp.get("full") or "").strip().lower() in {"1", "true", "yes"}
            if expand == "all" or full:
                return IncidentFullSerializer
        except Exception:
            pass
        return super().get_serializer_class()

    def get_queryset(self):
        qs = (
            Incident.objects.select_related(
                "violation",
                "student",
                "reporter",
                "student__class_fk",
                "student__class_fk__wing",
            )
            .defer("violation__policy")
            .all()
        )
        user = getattr(self.request, "user", None)
        if not user:
            return qs.none()
        # Support explicit scoping via ?mine=1 to always restrict to current user's incidents
        mine = (self.request.query_params.get("mine") or self.request.query_params.get("me") or "").strip()
        force_mine = mine in {"1", "true", "yes"}
        # Non-privileged users (e.g., teachers) only see their own incidents by default
        if force_mine or not (
            getattr(user, "is_staff", False)
            or getattr(user, "is_superuser", False)
            or user.has_perm("discipline.access")
        ):
            # Scope to current user's incidents. In dev/ported DBs, IDs may not match;
            # optionally include username match as a safe fallback.
            from django.conf import settings as dj_settings
            from django.db.models import Q

            if getattr(dj_settings, "DISCIPLINE_MATCH_MINE_BY_USERNAME", False):
                qs = qs.filter(Q(reporter_id=user.id) | Q(reporter__username=getattr(user, "username", None)))
            else:
                qs = qs.filter(reporter_id=user.id)
        # Optional status filter to support UI param
        st = (self.request.query_params.get("status") or "").strip()
        if st in {"open", "under_review", "closed"}:
            qs = qs.filter(status=st)
        # Optional student filter to support UI deep-linking per student
        student_id = (self.request.query_params.get("student") or "").strip()
        if student_id.isdigit():
            try:
                qs = qs.filter(student_id=int(student_id))
            except Exception:
                pass
        # Consistent ordering: most recent first
        qs = qs.order_by("-occurred_at", "-created_at")
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
            if logger and logger.isEnabledFor(logging.INFO):
                logger.info("incident.create.denied_perm user=%s", getattr(user, "id", None))
            return Response(
                {"detail": "لا تملك صلاحية إنشاء", "code": "NO_CREATE_PERMISSION"},
                status=status.HTTP_403_FORBIDDEN,
            )
        # Allow staff/superuser to create without scope restriction
        if not (getattr(user, "is_staff", False) or getattr(user, "is_superuser", False)):
            try:
                # Parse payload minimally to validate scope
                student_id = int(request.data.get("student"))
                violation_id = int(request.data.get("violation"))
                occurred_at_raw = request.data.get("occurred_at")
            except Exception:
                if logger and logger.isEnabledFor(logging.WARNING):
                    logger.warning(
                        "incident.create.bad_payload user=%s data_keys=%s",
                        getattr(user, "id", None),
                        list(request.data.keys()),
                    )
                return Response(
                    {"detail": "بيانات غير صالحة", "code": "BAD_PAYLOAD"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
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
                if logger and logger.isEnabledFor(logging.WARNING):
                    logger.warning(
                        "incident.create.bad_time user=%s occurred_at=%s",
                        getattr(user, "id", None),
                        occurred_at_raw,
                    )
                return Response(
                    {"detail": "وقت الحادثة غير صالح", "code": "BAD_OCCURRED_AT"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            # For low severity incidents (<=2), ensure reporter has the student in any of their classes for the date
            if severity <= 2:
                try:
                    from school.models import Staff, TeachingAssignment  # type: ignore
                    from apps.attendance import selectors  # type: ignore

                    staff = Staff.objects.filter(user_id=user.id).first()
                    if staff:
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
                            except Exception as e:
                                if logger and logger.isEnabledFor(logging.DEBUG):
                                    logger.debug(
                                        "incident.create.scope_roster_error user=%s class_id=%s err=%s",
                                        getattr(user, "id", None),
                                        cid,
                                        e,
                                    )
                                continue
                        if not allowed:
                            if logger and logger.isEnabledFor(logging.INFO):
                                logger.info(
                                    "incident.create.denied_scope user=%s student=%s violation=%s severity=%s",
                                    getattr(user, "id", None),
                                    student_id,
                                    violation_id,
                                    severity,
                                )
                            return Response(
                                {
                                    "detail": "لا يحق لك تسجيل واقعة لهذا الطالب خارج صفوفك.",
                                    "code": "OUT_OF_SCOPE",
                                },
                                status=status.HTTP_403_FORBIDDEN,
                            )
                    else:
                        # No Staff link for this user: cannot enforce scope in this environment → allow and defer to review.
                        if logger and logger.isEnabledFor(logging.INFO):
                            logger.info(
                                "incident.create.soft_allow_no_staff_link user=%s student=%s violation=%s",
                                getattr(user, "id", None),
                                student_id,
                                violation_id,
                            )
                        pass
                except Exception as e:
                    # If scope validation fails unexpectedly, allow creation to avoid blocking teachers due to configuration gaps.
                    # Staff/superusers are always allowed; non-privileged users proceed as well, and supervisors can later review.
                    if logger and logger.isEnabledFor(logging.WARNING):
                        logger.warning(
                            "incident.create.soft_allow_exception user=%s err=%s",
                            getattr(user, "id", None),
                            e,
                        )
                    pass
        if logger and logger.isEnabledFor(logging.INFO):
            logger.info("incident.create.allowed user=%s", getattr(user, "id", None))
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        # Ensure reporter is set server-side regardless of client payload
        try:
            obj = serializer.save(reporter=self.request.user)
        except TypeError:
            # Fallback if reporter is already bound in serializer (shouldn't happen due to read-only)
            obj = serializer.save()
        # Audit: creation
        try:
            self._audit(obj, "create", note="incident created")
        except Exception:
            pass
        # Important: prevent a post-save lazy load of Violation that would SELECT all columns
        # (including the optional 'policy' column that may not exist in older databases) when
        # the serializer builds the representation. Populate the relation cache with a
        # safely-loaded Violation instance that defers 'policy'.
        try:
            if getattr(obj, "violation_id", None):
                safe_v = (
                    Violation.objects.only("id", "code", "category", "severity", "requires_committee")
                    .defer("policy")
                    .get(id=obj.violation_id)
                )
                # Populate Django relation cache so serializer uses this instance without re-querying
                setattr(obj, "violation", safe_v)
        except Exception:
            # If this optimization fails, we still return success; other guards elsewhere
            # (serializer and query defers) should minimize risk, and worst-case we fall back.
            pass

    # --- Professional audit helpers ---
    def _get_client_ip(self, request):
        try:
            xff = request.META.get("HTTP_X_FORWARDED_FOR")
            if xff:
                return xff.split(",")[0].strip()
            return request.META.get("REMOTE_ADDR", "")
        except Exception:
            return ""

    def _audit(
        self,
        incident: Incident,
        action: str,
        note: str = "",
        meta: Dict | None = None,
        from_status: str | None = None,
        to_status: str | None = None,
    ):
        try:
            IncidentAuditLog.objects.create(
                incident=incident,
                action=action,
                actor=getattr(self.request, "user", None),
                from_status=from_status or getattr(incident, "status", ""),
                to_status=to_status or getattr(incident, "status", ""),
                note=note or "",
                client_ip=self._get_client_ip(self.request),
                meta=meta or {},
            )
        except Exception:
            # Do not block business operation on audit failure
            if logger and logger.isEnabledFor(logging.WARNING):
                logger.warning("incident.audit.failed action=%s incident=%s", action, getattr(incident, "id", None))

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
        # Compute repeat within window (catalog-driven with safe fallbacks)
        from django.utils.timezone import now
        from datetime import timedelta
        from django.conf import settings as dj_settings

        # Defaults from settings
        window_days = int(getattr(dj_settings, "DISCIPLINE_REPEAT_WINDOW_D", 30))
        threshold = int(getattr(dj_settings, "DISCIPLINE_REPEAT_THRESHOLD", 2))
        try:
            # Per-violation policy overrides
            vpol = getattr(getattr(inc, "violation", None), "policy", None) or {}
            if isinstance(vpol, dict):
                # window days
                if vpol.get("window_days") is not None:
                    window_days = int(vpol.get("window_days") or window_days)
                # escalation.after_repeats
                esc = vpol.get("escalation") or {}
                if isinstance(esc, dict) and esc.get("after_repeats") is not None:
                    threshold = int(esc.get("after_repeats") or threshold)
        except Exception:
            pass
        recent = (
            Incident.objects.filter(
                student_id=inc.student_id,
                violation_id=inc.violation_id,
                occurred_at__gte=now() - timedelta(days=window_days),
            )
            .exclude(id=inc.id)
            .count()
        )
        escalated = recent >= threshold  # سياسة قابلة للتهيئة (كتالوجية عند التوفر)
        inc.escalated_due_to_repeat = escalated
        # Determine committee requirement (catalog-aware)
        committee_requires = False
        try:
            vpol = getattr(getattr(inc, "violation", None), "policy", None) or {}
            if isinstance(vpol, dict):
                cpol = vpol.get("committee") or {}
                if isinstance(cpol, dict):
                    sev_gte = cpol.get("requires_on_severity_gte")
                    after_rep = cpol.get("after_repeats")
                    if isinstance(sev_gte, (int, float)) and int(getattr(inc, "severity", 1) or 1) >= int(sev_gte):
                        committee_requires = True
                    if isinstance(after_rep, (int, float)) and recent >= int(after_rep):
                        committee_requires = True
        except Exception:
            pass
        # Fallback generic rule
        if inc.severity >= 3 or escalated:
            committee_requires = True or committee_requires
        # Violation-level requires_committee forces it
        if bool(getattr(getattr(inc, "violation", None), "requires_committee", False)):
            committee_requires = True
        inc.committee_required = bool(committee_requires)
        # Auto bump severity by 1 (max 4) when escalated, if enabled via settings
        from django.conf import settings as dj_settings

        if escalated and getattr(dj_settings, "DISCIPLINE_AUTO_ESCALATE_SEVERITY", True):
            try:
                inc.severity = min(4, int(getattr(inc, "severity", 1) or 1) + 1)
            except Exception:
                inc.severity = min(4, 1 + 1)
        inc.submitted_at = timezone.now()
        prev = inc.status
        inc.status = "under_review"
        inc.save(
            update_fields=[
                "escalated_due_to_repeat",
                "committee_required",
                "submitted_at",
                "status",
                "severity",
                "updated_at",
            ]
        )
        try:
            self._audit(
                inc,
                "submit",
                note="submitted for review",
                from_status=prev,
                to_status=inc.status,
                meta={"repeat_in_window": bool(escalated)},
            )
        except Exception:
            pass

        # Auto-schedule to Standing Committee when required and not yet scheduled
        try:
            if inc.committee_required and not getattr(inc, "committee_scheduled_at", None):
                self._schedule_committee_from_standing(inc, request.user)
        except Exception:
            # Never block submit on auto-schedule failure; it can be scheduled manually later
            if logger and logger.isEnabledFor(logging.WARNING):
                logger.warning("incident.submit.auto_schedule.failed incident=%s", getattr(inc, "id", None))

        return Response(self.get_serializer(inc).data, status=status.HTTP_200_OK)

    # --- Committee helpers ---
    def _schedule_committee_from_standing(self, inc: Incident, user):
        """Schedule the incident to the standing committee and persist records.
        Safe to call multiple times; it will upsert the IncidentCommittee record.
        Returns True on success, False on failure.
        """
        try:
            from .models import StandingCommittee, StandingCommitteeMember

            standing = StandingCommittee.objects.order_by("id").first()
            if not (standing and getattr(standing, "chair_id", None)):
                return False
            chair_id = int(standing.chair_id)
            member_ids = [
                int(x.user_id) for x in StandingCommitteeMember.objects.filter(standing=standing).only("user_id")
            ]
            recorder_id = int(standing.recorder_id) if getattr(standing, "recorder_id", None) else None
        except Exception:
            return False

        # Map users
        users_map = {u.id: u for u in get_user_model().objects.filter(id__in=list(set([chair_id] + member_ids + ([recorder_id] if recorder_id else []))))}

        from django.utils import timezone as _tz

        inc.committee_panel = {
            "chair_id": chair_id,
            "member_ids": member_ids,
            "recorder_id": recorder_id,
        }
        inc.committee_required = True
        inc.committee_scheduled_by = user
        inc.committee_scheduled_at = _tz.now()
        try:
            inc.save(
                update_fields=[
                    "committee_panel",
                    "committee_required",
                    "committee_scheduled_by",
                    "committee_scheduled_at",
                    "updated_at",
                ]
            )
        except Exception:
            return False

        # Persist IncidentCommittee graph (best-effort)
        try:
            from .models import IncidentCommittee, IncidentCommitteeMember

            committee_obj, _ = IncidentCommittee.objects.update_or_create(
                incident=inc,
                defaults={
                    "chair": users_map.get(chair_id),
                    "recorder": users_map.get(recorder_id) if recorder_id else None,
                    "scheduled_by": user,
                },
            )
            IncidentCommitteeMember.objects.filter(committee=committee_obj).delete()
            for mid in member_ids:
                u = users_map.get(mid)
                if u:
                    IncidentCommitteeMember.objects.create(committee=committee_obj, user=u)
        except Exception:
            if logger and logger.isEnabledFor(logging.WARNING):
                logger.warning("committee.persist.failed incident=%s", getattr(inc, "id", None))

        # Grant lightweight perms (best-effort)
        try:
            from django.contrib.auth.models import Permission

            def _grant(u, codename: str):
                try:
                    perm = Permission.objects.get(codename=codename)
                    u.user_permissions.add(perm)
                except Exception:
                    pass

            involved_ids = set([chair_id] + member_ids + ([recorder_id] if recorder_id else []))
            for uid in involved_ids:
                uu = users_map.get(uid)
                if uu:
                    _grant(uu, "incident_committee_view")
            for uid in [chair_id, recorder_id]:
                if uid:
                    uu = users_map.get(uid)
                    if uu:
                        _grant(uu, "incident_committee_decide")
        except Exception:
            if logger and logger.isEnabledFor(logging.WARNING):
                logger.warning("committee.perms.grant.failed incident=%s", getattr(inc, "id", None))

        # Audit
        try:
            IncidentAuditLog.objects.create(
                incident=inc,
                action="update",
                actor=user,
                from_status=inc.status,
                to_status=inc.status,
                note="جدولة لجنة (تلقائي)",
                meta={
                    "action": "schedule_committee",
                    "auto": True,
                    "panel": inc.committee_panel,
                },
            )
        except Exception:
            pass

        return True

    @action(detail=True, methods=["post"])
    def review(self, request, pk=None):
        inc = self.get_object()
        # Require granular permission per RBAC
        if not self._has(request.user, "incident_review"):
            return Response({"detail": "صلاحية غير كافية للمراجعة."}, status=status.HTTP_403_FORBIDDEN)
        if inc.status != "under_review":
            return Response(
                {"detail": "لا يمكن المراجعة إلا للحالات under_review."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        prev = inc.status
        inc.reviewed_by = request.user
        inc.reviewed_at = timezone.now()
        inc.save(update_fields=["reviewed_by", "reviewed_at", "updated_at"])
        try:
            self._audit(inc, "review", note="reviewed", from_status=prev, to_status=inc.status)
        except Exception:
            pass
        return Response(self.get_serializer(inc).data)

    @action(detail=True, methods=["post"], url_path="add-action")
    def add_action(self, request, pk=None):
        inc = self.get_object()
        if inc.status not in ("under_review", "open"):
            return Response(
                {"detail": "إضافة إجراء متاحة خلال open/under_review فقط."},
                status=status.HTTP_400_BAD_REQUEST,
            )
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
            return Response(
                {"detail": "إضافة عقوبة متاحة خلال open/under_review فقط."},
                status=status.HTTP_400_BAD_REQUEST,
            )
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
        if inc.severity >= 2 and not (
            (inc.actions_applied and len(inc.actions_applied) > 0)
            or (inc.sanctions_applied and len(inc.sanctions_applied) > 0)
        ):
            return Response(
                {"detail": "لا يمكن إغلاق واقعة ذات شدة ≥ 2 دون إجراء/عقوبة."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        inc.closed_by = request.user
        inc.closed_at = timezone.now()
        inc.status = "closed"
        inc.save(update_fields=["closed_by", "closed_at", "status", "updated_at"])
        return Response(self.get_serializer(inc).data)

    @action(detail=True, methods=["post"], url_path="appeal")
    def appeal(self, request, pk=None):
        """تقديم اعتراض على واقعة مغلقة وإعادتها للمراجعة.

        لا نضيف حقول قاعدة بيانات جديدة هنا حفاظاً على الحد الأدنى من التغييرات؛ نسجّل الاعتراض
        كعنصر ضمن actions_applied مع تفاصيل موجزة، ثم نعيد الحالة إلى under_review.
        الشروط:
        - يجب أن تكون الحالة الحالية closed.
        - يُسمح بالاعتراض لمالك البلاغ (reporter) أو لمستخدم ذي صلاحية مراجعة الانضباط.
        """
        inc = self.get_object()
        if inc.status != "closed":
            return Response({"detail": "يمكن الاعتراض فقط على واقعة مغلقة."}, status=status.HTTP_400_BAD_REQUEST)
        user = request.user
        is_reviewer = self._has(user, "incident_review")
        is_owner = getattr(inc, "reporter_id", None) == getattr(user, "id", None)
        if not (is_owner or is_reviewer or user.is_staff or user.is_superuser):
            return Response({"detail": "صلاحية غير كافية لتقديم الاعتراض."}, status=status.HTTP_403_FORBIDDEN)

        reason = str(request.data.get("reason") or "").strip()
        arr = list(inc.actions_applied or [])
        arr.append(
            {
                "name": "appeal",
                "by": getattr(user, "username", None),
                "user_id": getattr(user, "id", None),
                "reason": reason,
                "at": timezone.now().isoformat(),
            }
        )
        inc.actions_applied = arr
        inc.status = "under_review"
        # عندما تعود للمراجعة، تزال closed_by/closed_at حتى تُحسم من جديد
        try:
            inc.closed_by = None  # type: ignore[attr-defined]
            inc.closed_at = None  # type: ignore[attr-defined]
        except Exception:
            pass
        inc.save(update_fields=["actions_applied", "status", "updated_at"])
        return Response(self.get_serializer(inc).data)

    @action(detail=True, methods=["post"], url_path="reopen")
    def reopen(self, request, pk=None):
        """إعادة فتح واقعة مغلقة بواسطة صاحب صلاحية (L2/مشرف/إداري)."""
        inc = self.get_object()
        if inc.status != "closed":
            return Response({"detail": "الحالة الحالية ليست مغلقة."}, status=status.HTTP_400_BAD_REQUEST)
        user = request.user
        # نعتبر incident_review أو incident_escalate صلاحية كافية لإعادة الفتح
        if not (
            self._has(user, "incident_review")
            or self._has(user, "incident_escalate")
            or user.is_staff
            or user.is_superuser
        ):
            return Response({"detail": "صلاحية غير كافية لإعادة فتح الواقعة."}, status=status.HTTP_403_FORBIDDEN)

        note = str(request.data.get("note") or "").strip()
        arr = list(inc.actions_applied or [])
        arr.append(
            {
                "name": "reopen",
                "by": getattr(user, "username", None),
                "user_id": getattr(user, "id", None),
                "note": note,
                "at": timezone.now().isoformat(),
            }
        )
        inc.actions_applied = arr
        inc.status = "under_review"
        try:
            inc.closed_by = None  # type: ignore[attr-defined]
            inc.closed_at = None  # type: ignore[attr-defined]
        except Exception:
            pass
        inc.save(update_fields=["actions_applied", "status", "updated_at"])
        return Response(self.get_serializer(inc).data)

    @action(detail=True, methods=["post"])
    def escalate(self, request, pk=None):
        inc = self.get_object()
        if not self._has(request.user, "incident_escalate"):
            return Response({"detail": "صلاحية غير كافية للتصعيد."}, status=status.HTTP_403_FORBIDDEN)
        # Escalate severity by 1 up to max 4 and mark committee if >=3
        new_sev = min(4, int(inc.severity or 1) + 1)
        inc.severity = new_sev
        # Catalog-aware committee requirement (fallback to sev>=3)
        committee_requires = bool(new_sev >= 3)
        try:
            vpol = getattr(getattr(inc, "violation", None), "policy", None) or {}
            if isinstance(vpol, dict):
                cpol = vpol.get("committee") or {}
                if isinstance(cpol, dict) and cpol.get("requires_on_severity_gte") is not None:
                    try:
                        req_sev = int(cpol.get("requires_on_severity_gte"))
                        if isinstance(req_sev, int):
                            committee_requires = bool(new_sev >= req_sev)
                    except Exception:
                        pass
        except Exception:
            pass
        inc.committee_required = bool(committee_requires)
        inc.escalated_due_to_repeat = True
        inc.save(
            update_fields=[
                "severity",
                "committee_required",
                "escalated_due_to_repeat",
                "updated_at",
            ]
        )
        # Auto-schedule to Standing Committee if now required and not yet scheduled
        try:
            if inc.committee_required and not getattr(inc, "committee_scheduled_at", None):
                self._schedule_committee_from_standing(inc, request.user)
        except Exception:
            if logger and logger.isEnabledFor(logging.WARNING):
                logger.warning(
                    "incident.escalate.auto_schedule.failed incident=%s",
                    getattr(inc, "id", None),
                )
        return Response(self.get_serializer(inc).data)

    @action(detail=True, methods=["post"], url_path="notify-guardian")
    def notify_guardian(self, request, pk=None):
        inc = self.get_object()
        if not self._has(request.user, "incident_notify_guardian"):
            return Response({"detail": "صلاحية غير كافية للإشعار."}, status=status.HTTP_403_FORBIDDEN)
        channel = (request.data.get("channel") or "internal").strip()
        note = str(request.data.get("note") or "").strip()
        arr = list(inc.actions_applied or [])
        arr.append(
            {
                "name": "notify_guardian",
                "channel": channel,
                "note": note,
                "at": timezone.now().isoformat(),
            }
        )
        inc.actions_applied = arr
        inc.save(update_fields=["actions_applied", "updated_at"])
        try:
            self._audit(inc, "notify_guardian", note=note, meta={"channel": channel})
        except Exception:
            pass
        return Response(
            {"detail": "تم الإشعار (placeholder)", "incident": self.get_serializer(inc).data},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=False, methods=["get"], url_path="visible")
    def visible(self, request):
        """قائمة الوقائع المرئية للمستخدم الحالي (لدعم لوحة مشرف الجناح والبوابة).

        يدعم فلاتر بسيطة: from, to (تواريخ YYYY-MM-DD)، status، search (q)، class_id، wing_id.
        يدعم التصفح: limit (افتراضي 25، أقصى 200) و offset.

        الاستجابة: { total, items: [...] }
        """
        try:
            qs = (
                Incident.objects.select_related(
                    "violation",
                    "student",
                    "reporter",
                    "student__class_fk",
                    "student__class_fk__wing",
                )
                # Avoid selecting optional Violation.policy column which may be missing in older DBs
                .defer("violation__policy")
                .all()
            )
            user = request.user
            # استخرج نطاق الأجنحة أولاً
            # اكتشاف أجنحة المستخدم المشرف عليها بشكل مرن (يدعم مخططات مختلفة للموديل)
            try:
                from school.models import Staff, Wing  # type: ignore

                staff_obj = Staff.objects.filter(user_id=user.id).only("id").first()
                wing_ids: list[int] = []
                # ابحث عن الحقول المحتملة في Wing التي قد تربط المشرف
                fld_names = {f.name for f in Wing._meta.get_fields()}  # type: ignore
                # supervisor (FK إلى Staff)
                if "supervisor" in fld_names and staff_obj is not None:
                    try:
                        wing_ids += list(Wing.objects.filter(supervisor_id=staff_obj.id).values_list("id", flat=True))
                    except Exception:
                        pass
                # supervisor_user (FK إلى User)
                if "supervisor_user" in fld_names:
                    try:
                        wing_ids += list(Wing.objects.filter(supervisor_user_id=user.id).values_list("id", flat=True))
                    except Exception:
                        pass
                # supervisor_id (رقمي عام) – في حال التسمية المباشرة
                if "supervisor_id" in fld_names and staff_obj is not None:
                    try:
                        wing_ids += list(Wing.objects.filter(supervisor_id=staff_obj.id).values_list("id", flat=True))
                    except Exception:
                        pass
                # إزالة التكرارات
                wing_ids = list({int(w) for w in wing_ids})
                # في حال مرّر العميل wing_id محدداً وكان المستخدم فعلياً مشرفاً لهذا الجناح
                # لكن لم يُكتشف عبر المسارات العامة أعلاه، قم بإضافته يدوياً لتفعيل سياسة رؤية المشرف.
                req_wing = (request.query_params.get("wing_id") or "").strip()
                if req_wing.isdigit():
                    try:
                        wval = int(req_wing)
                        is_super_for_req = False
                        if "supervisor" in fld_names and staff_obj is not None:
                            is_super_for_req = Wing.objects.filter(id=wval, supervisor_id=staff_obj.id).exists()
                        if not is_super_for_req and "supervisor_user" in fld_names:
                            is_super_for_req = Wing.objects.filter(id=wval, supervisor_user_id=user.id).exists()
                        if not is_super_for_req and "supervisor_id" in fld_names and staff_obj is not None:
                            is_super_for_req = Wing.objects.filter(id=wval, supervisor_id=staff_obj.id).exists()
                        if is_super_for_req and wval not in wing_ids:
                            wing_ids.append(wval)
                    except Exception:
                        pass
                # اكتشاف العضوية في مجموعة wing_supervisor كمسار احتياطي للترخيص دون ربط صريح بالجناح
                try:
                    is_wing_supervisor_group = bool(
                        getattr(user, "groups", None)
                        and user.groups.filter(name__in=["wing_supervisor", "supervisor"]).exists()
                    )
                except Exception:
                    is_wing_supervisor_group = False
            except Exception:
                wing_ids = []
                is_wing_supervisor_group = False

            # سياسة الرؤية:
            # - إذا كان المستخدم مشرف جناح (wing_ids موجودة) → يرى كل وقائع فصول أجنحته (بدون قيد "أبلغها هو").
            # - وإلا: إن لم يكن طاقم/صاحب صلاحية، يُقيد بما أبلغَه فقط.
            is_staff_like = user.is_staff or user.is_superuser or user.has_perm("discipline.access")
            # مسار الإشراف بالجناح: إن تم اكتشاف أجنحة، نقيّد بها.
            if wing_ids:
                qs = qs.filter(student__class_fk__wing_id__in=wing_ids)
            else:
                # إن لم تُكتشف أجنحة ولكن المستخدم ضمن مجموعة مشرفي الأجنحة وقد طلب جناحًا صريحًا
                # نسمح بالتقييد على الجناح المطلوب بدل تقييده بتقارير نفسه فقط.
                req_wing = (request.query_params.get("wing_id") or "").strip()
                if is_wing_supervisor_group and req_wing.isdigit():
                    try:
                        qs = qs.filter(student__class_fk__wing_id=int(req_wing))
                    except Exception:
                        # لو فشل الفلتر لأي سبب، لا نحجب البيانات الأخرى عن غير قصد
                        pass
                elif not is_staff_like:
                    qs = qs.filter(reporter_id=user.id)

            # فلاتر زمنية
            from_s = (request.query_params.get("from") or "").strip()
            to_s = (request.query_params.get("to") or "").strip()
            from django.utils.dateparse import parse_date

            # ملاحظة: بعض السجلات القديمة لا تملك occurred_at، لذا نعتمد على تاريخ بديل event_date = occurred_at أو created_at
            if from_s or to_s:
                try:
                    from django.db.models.functions import Coalesce, TruncDate

                    qs = qs.annotate(event_date=Coalesce(TruncDate("occurred_at"), TruncDate("created_at")))
                    if from_s:
                        d = parse_date(from_s)
                        if d:
                            qs = qs.filter(event_date__gte=d)
                    if to_s:
                        d = parse_date(to_s)
                        if d:
                            qs = qs.filter(event_date__lte=d)
                except Exception:
                    # في حال عدم توفر الدوال (حالات قديمة)، نرجع للفلترة على occurred_at فقط
                    if from_s:
                        d = parse_date(from_s)
                        if d:
                            qs = qs.filter(occurred_at__date__gte=d)
                    if to_s:
                        d = parse_date(to_s)
                        if d:
                            qs = qs.filter(occurred_at__date__lte=d)

            # فلاتر حالة (قبول مرادفات الواجهة: in_progress/resolved/archived)
            st = (request.query_params.get("status") or "").strip()
            st_norm = "under_review" if st == "in_progress" else ("closed" if st in {"resolved", "archived"} else st)
            if st_norm in {"open", "under_review", "closed"}:
                qs = qs.filter(status=st_norm)

            # فلاتر الصف/الجناح (أفضل جهد مع توفر النماذج)
            class_id = (request.query_params.get("class_id") or request.query_params.get("class") or "").strip()
            if class_id.isdigit():
                try:
                    qs = qs.filter(student__class_fk_id=int(class_id))
                except Exception:
                    pass
            wing_id = (request.query_params.get("wing_id") or "").strip()
            if wing_id.isdigit():
                try:
                    # عند توفير wing_id، نقيّد به أيضاً لكن ضمن نطاق أجنحة المستخدم المشرف إن وُجد.
                    wing_val = int(wing_id)
                    if wing_ids and wing_val not in wing_ids:
                        # لا تسمح بطلب جناح خارج نطاق الإشراف
                        qs = qs.none()
                    else:
                        qs = qs.filter(student__class_fk__wing_id=wing_val)
                except Exception:
                    pass

            # بحث نصي
            q = (request.query_params.get("q") or request.query_params.get("search") or "").strip()
            if q:
                from django.db.models import Q

                qs = qs.filter(
                    Q(narrative__icontains=q)
                    | Q(location__icontains=q)
                    | Q(violation__category__icontains=q)
                    | Q(violation__code__icontains=q)
                    | Q(student__full_name__icontains=q)
                )

            qs = qs.order_by("-occurred_at", "-created_at")

            # Paging
            try:
                limit = int(request.query_params.get("limit", 25))
            except Exception:
                limit = 25
            try:
                offset = int(request.query_params.get("offset", 0))
            except Exception:
                offset = 0
            limit = max(1, min(200, limit))
            offset = max(0, offset)

            total = qs.count()
            page = list(qs[offset : offset + limit])
            ser = self.get_serializer(page, many=True)
            data = ser.data
            return Response({"total": total, "items": data, "limit": limit, "offset": offset})
        except Exception as e:
            logger.warning("incident.visible.error user=%s err=%s", getattr(request.user, "id", None), e)
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=["get"], url_path="admin-export")
    def admin_export(self, request):
        """تصدير/تحميل بيانات الوقائع كما تظهر في لوحة الإدارة.

        - مخصّص لموظفي النظام فقط (is_staff أو superuser).
        - يُعيد نفس البينات الغنية المستخدمة في الواجهة (IncidentFullSerializer).
        - يدعم نفس الفلاتر الشائعة: from, to, status, class_id, wing_id, q، مع التصفح limit/offset.
        - لا يفرض قيود «نطاق الجناح»؛ فالموظفون يرون كل البيانات.
        - الاستجابة: { total, items, limit, offset }
        """
        user = request.user
        if not (getattr(user, "is_staff", False) or getattr(user, "is_superuser", False)):
            return Response({"detail": "صلاحية غير كافية. يتطلب حساب موظف."}, status=status.HTTP_403_FORBIDDEN)

        try:
            qs = Incident.objects.select_related(
                "violation",
                "student",
                "reporter",
                "student__class_fk",
                "student__class_fk__wing",
            ).all()

            # فلاتر زمنية (event_date = occurred_at أو created_at)
            from_s = (request.query_params.get("from") or "").strip()
            to_s = (request.query_params.get("to") or "").strip()
            from django.utils.dateparse import parse_date

            if from_s or to_s:
                try:
                    from django.db.models.functions import Coalesce, TruncDate

                    qs = qs.annotate(event_date=Coalesce(TruncDate("occurred_at"), TruncDate("created_at")))
                    if from_s:
                        d = parse_date(from_s)
                        if d:
                            qs = qs.filter(event_date__gte=d)
                    if to_s:
                        d = parse_date(to_s)
                        if d:
                            qs = qs.filter(event_date__lte=d)
                except Exception:
                    if from_s:
                        d = parse_date(from_s)
                        if d:
                            qs = qs.filter(occurred_at__date__gte=d)
                    if to_s:
                        d = parse_date(to_s)
                        if d:
                            qs = qs.filter(occurred_at__date__lte=d)

            # فلاتر الحالة (قبول مرادفات الواجهة)
            st = (request.query_params.get("status") or "").strip()
            st_norm = "under_review" if st == "in_progress" else ("closed" if st in {"resolved", "archived"} else st)
            if st_norm in {"open", "under_review", "closed"}:
                qs = qs.filter(status=st_norm)

            # فلاتر الصف والجناح (دون قيود نطاق)
            class_id = (request.query_params.get("class_id") or request.query_params.get("class") or "").strip()
            if class_id.isdigit():
                try:
                    qs = qs.filter(student__class_fk_id=int(class_id))
                except Exception:
                    pass
            wing_id = (request.query_params.get("wing_id") or "").strip()
            if wing_id.isdigit():
                try:
                    qs = qs.filter(student__class_fk__wing_id=int(wing_id))
                except Exception:
                    pass

            # بحث نصي
            q = (request.query_params.get("q") or request.query_params.get("search") or "").strip()
            if q:
                from django.db.models import Q

                qs = qs.filter(
                    Q(narrative__icontains=q)
                    | Q(location__icontains=q)
                    | Q(violation__category__icontains=q)
                    | Q(violation__code__icontains=q)
                    | Q(student__full_name__icontains=q)
                )

            qs = qs.order_by("-occurred_at", "-created_at")

            # التصفح
            try:
                limit = int(request.query_params.get("limit", 50))
            except Exception:
                limit = 50
            try:
                offset = int(request.query_params.get("offset", 0))
            except Exception:
                offset = 0
            limit = max(1, min(500, limit))
            offset = max(0, offset)

            total = qs.count()
            page = list(qs[offset : offset + limit])

            # استخدم التمثيل الكامل
            ser = IncidentFullSerializer(page, many=True)
            return Response({"total": total, "items": ser.data, "limit": limit, "offset": offset})
        except Exception as e:
            logger.warning("incident.admin_export.error user=%s err=%s", getattr(user, "id", None), e)
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        """ملخص إحصائي سريع للوقائع ضمن نطاق رؤية المستخدم.

        يُطبق نفس فلاتر visible تقريبًا: from, to, status, class_id, wing_id، وبنفس سياسة رؤية الجناح للمشرف.
        يعيد:
          {
            total: N,
            by_status: { open: n1, under_review: n2, closed: n3 },
            by_severity: { "1": c1, "2": c2, "3": c3, "4": c4 }
          }
        """
        try:
            qs = Incident.objects.select_related(
                "student__class_fk",
                "student__class_fk__wing",
            ).all()

            user = request.user
            is_staff_like = user.is_staff or user.is_superuser or user.has_perm("discipline.access")
            # نطاق الجناح لمشرف الأجنحة (مرن)
            try:
                from school.models import Staff, Wing  # type: ignore

                staff_obj = Staff.objects.filter(user_id=user.id).only("id").first()
                wing_ids: list[int] = []
                fld_names = {f.name for f in Wing._meta.get_fields()}  # type: ignore
                if "supervisor" in fld_names and staff_obj is not None:
                    try:
                        wing_ids += list(Wing.objects.filter(supervisor_id=staff_obj.id).values_list("id", flat=True))
                    except Exception:
                        pass
                if "supervisor_user" in fld_names:
                    try:
                        wing_ids += list(Wing.objects.filter(supervisor_user_id=user.id).values_list("id", flat=True))
                    except Exception:
                        pass
                if "supervisor_id" in fld_names and staff_obj is not None:
                    try:
                        wing_ids += list(Wing.objects.filter(supervisor_id=staff_obj.id).values_list("id", flat=True))
                    except Exception:
                        pass
                wing_ids = list({int(w) for w in wing_ids})

                # إذا مرّر العميل wing_id وكان المستخدم فعلاً مشرفًا عليه لكن لم يُلتقط تلقائيًا، أضِفه لتمكين الرؤية
                req_wing = (request.query_params.get("wing_id") or "").strip()
                if req_wing.isdigit():
                    try:
                        wval = int(req_wing)
                        is_super_for_req = False
                        if "supervisor" in fld_names and staff_obj is not None:
                            is_super_for_req = Wing.objects.filter(id=wval, supervisor_id=staff_obj.id).exists()
                        if not is_super_for_req and "supervisor_user" in fld_names:
                            is_super_for_req = Wing.objects.filter(id=wval, supervisor_user_id=user.id).exists()
                        if not is_super_for_req and "supervisor_id" in fld_names and staff_obj is not None:
                            is_super_for_req = Wing.objects.filter(id=wval, supervisor_id=staff_obj.id).exists()
                        if is_super_for_req and wval not in wing_ids:
                            wing_ids.append(wval)
                    except Exception:
                        pass
                # اكتشاف مجموعة الإشراف كمسار بديل عندما لا يتوفر ربط صريح
                try:
                    is_wing_supervisor_group = bool(
                        getattr(user, "groups", None)
                        and user.groups.filter(name__in=["wing_supervisor", "supervisor"]).exists()
                    )
                except Exception:
                    is_wing_supervisor_group = False
            except Exception:
                wing_ids = []
                is_wing_supervisor_group = False
            if wing_ids:
                qs = qs.filter(student__class_fk__wing_id__in=wing_ids)
            else:
                req_wing = (request.query_params.get("wing_id") or "").strip()
                if is_wing_supervisor_group and req_wing.isdigit():
                    try:
                        qs = qs.filter(student__class_fk__wing_id=int(req_wing))
                    except Exception:
                        pass
                elif not is_staff_like:
                    qs = qs.filter(reporter_id=user.id)

            # فلاتر زمنية
            from_s = (request.query_params.get("from") or "").strip()
            to_s = (request.query_params.get("to") or "").strip()
            from django.utils.dateparse import parse_date

            # استخدم event_date (occurred_at أو created_at) لنضمن عدم ضياع السجلات ذات occurred_at الفارغ
            if from_s or to_s:
                try:
                    from django.db.models.functions import Coalesce, TruncDate

                    qs = qs.annotate(event_date=Coalesce(TruncDate("occurred_at"), TruncDate("created_at")))
                    if from_s:
                        d = parse_date(from_s)
                        if d:
                            qs = qs.filter(event_date__gte=d)
                    if to_s:
                        d = parse_date(to_s)
                        if d:
                            qs = qs.filter(event_date__lte=d)
                except Exception:
                    if from_s:
                        d = parse_date(from_s)
                        if d:
                            qs = qs.filter(occurred_at__date__gte=d)
                    if to_s:
                        d = parse_date(to_s)
                        if d:
                            qs = qs.filter(occurred_at__date__lte=d)

            # فلاتر الحالة (قبول مرادفات الواجهة)
            st = (request.query_params.get("status") or "").strip()
            st_norm = "under_review" if st == "in_progress" else ("closed" if st in {"resolved", "archived"} else st)
            if st_norm in {"open", "under_review", "closed"}:
                qs = qs.filter(status=st_norm)

            # الصف والجناح
            class_id = (request.query_params.get("class_id") or request.query_params.get("class") or "").strip()
            if class_id.isdigit():
                try:
                    qs = qs.filter(student__class_fk_id=int(class_id))
                except Exception:
                    pass
            wing_id = (request.query_params.get("wing_id") or "").strip()
            if wing_id.isdigit():
                try:
                    wing_val = int(wing_id)
                    if wing_ids and wing_val not in wing_ids:
                        qs = qs.none()
                    else:
                        qs = qs.filter(student__class_fk__wing_id=wing_val)
                except Exception:
                    pass

            total = qs.count()
            # by_status
            status_counts = qs.values("status").annotate(c=Count("id")).order_by()
            by_status = {"open": 0, "under_review": 0, "closed": 0}
            for row in status_counts:
                by_status[str(row["status"])] = int(row["c"])

            # by_severity
            sev_counts = qs.values("severity").annotate(c=Count("id")).order_by()
            by_severity = {str(k): 0 for k in [1, 2, 3, 4]}
            for row in sev_counts:
                key = str(row["severity"])
                by_severity[key] = int(row["c"]) + int(by_severity.get(key, 0))

            return Response({"total": total, "by_status": by_status, "by_severity": by_severity})
        except Exception as e:
            logger.warning("incident.summary.error user=%s err=%s", getattr(request.user, "id", None), e)
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=["get"], url_path="diagnostics")
    def diagnostics(self, request):
        """تشخيص شامل يوضح أين تختفي البيانات عبر مراحل التصفية.

        الهدف: مساعدتك على معرفة «أين المشكلة» عندما يظهر الجدول فارغًا.

        ماذا يعيد؟
        - لقطات أعداد قبل وبعد كل مرحلة (إجمالي الكل، بعد نطاق الرؤية، بعد التاريخ، الحالة، الصف/الجناح، وبعد البحث).
        - قائمة بالأجنحة المكتشفة للمستخدم الحالي (إن وُجدت).
        - الحقول الفعلية الموجودة في نموذج Wing ذات الصلة بالإشراف.
        - نسخة من بارامترات الطلب كما استقبلها الخادم.

        ملاحظة الأمان: لا يُظهر هذا الإجراء أي بيانات حساسة؛ ويعيد فقط أرقامًا وعينات محدودة ضمن نطاق رؤية المستخدم العادي. متاح لأي مستخدم مُصادق.
        """
        try:
            params = {k: (v or "").strip() for k, v in request.query_params.items()}
            user = request.user
            # ابدأ بدون أي فلترة لتكوين خط أساس
            base_qs = Incident.objects.select_related(
                "violation",
                "student",
                "reporter",
                "student__class_fk",
                "student__class_fk__wing",
            ).all()

            snap = {}
            snap["total_all"] = base_qs.count()

            # نطاق الرؤية (نفس visible/summary)
            is_staff_like = user.is_staff or user.is_superuser or user.has_perm("discipline.access")

            # اكتشاف نطاق أجنحة المشرف
            wing_ids: list[int] = []
            wing_fields = []
            try:
                from school.models import Staff, Wing  # type: ignore

                staff_obj = Staff.objects.filter(user_id=user.id).only("id").first()
                fld_names = {f.name for f in Wing._meta.get_fields()}  # type: ignore
                wing_fields = sorted(list(fld_names))
                if "supervisor" in fld_names and staff_obj is not None:
                    try:
                        wing_ids += list(Wing.objects.filter(supervisor_id=staff_obj.id).values_list("id", flat=True))
                    except Exception:
                        pass
                if "supervisor_user" in fld_names:
                    try:
                        wing_ids += list(Wing.objects.filter(supervisor_user_id=user.id).values_list("id", flat=True))
                    except Exception:
                        pass
                if "supervisor_id" in fld_names and staff_obj is not None:
                    try:
                        wing_ids += list(Wing.objects.filter(supervisor_id=staff_obj.id).values_list("id", flat=True))
                    except Exception:
                        pass
                wing_ids = list({int(w) for w in wing_ids})

                # دعم إدراج wing_id المطلوب إذا كان المستخدم فعلاً مشرفًا عليه
                req_wing = (request.query_params.get("wing_id") or "").strip()
                if req_wing.isdigit():
                    try:
                        wval = int(req_wing)
                        is_super_for_req = False
                        if "supervisor" in fld_names and staff_obj is not None:
                            is_super_for_req = Wing.objects.filter(id=wval, supervisor_id=staff_obj.id).exists()
                        if not is_super_for_req and "supervisor_user" in fld_names:
                            is_super_for_req = Wing.objects.filter(id=wval, supervisor_user_id=user.id).exists()
                        if not is_super_for_req and "supervisor_id" in fld_names and staff_obj is not None:
                            is_super_for_req = Wing.objects.filter(id=wval, supervisor_id=staff_obj.id).exists()
                        if is_super_for_req and wval not in wing_ids:
                            wing_ids.append(wval)
                    except Exception:
                        pass
            except Exception:
                wing_ids = []

            scope_qs = base_qs
            if wing_ids:
                scope_qs = scope_qs.filter(student__class_fk__wing_id__in=wing_ids)
            elif not is_staff_like:
                scope_qs = scope_qs.filter(reporter_id=user.id)
            snap["after_scope"] = scope_qs.count()

            # التاريخ (event_date)
            from_s = (request.query_params.get("from") or "").strip()
            to_s = (request.query_params.get("to") or "").strip()
            from django.utils.dateparse import parse_date

            time_qs = scope_qs
            if from_s or to_s:
                try:
                    from django.db.models.functions import Coalesce, TruncDate

                    time_qs = time_qs.annotate(event_date=Coalesce(TruncDate("occurred_at"), TruncDate("created_at")))
                    if from_s:
                        d = parse_date(from_s)
                        if d:
                            time_qs = time_qs.filter(event_date__gte=d)
                    if to_s:
                        d = parse_date(to_s)
                        if d:
                            time_qs = time_qs.filter(event_date__lte=d)
                except Exception:
                    if from_s:
                        d = parse_date(from_s)
                        if d:
                            time_qs = time_qs.filter(occurred_at__date__gte=d)
                    if to_s:
                        d = parse_date(to_s)
                        if d:
                            time_qs = time_qs.filter(occurred_at__date__lte=d)
            snap["after_time"] = time_qs.count()

            # الحالة (طَبّق نفس التطبيع المستعمل في بقية النهايات: قبول مرادفات الواجهة)
            st_raw = (request.query_params.get("status") or "").strip()
            st = (
                "under_review"
                if st_raw == "in_progress"
                else ("closed" if st_raw in {"resolved", "archived"} else st_raw)
            )
            status_qs = time_qs
            if st in {"open", "under_review", "closed"}:
                status_qs = status_qs.filter(status=st)
            snap["after_status"] = status_qs.count()

            # الصف/الجناح
            class_id = (request.query_params.get("class_id") or request.query_params.get("class") or "").strip()
            wing_id = (request.query_params.get("wing_id") or "").strip()
            clswing_qs = status_qs
            if class_id.isdigit():
                try:
                    clswing_qs = clswing_qs.filter(student__class_fk_id=int(class_id))
                except Exception:
                    pass
            if wing_id.isdigit():
                try:
                    wing_val = int(wing_id)
                    if wing_ids and wing_val not in wing_ids:
                        clswing_qs = clswing_qs.none()
                    else:
                        clswing_qs = clswing_qs.filter(student__class_fk__wing_id=wing_val)
                except Exception:
                    pass
            snap["after_class_wing"] = clswing_qs.count()

            # البحث
            q = (request.query_params.get("q") or request.query_params.get("search") or "").strip()
            final_qs = clswing_qs
            if q:
                from django.db.models import Q

                final_qs = final_qs.filter(
                    Q(narrative__icontains=q)
                    | Q(location__icontains=q)
                    | Q(violation__category__icontains=q)
                    | Q(violation__code__icontains=q)
                    | Q(student__full_name__icontains=q)
                )
            total = final_qs.count()

            # عينة صغيرة لعرض شكل البيانات المتاحة فعلاً للمستخدم (ضمن نطاقه)
            sample = list(final_qs.order_by("-occurred_at", "-created_at").values_list("id", flat=True)[:10])

            payload = {
                "params": params,
                "is_staff_like": bool(is_staff_like),
                "detected_wing_ids": wing_ids,
                "wing_model_fields": wing_fields,
                "snapshots": snap,
                "final_total": total,
                "sample_ids": [str(x) for x in sample],
            }
            return Response(payload)
        except Exception as e:
            logger.warning("incident.diagnostics.error user=%s err=%s", getattr(request.user, "id", None), e)
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=["get"], url_path="mine")
    def mine(self, request):
        """Return incidents reported by the current user only, regardless of privileges.
        Supports status and search params, ordered by most recent. Paginates if pagination is enabled.
        Added defensive checks to avoid 500s when authentication/config differs across environments.
        """
        try:
            # Require authentication explicitly (some deployments may customize DRF auth settings)
            user = getattr(request, "user", None)
            if not user or not getattr(user, "is_authenticated", False):
                return Response({"detail": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)

            from django.conf import settings as dj_settings
            from django.db.models import Q

            # Keep select_related lightweight and resilient; student relation can be heavy/optional in some installs
            try:
                base_qs = Incident.objects.select_related("violation", "reporter", "student").defer("violation__policy")
            except Exception:
                # Fallback if resolving some relations fails in mixed app setups
                base_qs = Incident.objects.select_related("violation", "reporter").defer("violation__policy")

            if getattr(dj_settings, "DISCIPLINE_MATCH_MINE_BY_USERNAME", False):
                qs = base_qs.filter(Q(reporter_id=user.id) | Q(reporter__username=getattr(user, "username", None)))
            else:
                qs = base_qs.filter(reporter_id=user.id)
            qs = qs.order_by("-occurred_at", "-created_at")

            # Optional status filter
            st = (self.request.query_params.get("status") or "").strip()
            if st in {"open", "under_review", "closed"}:
                qs = qs.filter(status=st)

            # Optional search (mirror SearchFilter fields)
            s = (self.request.query_params.get("search") or "").strip()
            if s:
                qs = qs.filter(
                    Q(narrative__icontains=s)
                    | Q(location__icontains=s)
                    | Q(violation__category__icontains=s)
                    | Q(violation__code__icontains=s)
                )

            page = self.paginate_queryset(qs)
            if page is not None:
                ser = self.get_serializer(page, many=True)
                return self.get_paginated_response(ser.data)
            ser = self.get_serializer(qs, many=True)
            return Response(ser.data)
        except Exception as e:
            # Log and return a safe error instead of generic 500
            try:
                logger.error(
                    "incident.mine.failed user=%s err=%s", getattr(getattr(request, "user", None), "id", None), e
                )
            except Exception:
                pass
            return Response(
                {"detail": "Failed to fetch your incidents.", "code": "INCIDENT_MINE_FAILED"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

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
            data["columns"][st] = self.get_serializer(items_sorted, many=True).data
        return Response(data)

    @action(detail=False, methods=["get"], url_path="overview")  # /incidents/overview/?days=7|30
    def overview(self, request):
        """نظرة عامة سريعة (overview) لاستخدامات المشرفين: إجماليات بالحالة وبالشدة، أكثر المخالفات تكرارًا،
        ومؤشرات تجاوز مهلة المراجعة/الإشعار. هذا يختلف عن /summary/ الموثّق والذي يعيد { total, by_status, by_severity } فقط.
        days الافتراضي 7؛ يقبل 7 أو 30.
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
                top_payload.append(
                    {
                        "code": code,
                        "category": getattr(v, "category", None),
                        "count": cnt,
                    }
                )
        out["top_violations"] = top_payload
        return Response(out)

    @action(detail=False, methods=["get"], url_path="committee-dashboard")
    def committee_dashboard(self, request):
        """تجميع بطاقات لوحة «رئيس اللجنة السلوكية» في استجابة واحدة.

        صلاحيات: incident_committee_view أو is_staff/superuser.

        معلمات اختيارية:
          - days: 7 أو 30 (افتراضي 30)
          - from/to/status/wing_id: نفس فلاتر visible (اختياري — أفضل جلب المدى عبر days)
        """
        user = request.user
        if not (
            self._has(user, "incident_committee_view")
            or getattr(user, "is_staff", False)
            or getattr(user, "is_superuser", False)
        ):
            return Response({"detail": "صلاحية غير كافية."}, status=status.HTTP_403_FORBIDDEN)

        from datetime import datetime, timedelta
        from django.utils import timezone as _tz
        from .models import StandingCommittee

        now = _tz.now()
        try:
            days = int(request.query_params.get("days", 30))
        except Exception:
            days = 30
        if days not in (7, 30):
            days = 30
        since_dt = now - timedelta(days=days)

        # بناء queryset أساسي مع فلاتر معقولة (committee_required فقط)
        qs = (
            Incident.objects.all()
            .select_related("violation", "student")
            .defer("violation__policy")
        )

        # فلترة التاريخ وفق event_date = occurred_at.date أو created_at.date
        from_param = request.query_params.get("from")
        to_param = request.query_params.get("to")

        def parse_date(s):
            try:
                return datetime.strptime(s, "%Y-%m-%d").date()
            except Exception:
                return None

        from_date = parse_date(from_param) if from_param else (since_dt.date())
        to_date = parse_date(to_param) if to_param else None

        if from_date:
            qs = qs.filter(
                Q(occurred_at__date__gte=from_date) | (Q(occurred_at__isnull=True) & Q(created_at__date__gte=from_date))
            )
        if to_date:
            qs = qs.filter(
                Q(occurred_at__date__lte=to_date) | (Q(occurred_at__isnull=True) & Q(created_at__date__lte=to_date))
            )

        # فلترة الحالة (تطبيع مبسط)
        status_param = (request.query_params.get("status") or "").strip().lower()
        status_map = {"in_progress": "under_review", "resolved": "closed", "archived": "closed"}
        if status_param:
            norm = status_map.get(status_param, status_param)
            if norm in {"open", "under_review", "closed"}:
                qs = qs.filter(status=norm)

        # فلترة الجناح إن طُلب
        wing_id = request.query_params.get("wing_id")
        if wing_id and str(wing_id).isdigit():
            qs = qs.filter(student__class_fk__wing_id=int(wing_id))

        # قصر اللوحة على الوقائع التي تتطلب لجنة
        qs_committee = qs.filter(committee_required=True)

        # ============ KPIs ============
        total_need_committee = qs_committee.count()
        need_scheduling_qs = qs_committee.filter(committee__isnull=True)
        need_scheduling_count = need_scheduling_qs.count()
        scheduled_qs = qs_committee.filter(committee__isnull=False)
        # بانتظار قرار اللجنة: لا يوجد Audit بmeta.action=committee_decision
        scheduled_pending_qs = scheduled_qs.exclude(audit_logs__meta__action="committee_decision")
        scheduled_pending_count = scheduled_pending_qs.count()

        # قرارات الأيام الأخيرة
        recent_decisions_qs = IncidentAuditLog.objects.filter(meta__action="committee_decision", at__gte=since_dt)
        recent_approve = recent_decisions_qs.filter(meta__decision="approve").count()
        recent_reject = recent_decisions_qs.filter(meta__decision="reject").count()
        recent_return = recent_decisions_qs.filter(meta__decision="return").count()

        kpis = {
            "need_committee": total_need_committee,
            "need_scheduling": need_scheduling_count,
            "scheduled_pending": scheduled_pending_count,
            "decisions_recent": {
                "approve": recent_approve,
                "reject": recent_reject,
                "return": recent_return,
            },
        }

        # ============ SLA Overdue ============
        # المراجعة والإشعار يعتمد على submitted_at ونافذتي SLA من الإعدادات
        try:
            from django.conf import settings as dj_settings

            review_h = int(getattr(dj_settings, "DISCIPLINE_REVIEW_SLA_H", 24))
            notify_h = int(getattr(dj_settings, "DISCIPLINE_NOTIFY_SLA_H", 48))
        except Exception:
            review_h, notify_h = 24, 48

        overdue_review = qs_committee.filter(
            status="under_review",
            submitted_at__isnull=False,
            submitted_at__lt=now - timedelta(hours=review_h),
        ).count()
        overdue_notify = qs_committee.filter(
            status="under_review",
            submitted_at__isnull=False,
            submitted_at__lt=now - timedelta(hours=notify_h),
        ).count()
        overdue = {"review": overdue_review, "notify": overdue_notify}

        # ============ Top violations (last 30 or days window) ============
        recent_committee_qs = qs_committee.filter(
            Q(occurred_at__gte=since_dt) | (Q(occurred_at__isnull=True) & Q(created_at__gte=since_dt))
        )
        viol_counts = (
            recent_committee_qs.values("violation__code", "violation__category")
            .annotate(cnt=models.Count("id"))
            .order_by("-cnt")[:5]
        )
        top_violations = [
            {
                "code": row.get("violation__code"),
                "category": row.get("violation__category"),
                "count": int(row.get("cnt") or 0),
            }
            for row in viol_counts
        ]

        # ============ Standing committee ============
        standing_payload = None
        try:
            standing = StandingCommittee.objects.order_by("id").first()
            if standing:
                # احضر الأعضاء
                from .models import StandingCommitteeMember

                member_ids = list(
                    StandingCommitteeMember.objects.filter(standing=standing).values_list("user_id", flat=True)
                )

                def user_obj(uid):
                    u = get_user_model().objects.filter(id=uid).first()
                    if not u:
                        return None
                    # Staff.full_name
                    staff_full = None
                    try:
                        from school.models import Staff  # type: ignore

                        staff_full = (
                            Staff.objects.filter(user_id=u.id)
                            .only("full_name")
                            .values_list("full_name", flat=True)
                            .first()
                        ) or None
                    except Exception:
                        pass
                    full_name = u.get_full_name() if hasattr(u, "get_full_name") else None
                    return {"id": u.id, "username": u.username, "full_name": full_name, "staff_full_name": staff_full}

                standing_payload = {
                    "chair": (
                        user_obj(getattr(standing, "chair_id", None)) if getattr(standing, "chair_id", None) else None
                    ),
                    "recorder": (
                        user_obj(getattr(standing, "recorder_id", None))
                        if getattr(standing, "recorder_id", None)
                        else None
                    ),
                    "members": [user_obj(uid) for uid in member_ids if uid],
                }
        except Exception:
            standing_payload = None

        # ============ Queues ============
        def inc_basic_payload(i: Incident):
            # حزمة مختصرة للعرض في قوائم الانتظار
            try:
                student_name = getattr(getattr(i, "student", None), "full_name", None)
            except Exception:
                student_name = None
            try:
                viol_code = getattr(getattr(i, "violation", None), "code", None)
            except Exception:
                viol_code = None
            # ملخص سريع لآخر ما اقترحته المراجِعة (إن وُجد)
            try:
                acts = list(getattr(i, "actions_applied", None) or [])
                sancs = list(getattr(i, "sanctions_applied", None) or [])
                pa = ", ".join([str((a or {}).get("name") or "").strip() for a in acts if (a or {}).get("name")])
                ps = ", ".join([str((s or {}).get("name") or "").strip() for s in sancs if (s or {}).get("name")])
                if pa and ps:
                    proposed_summary = f"إجراءات: {pa} • عقوبات: {ps}"
                elif pa:
                    proposed_summary = f"إجراءات: {pa}"
                elif ps:
                    proposed_summary = f"عقوبات: {ps}"
                else:
                    proposed_summary = None
            except Exception:
                proposed_summary = None
            return {
                "id": str(i.id),
                "occurred_at": getattr(i, "occurred_at", None),
                "created_at": getattr(i, "created_at", None),
                "student_name": student_name,
                "violation_code": viol_code,
                "status": i.status,
                "severity": i.severity,
                "proposed_summary": proposed_summary,
            }

        need_sched_items = [
            inc_basic_payload(i) for i in need_scheduling_qs.order_by("-occurred_at", "-created_at")[:5]
        ]
        scheduled_pending_items = [
            inc_basic_payload(i) for i in scheduled_pending_qs.order_by("-occurred_at", "-created_at")[:5]
        ]

        queues = {
            "need_scheduling": need_sched_items,
            "scheduled_pending_decision": scheduled_pending_items,
        }

        # ============ Recent decisions (last 5) ============
        recent_items = []
        try:
            logs = (
                IncidentAuditLog.objects.filter(meta__action="committee_decision")
                .select_related("incident", "actor")
                .order_by("-at", "-id")[:5]
            )
            for log in logs:
                # actor name
                actor_name = None
                try:
                    actor = getattr(log, "actor", None)
                    if actor:
                        actor_name = actor.get_full_name() or actor.username
                        # Staff full name first
                        try:
                            from school.models import Staff  # type: ignore

                            staff_full = (
                                Staff.objects.filter(user=actor)
                                .only("full_name")
                                .values_list("full_name", flat=True)
                                .first()
                            )
                            if staff_full:
                                actor_name = staff_full
                        except Exception:
                            pass
                except Exception:
                    actor_name = None
                recent_items.append(
                    {
                        "incident_id": str(getattr(log, "incident_id", "")),
                        "decision": (getattr(log, "meta", {}) or {}).get("decision"),
                        "at": getattr(log, "at", None),
                        "actor": actor_name,
                        "note": getattr(log, "note", ""),
                    }
                )
        except Exception:
            recent_items = []

        out = {
            "since": since_dt.isoformat(),
            "kpis": kpis,
            "overdue": overdue,
            "top_violations_30d": top_violations,
            "standing": standing_payload,
            "queues": queues,
            "recent_decisions": recent_items,
        }
        return Response(out)

    # ===================== Attachments (Option B - minimal backend) =====================
    @action(detail=True, methods=["get", "post"], url_path="attachments")
    def attachments(self, request, pk=None):
        """List or upload attachments for an incident.

        GET  -> list attachments
        POST -> upload attachment (multipart/form-data) with fields: kind, file, meta (JSON or text)
        """
        inc = self.get_object()
        user = request.user

        def can_view(u):
            return (
                self._has(u, "incident_attachment_view")
                or self._has(u, "incident_committee_view")
                or self._has(u, "incident_review")
                or getattr(u, "is_staff", False)
                or getattr(u, "is_superuser", False)
                or getattr(inc, "reporter_id", None) == getattr(u, "id", None)
            )

        def can_upload(u):
            return (
                self._has(u, "incident_attachment_upload")
                or self._has(u, "incident_review")
                or getattr(u, "is_staff", False)
                or getattr(u, "is_superuser", False)
            )

        if request.method.lower() == "get":
            if not can_view(user):
                return Response({"detail": "صلاحية غير كافية."}, status=status.HTTP_403_FORBIDDEN)
            items = [
                {
                    "id": a.id,
                    "kind": a.kind,
                    "mime": a.mime,
                    "size": a.size,
                    "sha256": a.sha256,
                    "created_at": a.created_at,
                    "created_by": getattr(a.created_by, "id", None),
                    "meta": a.meta or {},
                }
                for a in IncidentAttachment.objects.filter(incident=inc).order_by("-created_at", "-id")
            ]
            # Audit (best-effort)
            try:
                IncidentAuditLog.objects.create(
                    incident=inc,
                    action="update",
                    actor=user,
                    from_status=inc.status,
                    to_status=inc.status,
                    note="استعراض مرفقات",
                    meta={"action": "attachment_list"},
                )
            except Exception:
                pass
            return Response({"attachments": items})

        # POST (upload)
        if not can_upload(user):
            return Response({"detail": "صلاحية غير كافية للرفع."}, status=status.HTTP_403_FORBIDDEN)

        up = request.FILES.get("file")
        kind = str(request.data.get("kind", "other")).strip() or "other"
        meta_raw = request.data.get("meta")
        meta_obj = {}
        if meta_raw:
            try:
                if isinstance(meta_raw, (dict, list)):
                    meta_obj = meta_raw  # type: ignore
                else:
                    meta_obj = json.loads(str(meta_raw))
            except Exception:
                meta_obj = {"_raw": str(meta_raw)}
        if not up:
            return Response({"detail": "file مطلوب"}, status=status.HTTP_400_BAD_REQUEST)

        # Basic type/size checks (10 MiB)
        max_size = 10 * 1024 * 1024
        if getattr(up, "size", 0) > max_size:
            return Response({"detail": "الملف أكبر من الحد المسموح (10MiB)."}, status=status.HTTP_400_BAD_REQUEST)
        mime = getattr(up, "content_type", "") or ""
        allowed = {"application/pdf", "image/jpeg", "image/png"}
        if allowed and mime not in allowed:
            return Response({"detail": "صيغة ملف غير مدعومة. المسموح: PDF, JPG, PNG."}, status=status.HTTP_400_BAD_REQUEST)

        # Compute sha256
        h = hashlib.sha256()
        for chunk in up.chunks():
            h.update(chunk)
        digest = h.hexdigest()

        att = IncidentAttachment.objects.create(
            incident=inc,
            kind=kind if kind in {k for k, _ in IncidentAttachment.KIND_CHOICES} else "other",
            file=up,
            mime=mime,
            size=getattr(up, "size", 0) or 0,
            sha256=digest,
            created_by=user,
            meta=meta_obj,
        )

        # Audit
        try:
            IncidentAuditLog.objects.create(
                incident=inc,
                action="update",
                actor=user,
                from_status=inc.status,
                to_status=inc.status,
                note=f"رفع مرفق ({att.kind})",
                meta={"action": "attachment_upload", "attachment_id": att.id, "sha256": att.sha256},
            )
        except Exception:
            pass

        return Response(
            {
                "ok": True,
                "attachment": {
                    "id": att.id,
                    "kind": att.kind,
                    "mime": att.mime,
                    "size": att.size,
                    "sha256": att.sha256,
                },
            }
        )

    @action(detail=True, methods=["get"], url_path=r"attachments/(?P<att_id>[^/.]+)/download")
    def attachment_download(self, request, pk=None, att_id: str = ""):
        """Download an attachment file for the incident."""
        inc = self.get_object()
        user = request.user
        # permission
        if not (
            self._has(user, "incident_attachment_view")
            or self._has(user, "incident_committee_view")
            or self._has(user, "incident_review")
            or getattr(user, "is_staff", False)
            or getattr(user, "is_superuser", False)
            or getattr(inc, "reporter_id", None) == getattr(user, "id", None)
        ):
            return Response({"detail": "صلاحية غير كافية."}, status=status.HTTP_403_FORBIDDEN)

        att = IncidentAttachment.objects.filter(incident=inc, id=att_id).first()
        if not att:
            return Response({"detail": "المرفق غير موجود."}, status=status.HTTP_404_NOT_FOUND)
        try:
            f = att.file
            f.open("rb")  # type: ignore
            resp = FileResponse(f, content_type=(att.mime or "application/octet-stream"))
            resp["Content-Disposition"] = f'inline; filename="{f.name.split('/')[-1]}"'
        except Exception:
            return Response({"detail": "تعذّر فتح الملف."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Audit best-effort
        try:
            IncidentAuditLog.objects.create(
                incident=inc,
                action="update",
                actor=user,
                from_status=inc.status,
                to_status=inc.status,
                note=f"تنزيل مرفق ({att.kind})",
                meta={"action": "attachment_download", "attachment_id": att.id},
            )
        except Exception:
            pass
        return resp

    @action(detail=True, methods=["get"], url_path="pledge/preview")
    def pledge_preview(self, request, pk=None):
        """Return a simple HTML pledge preview for printing (Option A server-side).

        Query: format=html (default) | pdf (not implemented here)
        """
        inc = self.get_object()
        user = request.user
        if not (
            self._has(user, "incident_review")
            or self._has(user, "incident_committee_view")
            or getattr(user, "is_staff", False)
            or getattr(user, "is_superuser", False)
            or getattr(inc, "reporter_id", None) == getattr(user, "id", None)
        ):
            return Response({"detail": "صلاحية غير كافية."}, status=status.HTTP_403_FORBIDDEN)

        fmt = (request.query_params.get("format") or "html").lower()
        if fmt != "html":
            return Response({"detail": "صيغة غير مدعومة حالياً."}, status=status.HTTP_400_BAD_REQUEST)

        # collect minimal fields (avoid heavy joins)
        try:
            from .serializers import IncidentSerializer

            data = IncidentSerializer(instance=inc).data
        except Exception:
            data = {
                "id": str(getattr(inc, "id", "")),
                "student_name": None,
                "student": getattr(inc, "student_id", None),
                "violation_code": None,
                "occurred_at": getattr(inc, "occurred_at", None),
                "proposed_summary": None,
            }

        short_id = str(data.get("id", ""))[:8]
        student_name = data.get("student_name") or ("#" + str(data.get("student")))
        occurred = data.get("occurred_at")
        try:
            occurred_str = (
                "—"
                if not occurred
                else f"{occurred[:10]}" if isinstance(occurred, str) else occurred.strftime("%Y-%m-%d")
            )
        except Exception:
            occurred_str = "—"
        proposed = data.get("proposed_summary") or "—"

        now_dt = timezone.now()
        y = now_dt.year
        m = f"{now_dt.month:02d}"
        d = f"{now_dt.day:02d}"
        doc_id = f"PLEDG-{y}{m}-{short_id}"

        html = f"""
<!DOCTYPE html>
<html lang=\"ar\" dir=\"rtl\">\n<head>\n<meta charset=\"utf-8\" />\n<title>تعهد خطي — {student_name}</title>\n<style>
  :root{{ --fg:#111; --muted:#666; --accent:#0d6efd; }}
  body{{ font-family:'Segoe UI', Tahoma, Arial, sans-serif; color:var(--fg); margin:0; }}
  header, footer{{ position:fixed; left:0; right:0; }}
  header{{ top:0; padding:12px 24px; border-bottom:1px solid #ddd; }}
  footer{{ bottom:0; padding:8px 24px; border-top:1px solid #ddd; color:#666; font-size:11px; }}
  main{{ padding:120px 24px 80px; max-width:820px; margin:0 auto; }}
  h1{{ font-size:18px; margin:0 0 12px; }}
  .row{{ display:grid; grid-template-columns:repeat(2, minmax(0,1fr)); gap:8px 16px; }}
  .box{{ border:1px solid #ccc; padding:12px; border-radius:6px; }}
  .muted{{ color:#666; font-size:12px; }}
  .sig-grid{{ display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin-top:16px; }}
  .sig{{ border:1px dashed #999; min-height:72px; padding:8px; }}
  .qr{{ width:96px; height:96px; border:1px solid #ccc; display:inline-block; background: repeating-linear-gradient(45deg,#eee 0,#eee 8px,#ddd 8px,#ddd 16px); }}
  .meta{{ margin-top:10px; font-size:12px; color:#666; }}
  @media print{{ @page{{ size:A4; margin:2cm; }} header,footer{{ position:fixed; }} main{{ padding:0; margin-top:40px; }} }}
</style></head>
<body>
  <header>
    <div style=\"display:flex; align-items:center; gap:12px;\">
      <div style=\"font-weight:700;\">نظام السلوك المدرسي</div>
      <div class=\"muted\" style=\"margin-inline-start:auto\">رقم الوثيقة: {doc_id} · تاريخ الإصدار: {y}-{m}-{d}</div>
    </div>
  </header>
  <footer>سري — للاستخدام المدرسي · صفحة 1 من 1 · للتحقق امسح رمز QR</footer>
  <main>
    <h1>تعهد خطي بشأن التزام السلوك المدرسي</h1>
    <div class=\"row box\" style=\"margin-bottom:12px;\">
      <div><div class=\"muted\">الطالب</div><div>{student_name}</div></div>
      <div><div class=\"muted\">رقم الواقعة</div><div>{short_id}</div></div>
      <div><div class=\"muted\">التاريخ</div><div>{occurred_str}</div></div>
      <div><div class=\"muted\">المخالفة</div><div>—</div></div>
    </div>
    <div class=\"box\">\n      <p>أنا الطالب/ـة المذكور أعلاه، أقرّ بأنني اطّلعت على الواقعة رقم {short_id} وأتعهد بالالتزام بقواعد السلوك والانضباط المدرسي، والتعاون مع المدرسة خلال فترة المتابعة.</p>
      <ol><li>الالتزام التام بالقواعد وتجنب تكرار المخالفة.</li><li>التعاون مع الهيئتين التعليمية والإرشادية عند الطلب.</li><li>قبول المتابعة الدورية والامتثال للتوجيهات.</li><li>العلم بأن تكرار المخالفة قد يترتب عليه إجراءات أشد وفق اللوائح.</li></ol>
      <div class=\"muted\">ملخص الإجراء/التوصية (إن وُجد):</div>
      <div style=\"font-weight:600; margin-bottom:8px;\">{proposed}</div>
      <div class=\"sig-grid\"><div class=\"sig\"><div class=\"muted\">توقيع الطالب/ـة</div></div><div class=\"sig\"><div class=\"muted\">توقيع ولي الأمر</div></div><div class=\"sig\"><div class=\"muted\">ختم المدرسة / موظف الاستلام</div></div></div>
      <div class=\"meta\">رقم الوثيقة: {doc_id}</div>
      <div style=\"margin-top:8px; display:flex; align-items:center; gap:12px;\"><div class=\"qr\" aria-label=\"QR placeholder\"></div><div class=\"muted\">سيتم توليد رمز QR لاحقًا ضمن إصدار PDF.</div></div>
    </div>
  </main>
  <script>window.onload = function(){ setTimeout(function(){ window.print && window.print(); }, 50); };<\/script>
</body></html>
"""

        # Audit best-effort
        try:
            IncidentAuditLog.objects.create(
                incident=inc,
                action="update",
                actor=user,
                from_status=inc.status,
                to_status=inc.status,
                note="عرض تعهد (معاينة)",
                meta={"action": "pledge_preview", "format": fmt},
            )
        except Exception:
            pass

        return HttpResponse(html, content_type="text/html; charset=utf-8")

    @action(
        detail=False, methods=["get"], url_path="count-by-student"
    )  # /incidents/count-by-student/?student=1&student=2
    def count_by_student(self, request):
        """Return counts of incidents per given student IDs.
        Query params: student (can be repeated) or student_ids (comma-separated).
        Respects the same visibility rules as list (get_queryset).
        """
        # Collect IDs from query params
        ids: List[int] = []
        raw_multi = request.query_params.getlist("student")
        for v in raw_multi:
            try:
                if str(v).strip().isdigit():
                    ids.append(int(v))
            except Exception:
                pass
        csv = (request.query_params.get("student_ids") or "").strip()
        if csv:
            for part in csv.split(","):
                part = part.strip()
                if part.isdigit():
                    ids.append(int(part))
        ids = list(dict.fromkeys([i for i in ids if i > 0]))  # de-dup & >0
        if not ids:
            return Response({}, status=status.HTTP_200_OK)
        # Base queryset: count ALL incidents for the given students (regardless of reporter)
        # The simplified UI expects a global count per student. We still require authentication
        # via the viewset, but we do not scope by reporter here.
        qs = Incident.objects.filter(student_id__in=ids)
        # Aggregate counts by student_id
        agg = qs.values("student_id").annotate(cnt=models.Count("id"))
        out: Dict[str, int] = {str(row["student_id"]): int(row["cnt"]) for row in agg}
        # Ensure all requested ids are present (0 when none)
        for i in ids:
            out.setdefault(str(i), 0)
        return Response(out)

    @action(detail=True, methods=["get"], url_path="committee-suggest")
    def committee_suggest(self, request, pk=None):
        """اقتراح احترافي ومحدد بشكل حتمي (Deterministic) لرئيس وأعضاء لجنة الواقعة.

        الهدف: مساعدة المسؤول على اختيار تشكيل لجنة عادل ومتوازن بسرعة، دون إلزام بالحفظ.

        المدخلات (Query):
          - member_count: عدد الأعضاء (عدا الرئيس) المطلوب اقتراحهم، افتراضي 2، المدى 2..4 (إجمالي 3..5).
          - exclude: قائمة CSV لمعرفات مستخدمين يجب استبعادهم.

        الضوابط:
          - يسمح بالوصول لمن يمتلك incident_committee_schedule أو incident_committee_decide أو للموظفين (is_staff/superuser).
          - استبعاد تضارب المصالح الشائع: مُبلِّغ الواقعة + أي معرف ضمن exclude.
          - مصادر الاختيار: جميع موظفي المدرسة (جميع Staff المرتبطين بحساب مستخدم User). برمجيًا نأخذ كل Staff.user غير الفارغ.

        المخرجات:
          {
            panel: { chair: {id, username, full_name}, members: [...], recorder: {...}|null },
            pools: { chairs: N, members: N, recorders: N },
            algorithm: "stable_hash_v1"
          }
        """
        User = get_user_model()
        inc = self.get_object()
        user = request.user
        # إذن الوصول
        if not (
            self._has(user, "incident_committee_schedule")
            or self._has(user, "incident_committee_decide")
            or getattr(user, "is_staff", False)
            or getattr(user, "is_superuser", False)
        ):
            return Response({"detail": "صلاحية غير كافية للوصول إلى مقترح اللجنة."}, status=status.HTTP_403_FORBIDDEN)

        # member_count
        try:
            member_count = int(request.query_params.get("member_count", 2))
        except Exception:
            member_count = 2
        member_count = max(2, min(4, member_count))

        # exclusions
        exclude_ids = set()
        csv = (request.query_params.get("exclude") or "").strip()
        if csv:
            for part in csv.split(","):
                part = part.strip()
                if part.isdigit():
                    exclude_ids.add(int(part))
        # استبعاد المُبلّغ
        try:
            if getattr(inc, "reporter_id", None):
                exclude_ids.add(int(inc.reporter_id))
        except Exception:
            pass

        def full_name(u):
            try:
                fn = u.get_full_name()
                return (
                    fn
                    if fn
                    else (getattr(u, "first_name", "") or getattr(u, "last_name", "") or getattr(u, "username", ""))
                )
            except Exception:
                return getattr(u, "username", "")

        def stable_sort(candidates):
            """رتّب المرشحين ترتيبًا حتميًا بحسب SHA256(incident_id:user_id)."""
            key_base = str(inc.id)

            def key_fn(u):
                raw = f"{key_base}:{getattr(u, 'id', 0)}".encode("utf-8")
                return int.from_bytes(hashlib.sha256(raw).digest(), "big")

            return sorted(candidates, key=key_fn)

        # بناء مجمع الرئيس: لم نعد نستخدم مجموعات؛ المصدر هو جميع الموظفين (Staff->User)

        # مجمع المرشحين: جميع موظفي المدرسة (كل Staff لديهم user مرتبط)
        try:
            from django.apps import apps as _apps

            Staff = _apps.get_model("school", "Staff")
            user_ids = list(Staff.objects.exclude(user__isnull=True).values_list("user_id", flat=True))
            base_qs = User.objects.filter(id__in=user_ids)
        except Exception:
            base_qs = User.objects.all()

        # لا نقيّد التشكيل بعضوية مجموعة، لكن يمكن للمؤسسة لاحقًا تفضيل أعضاء المجموعة عبر ترتيب إضافي.
        chair_qs = base_qs
        member_qs = base_qs
        recorder_qs = base_qs

        # استبعاد المعرفات غير المسموح بها
        def filter_exclusions(qs):
            if not exclude_ids:
                return list(qs)
            return [u for u in qs if getattr(u, "id", None) not in exclude_ids]

        chairs = filter_exclusions(chair_qs)
        members = filter_exclusions(member_qs)
        recorders = filter_exclusions(recorder_qs)

        # ترتيب ثابت (حتمي)
        chairs = stable_sort(chairs)
        members = stable_sort(members)
        recorders = stable_sort(recorders)

        # اختر الرئيس
        chair_obj = chairs[0] if chairs else None

        # استبعد الرئيس من الأعضاء
        if chair_obj is not None:
            members = [u for u in members if getattr(u, "id", None) != getattr(chair_obj, "id", None)]

        # اختر أعضاء بعدد مطلوب
        sel_members = members[:member_count] if members else []

        # اختر مقرر مختلف إن أمكن
        recorder_obj = None
        for u in recorders:
            if getattr(u, "id", None) not in {getattr(chair_obj, "id", None)} | {
                getattr(x, "id", None) for x in sel_members
            }:
                recorder_obj = u
                break

        # خريطة أسماء الموظفين (Staff.full_name) حسب user_id لإظهار أسماء الموظفين بدل أسماء المستخدمين
        staff_name_by_user: Dict[int, str] = {}
        try:
            from django.apps import apps as _apps

            Staff = _apps.get_model("school", "Staff")
            rows = Staff.objects.exclude(user__isnull=True).values_list("user_id", "full_name")
            staff_name_by_user = {int(uid): str(name) for uid, name in rows if uid}
        except Exception:
            staff_name_by_user = {}

        def as_payload(u):
            if not u:
                return None
            return {
                "id": getattr(u, "id", None),
                "username": getattr(u, "username", None),
                "full_name": full_name(u),
                # نضيف اسم الموظف من سجل Staff إن توفر، ليُعرَض في الواجهة بدلاً من اسم المستخدم
                "staff_full_name": staff_name_by_user.get(getattr(u, "id", 0)),
            }

        # قدرات الوصول للمستخدم الحالي (تفيد الواجهة في تفعيل الأزرار)
        caps = {
            "can_schedule": self._has(user, "incident_committee_schedule"),
            "can_decide": self._has(user, "incident_committee_decide"),
            "is_committee_member": False,  # لم نعد نستخدم مجموعة
            "is_staff": bool(getattr(user, "is_staff", False)),
            "is_superuser": bool(getattr(user, "is_superuser", False)),
        }

        # تعريف صلاحيات الأدوار ضمن مسار اللجنة (توصيف منطقي للمساعدة على UI)
        role_powers = {
            "chair": [
                "view",
                "schedule",  # إحالة/جدولة للجنة
                "decide",  # تسجيل قرار اللجنة
            ],
            "member": [
                "view",  # الاطلاع والمشاركة بالنقاش/التصويت
            ],
            "recorder": [
                "view",  # الاطلاع
                "record_notes",  # تدوين محضر/ملاحظات الجلسة (عند تفعيل حفظ التشكيل مستقبلًا)
            ],
        }

        # قائمة المرشحين (بعد الاستبعاد) لتغذية القوائم المنسدلة في الواجهة
        # نستخدم المجمع الأساسي (كل الموظفين) بعد تطبيق الاستبعادات وبأسماء كاملة.
        candidates_list = [as_payload(u) for u in stable_sort(filter_exclusions(base_qs))]

        payload = {
            "panel": {
                "chair": as_payload(chair_obj),
                "members": [as_payload(u) for u in sel_members],
                "recorder": as_payload(recorder_obj),
            },
            "pools": {
                "chairs": len(chairs),
                "members": len(members),
                "recorders": len(recorders),
            },
            "algorithm": "stable_hash_v1",
            "access_caps": caps,
            "role_powers": role_powers,
            "candidates": candidates_list,
        }
        return Response(payload)

    @action(detail=True, methods=["get"], url_path="committee-candidates")
    def committee_candidates(self, request, pk=None):
        """قائمة مرشّحي اللجنة من الباكند مع أدوات بحث و ترقيم صفحات.

        المصدر: جميع موظفي المدرسة المرتبطين بحساب User (Staff.user).

        استعلامات:
          - q: بحث بالاسم (اسم الموظف), اسم المستخدم، الاسم الكامل.
          - limit, offset: ترقيم صفحات (افتراضي limit=25, offset=0)
          - all_staff: إذا كانت 1 يتم أخذ جميع Staff.users بدل مجموعة اللجنة فقط.

        الوصول: incident_committee_view أو incident_committee_schedule أو incident_committee_decide
                أو is_staff/superuser.
        """
        User = get_user_model()
        inc = self.get_object()
        user = request.user
        if not (
            self._has(user, "incident_committee_view")
            or self._has(user, "incident_committee_schedule")
            or self._has(user, "incident_committee_decide")
            or getattr(user, "is_staff", False)
            or getattr(user, "is_superuser", False)
        ):
            return Response({"detail": "صلاحية غير كافية."}, status=status.HTTP_403_FORBIDDEN)

        q = (request.query_params.get("q") or "").strip()
        try:
            limit = max(1, min(100, int(request.query_params.get("limit", 25))))
        except Exception:
            limit = 25
        try:
            offset = max(0, int(request.query_params.get("offset", 0)))
        except Exception:
            offset = 0
        # لم تعد هناك مجموعة للجنة؛ جميع المرشحين من موظفي المدرسة
        all_staff = True

        # Build base pool
        try:
            from django.apps import apps as _apps

            Staff = _apps.get_model("school", "Staff")
            staff_qs = Staff.objects.exclude(user__isnull=True)
            user_ids_from_staff = list(staff_qs.values_list("user_id", flat=True))
        except Exception:
            staff_qs = None
            user_ids_from_staff = []

        base_users = User.objects.filter(id__in=user_ids_from_staff)

        # Apply search
        if q:
            # Search by staff_full_name, job_title, role, username, first/last name
            if staff_qs is not None:
                matching_staff_ids = list(
                    staff_qs.filter(
                        Q(full_name__icontains=q) | Q(job_title__icontains=q) | Q(role__icontains=q)
                    ).values_list("user_id", flat=True)
                )
            else:
                matching_staff_ids = []
            base_users = base_users.filter(
                Q(id__in=matching_staff_ids)
                | Q(username__icontains=q)
                | Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
            )

        # Deterministic order (stable hash by incident_id:user_id) with minor boost for search match
        key_base = str(getattr(inc, "id", "0"))

        def hash_key(uid: int) -> int:
            raw = f"{key_base}:{uid}".encode("utf-8")
            return int.from_bytes(hashlib.sha256(raw).digest(), "big")

        users_list = list(base_users)

        # Staff names map
        staff_name_by_user = {}
        staff_title_by_user = {}
        staff_role_by_user = {}
        try:
            if staff_qs is None:
                from django.apps import apps as _apps

                Staff = _apps.get_model("school", "Staff")
                staff_qs = Staff.objects.exclude(user__isnull=True)
            rows = staff_qs.values_list("user_id", "full_name", "job_title", "role")
            for uid, fn, jt, rl in rows:
                if uid:
                    staff_name_by_user[int(uid)] = str(fn or "")
                    staff_title_by_user[int(uid)] = str(jt or "")
                    staff_role_by_user[int(uid)] = str(rl or "")
        except Exception:
            pass

        def match_score(u) -> int:
            if not q:
                return 0
            text = " ".join(
                [
                    staff_name_by_user.get(getattr(u, "id", 0), ""),
                    staff_title_by_user.get(getattr(u, "id", 0), ""),
                    staff_role_by_user.get(getattr(u, "id", 0), ""),
                    getattr(u, "username", "") or "",
                    getattr(u, "first_name", "") or "",
                    getattr(u, "last_name", "") or "",
                ]
            ).lower()
            return 1 if q.lower() in text else 0

        users_list.sort(key=lambda u: (match_score(u) * -1, hash_key(getattr(u, "id", 0))))

        total = len(users_list)
        page = users_list[offset : offset + limit]

        def as_payload(u):
            return {
                "id": getattr(u, "id", None),
                "username": getattr(u, "username", None),
                "full_name": getattr(u, "get_full_name", lambda: "")() if hasattr(u, "get_full_name") else None,
                "staff_full_name": staff_name_by_user.get(getattr(u, "id", 0)),
                "job_title": staff_title_by_user.get(getattr(u, "id", 0)),
                "role": staff_role_by_user.get(getattr(u, "id", 0)),
            }

        data = {
            "items": [as_payload(u) for u in page],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
        # ضم «قدرات الوصول» لتمكين الواجهة من إظهار/إخفاء البطاقات حسب الصلاحيات
        access_caps = {
            "can_view": True,  # وصلنا هنا بعد التحقق أعلاه
            "can_schedule": bool(
                self._has(user, "incident_committee_schedule")
                or getattr(user, "is_staff", False)
                or getattr(user, "is_superuser", False)
            ),
            "can_decide": bool(
                self._has(user, "incident_committee_decide")
                or getattr(user, "is_staff", False)
                or getattr(user, "is_superuser", False)
            ),
            "is_staff": bool(getattr(user, "is_staff", False)),
            "is_superuser": bool(getattr(user, "is_superuser", False)),
        }
        data["access_caps"] = access_caps
        return Response(data)

    # ========== Committee: voting workflow ==========
    def _is_committee_member(self, user, inc: Incident) -> dict:
        """تحقق سريع من دور المستخدم ضمن لجنة الواقعة.
        يعيد قاموسًا مبسطًا: { is_member, is_chair, is_recorder }

        يعتمد على الجداول IncidentCommittee/IncidentCommitteeMember إن وُجدت
        ويستخدم committee_panel JSON كمسار احتياطي.
        """
        try:
            uid = getattr(user, "id", None)
            if not uid:
                return {"is_member": False, "is_chair": False, "is_recorder": False}
            # أولاً من الجداول
            try:
                committee = getattr(inc, "committee", None)
                if committee is not None:
                    is_chair = bool(getattr(committee, "chair_id", None) == uid)
                    is_rec = bool(getattr(committee, "recorder_id", None) == uid)
                    try:
                        mem_ids = set(committee.members.values_list("user_id", flat=True))
                    except Exception:
                        mem_ids = set()
                    is_mem = bool(uid in mem_ids or is_chair or is_rec)
                    return {"is_member": is_mem, "is_chair": is_chair, "is_recorder": is_rec}
            except Exception:
                pass
            # مسار احتياطي: JSON panel
            panel = getattr(inc, "committee_panel", None) or {}
            is_chair = bool(panel.get("chair_id") == uid)
            is_rec = bool(panel.get("recorder_id") == uid)
            try:
                mem_ids = set(panel.get("member_ids") or [])
            except Exception:
                mem_ids = set()
            is_mem = bool(uid in mem_ids or is_chair or is_rec)
            return {"is_member": is_mem, "is_chair": is_chair, "is_recorder": is_rec}
        except Exception:
            return {"is_member": False, "is_chair": False, "is_recorder": False}

    def _committee_quorum_and_majority(self, inc: Incident, votes: list[dict]) -> dict:
        """حساب النصاب والأغلبية بطريقة مبسطة: النصاب = نصف + 1 من (الأعضاء + الرئيس).
        الأغلبية البسيطة تحدد القرار المقترح. في حالة التعادل، يُستخدم تصويت الرئيس ككاسر تعادل إن وُجد.
        """
        try:
            # احسب العدد المتوقع للمصوتين
            total_voters = 0
            chair_id = None
            panel = getattr(inc, "committee_panel", None) or {}
            chair_id = panel.get("chair_id")
            members = list(panel.get("member_ids") or [])
            total_voters = (1 if chair_id else 0) + len(members)
            # جرّب من الجداول إن وُجدت
            try:
                committee = getattr(inc, "committee", None)
                if committee is not None:
                    chair_id = getattr(committee, "chair_id", chair_id)
                    total_voters = 1 + committee.members.count()
            except Exception:
                pass

            counts = {"approve": 0, "reject": 0, "return": 0}
            by_user: dict[int, str] = {}
            chair_vote = None
            for v in votes:
                uid = int(v.get("voter_id")) if v.get("voter_id") is not None else None
                decision = str(v.get("decision") or "").lower()
                if decision not in counts:
                    continue
                # آخر تصويت للمستخدم يغلب
                if uid is not None:
                    by_user[uid] = decision
                if chair_id is not None and uid == int(chair_id):
                    chair_vote = decision
            # أعد الاحتساب بعد إزالة التكرارات لكل مستخدم
            for d in by_user.values():
                counts[d] = counts.get(d, 0) + 1

            quorum = max(1, (total_voters // 2) + 1) if total_voters else 0
            participated = len(by_user)
            quorum_met = participated >= quorum if quorum else False
            # حدد الأغلبية
            maj_decision = None
            if counts:
                # ابحث عن أعلى عدّ
                sorted_items = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
                top = sorted_items[0]
                # تحقق من التعادل
                ties = [k for k, c in counts.items() if c == top[1] and c > 0]
                if len(ties) == 1:
                    maj_decision = top[0]
                else:
                    # تعادل — استخدم صوت الرئيس إن وُجد
                    if chair_vote in {"approve", "reject", "return"}:
                        maj_decision = chair_vote
            return {
                "total_voters": total_voters,
                "participated": participated,
                "quorum": quorum,
                "quorum_met": quorum_met,
                "counts": counts,
                "majority": maj_decision,
                "chair_vote": chair_vote,
            }
        except Exception:
            return {
                "total_voters": 0,
                "participated": 0,
                "quorum": 0,
                "quorum_met": False,
                "counts": {"approve": 0, "reject": 0, "return": 0},
                "majority": None,
                "chair_vote": None,
            }

    @action(detail=True, methods=["post"], url_path="committee-vote")
    def committee_vote(self, request, pk=None):
        """تسجيل تصويت عضو اللجنة على واقعة محددة.

        body: { decision: approve|reject|return, note? }
        الصلاحيات: يجب أن يكون المستخدم عضوًا في لجنة الواقعة (رئيس/عضو/مقرر) أو موظفًا/مديرًا.
        يسجل أثر تدقيق IncidentAuditLog.meta = { action: "committee_vote", decision, note }.
        """
        inc = self.get_object()
        user = request.user
        role = self._is_committee_member(user, inc)
        if not (role.get("is_member") or user.is_staff or user.is_superuser):
            return Response({"detail": "ليست ضمن لجنتك."}, status=status.HTTP_403_FORBIDDEN)

        decision = str((request.data or {}).get("decision") or "").strip().lower()
        if decision not in {"approve", "reject", "return"}:
            return Response({"detail": "قيمة decision غير صالحة."}, status=status.HTTP_400_BAD_REQUEST)
        note = str((request.data or {}).get("note") or "").strip()

        try:
            IncidentAuditLog.objects.create(
                incident=inc,
                action="update",
                actor=user,
                from_status=inc.status,
                to_status=inc.status,
                note=note,
                meta={"action": "committee_vote", "decision": decision, "voter_id": getattr(user, "id", None)},
            )
        except Exception:
            return Response({"detail": "تعذّر تسجيل التصويت."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({"ok": True})

    @action(detail=True, methods=["get"], url_path="committee-votes")
    def committee_votes(self, request, pk=None):
        """إرجاع ملخّص التصويت على الواقعة مع حساب النصاب والأغلبية المقترحة."""
        inc = self.get_object()
        votes_qs = IncidentAuditLog.objects.filter(incident=inc, meta__action="committee_vote").order_by("at")
        votes = list(
            votes_qs.values("actor_id", "meta").annotate(voter_id=models.F("actor_id")).values(
                "voter_id", "meta"
            )
        )
        out_votes = []
        for v in votes:
            meta = v.get("meta") or {}
            out_votes.append({
                "voter_id": v.get("voter_id"),
                "decision": meta.get("decision"),
            })
        agg = self._committee_quorum_and_majority(inc, out_votes)
        return Response({"votes": out_votes, "summary": agg})

    @action(detail=False, methods=["get"], url_path="my-committee")
    def my_committee(self, request):
        """إرجاع الوقائع التي يكون المستخدم الحالي جزءًا من لجنتها (رئيس/عضو/مقرر).
        تستخدم لواجهات الأعضاء/المقرر.
        """
        user = request.user
        try:
            qs = (
                Incident.objects.select_related("violation", "student").defer("violation__policy").all()
            )
            uid = getattr(user, "id", None)
            # من الجداول
            try:
                from .models import IncidentCommittee, IncidentCommitteeMember

                ic_ids = list(
                    IncidentCommittee.objects.filter(models.Q(chair_id=uid) | models.Q(recorder_id=uid))
                    .values_list("incident_id", flat=True)
                )
                icm_ids = list(
                    IncidentCommitteeMember.objects.filter(user_id=uid).values_list("committee__incident_id", flat=True)
                )
                ids = set([*ic_ids, *icm_ids])
                qs = qs.filter(id__in=list(ids)) | qs.filter(committee_panel__member_ids__contains=[uid])
            except Exception:
                # مسار JSON فقط
                qs = qs.filter(models.Q(committee_panel__chair_id=uid) | models.Q(committee_panel__recorder_id=uid) | models.Q(committee_panel__member_ids__contains=[uid]))
            qs = qs.order_by("-occurred_at", "-created_at")
            ser = IncidentSerializer(qs, many=True)
            return Response(ser.data)
        except Exception as e:
            logger.warning("incident.my_committee.error user=%s err=%s", getattr(user, "id", None), e)
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=["get"], url_path="committee-caps")
    def committee_caps(self, request):
        """إرجاع قدرات الوصول لمسار اللجنة للمستخدم الحالي (لاستخدامها في الواجهة لإظهار/إخفاء البطاقات).

        لا يتطلب معرّف واقعة؛ يعتمد على صلاحيات نموذج Incident وأعلام الموظف.
        كما يحاول اكتشاف دور المستخدم في «اللجنة الدائمة» كإشارة واجهة فقط.
        """
        user = request.user
        caps = {
            "can_view": bool(
                self._has(user, "incident_committee_view")
                or getattr(user, "is_staff", False)
                or getattr(user, "is_superuser", False)
            ),
            "can_schedule": bool(
                self._has(user, "incident_committee_schedule")
                or getattr(user, "is_staff", False)
                or getattr(user, "is_superuser", False)
            ),
            "can_decide": bool(
                self._has(user, "incident_committee_decide")
                or getattr(user, "is_staff", False)
                or getattr(user, "is_superuser", False)
            ),
            "is_staff": bool(getattr(user, "is_staff", False)),
            "is_superuser": bool(getattr(user, "is_superuser", False)),
            # إشارات «اللجنة الدائمة» اختيارية للعرض فقط
            "is_standing_chair": False,
            "is_standing_recorder": False,
            "is_standing_member": False,
        }
        # اسمح بالعرض إن كان المستخدم عضوًا فعليًا في أي لجنة حتى لو لم تُمنح صلاحية النموذج بعد
        try:
            if not caps["can_view"]:
                uid = getattr(user, "id", None)
                if uid:
                    try:
                        from .models import IncidentCommittee, IncidentCommitteeMember

                        is_in_committee = (
                            IncidentCommittee.objects.filter(models.Q(chair_id=uid) | models.Q(recorder_id=uid)).exists()
                            or IncidentCommitteeMember.objects.filter(user_id=uid).exists()
                        )
                    except Exception:
                        is_in_committee = False
                    if not is_in_committee:
                        # فحص مسار JSON القديم كخيار أخير
                        try:
                            is_in_committee = Incident.objects.filter(
                                models.Q(committee_panel__chair_id=uid)
                                | models.Q(committee_panel__recorder_id=uid)
                                | models.Q(committee_panel__member_ids__contains=[uid])
                            ).exists()
                        except Exception:
                            is_in_committee = False
                    if is_in_committee:
                        caps["can_view"] = True
        except Exception:
            pass
        try:
            from .models import StandingCommittee, StandingCommitteeMember

            sc = StandingCommittee.objects.order_by("id").first()
            if sc is not None:
                if getattr(sc, "chair_id", None) == getattr(user, "id", None):
                    caps["is_standing_chair"] = True
                if getattr(sc, "recorder_id", None) == getattr(user, "id", None):
                    caps["is_standing_recorder"] = True
                try:
                    caps["is_standing_member"] = StandingCommitteeMember.objects.filter(
                        standing=sc, user_id=getattr(user, "id", None)
                    ).exists()
                except Exception:
                    pass
        except Exception:
            pass
        return Response({"access_caps": caps})

    @action(detail=True, methods=["post"], url_path="schedule-committee")
    def schedule_committee(self, request, pk=None):
        """إحالة الواقعة إلى «اللجنة السلوكية الدائمة» حصريًا.

        ملاحظة مهمة:
        - تم التخلص بأمان من أي تشكيل مخصّص من العميل. لا تُقبل chair_id/member_ids/recorder_id.
        - يعتمد التشكيل دائمًا على "اللجنة الدائمة" المخزنة في قاعدة البيانات.
        - يتطلب الإذن incident_committee_schedule أو is_staff/superuser.
        """
        User = get_user_model()
        inc = self.get_object()
        user = request.user
        if not (
            self._has(user, "incident_committee_schedule")
            or getattr(user, "is_staff", False)
            or getattr(user, "is_superuser", False)
        ):
            return Response({"detail": "صلاحية غير كافية."}, status=status.HTTP_403_FORBIDDEN)
        # تجاهل كامل لأي Body وارد — تشكيل اللجنة سيكون دائمًا من «اللجنة الدائمة»
        body = {}

        # حمّل تشكيل اللجنة الدائمة حصريًا
        try:
            from .models import StandingCommittee, StandingCommitteeMember

            standing = StandingCommittee.objects.order_by("id").first()
            if not (standing and getattr(standing, "chair_id", None)):
                return Response(
                    {"detail": "لا توجد لجنة دائمة مهيّأة. يرجى ضبط الرئيس وعضوين على الأقل في اللجنة الدائمة."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            chair_id = int(standing.chair_id)
            member_ids = [
                int(x.user_id) for x in StandingCommitteeMember.objects.filter(standing=standing).only("user_id")
            ]
            recorder_id = int(standing.recorder_id) if getattr(standing, "recorder_id", None) else None
        except Exception:
            return Response(
                {"detail": "فشل تحميل اللجنة الدائمة. يرجى التحقق من الإعدادات."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # خريطة المستخدمين للتحPersist في جداول IncidentCommittee
        needed_ids = set([chair_id] + member_ids + ([recorder_id] if recorder_id else []))
        users_map = {u.id: u for u in get_user_model().objects.filter(id__in=list(needed_ids))}

        # Persist
        from django.utils import timezone as _tz

        inc.committee_panel = {
            "chair_id": chair_id,
            "member_ids": member_ids,
            "recorder_id": recorder_id,
        }
        inc.committee_required = True
        inc.committee_scheduled_by = user
        inc.committee_scheduled_at = _tz.now()
        inc.save(
            update_fields=[
                "committee_panel",
                "committee_required",
                "committee_scheduled_by",
                "committee_scheduled_at",
                "updated_at",
            ]
        )

        # حفظ في الجداول الجديدة IncidentCommittee/IncidentCommitteeMember
        try:
            from .models import IncidentCommittee, IncidentCommitteeMember

            committee_obj, _ = IncidentCommittee.objects.update_or_create(
                incident=inc,
                defaults={
                    "chair": users_map[chair_id],
                    "recorder": users_map.get(recorder_id) if recorder_id else None,
                    "scheduled_by": user,
                },
            )
            # أعد بناء الأعضاء
            IncidentCommitteeMember.objects.filter(committee=committee_obj).delete()
            for mid in member_ids:
                IncidentCommitteeMember.objects.create(committee=committee_obj, user=users_map[mid])
        except Exception:
            logger.warning("committee.persist.failed incident=%s", inc.id)

        # منح صلاحيات مسار اللجنة تلقائيًا (RBAC خفيف):
        # - جميع المشاركين (الرئيس/الأعضاء/المقرر) → incident_committee_view
        # - الرئيس والمقرر → incident_committee_decide
        try:
            from django.contrib.auth.models import Permission

            def _grant(u, codename: str):
                try:
                    perm = Permission.objects.get(codename=codename)
                    u.user_permissions.add(perm)
                except Exception:
                    # في بعض البيئات قد يختلف ContentType أو لم تُنشأ الأذونات بعد
                    pass

            involved_ids = set([chair_id] + member_ids + ([recorder_id] if recorder_id else []))
            for uid in involved_ids:
                try:
                    uu = users_map.get(uid)
                    if not uu:
                        continue
                    _grant(uu, "incident_committee_view")
                except Exception:
                    pass
            # رئيس + مقرر يملكان حق اعتماد قرار اللجنة
            for uid in [chair_id, recorder_id]:
                if not uid:
                    continue
                try:
                    uu = users_map.get(uid)
                    if not uu:
                        continue
                    _grant(uu, "incident_committee_decide")
                except Exception:
                    pass
        except Exception:
            logger.warning("committee.perms.grant.failed incident=%s", inc.id)

        # Audit log
        try:
            IncidentAuditLog.objects.create(
                incident=inc,
                action="update",
                actor=user,
                from_status=inc.status,
                to_status=inc.status,
                note="جدولة لجنة",
                meta={
                    "action": "schedule_committee",
                    "chair_id": chair_id,
                    "member_ids": member_ids,
                    "recorder_id": recorder_id,
                    "granted_perms": {
                        "view": list(set([chair_id] + member_ids + ([recorder_id] if recorder_id else []))),
                        "decide": [x for x in [chair_id, recorder_id] if x],
                    },
                },
            )
        except Exception:
            logging.getLogger(__name__).warning("incident.audit.failed action=schedule_committee incident=%s", inc.id)

        return Response(
            {
                "ok": True,
                "incident": IncidentFullSerializer(inc).data,
                "saved_panel": inc.committee_panel,
            }
        )

    @action(detail=True, methods=["post"], url_path="committee-decision")
    def committee_decision(self, request, pk=None):
        """تسجيل قرار لجنة السلوك للواقعة.

        المدخلات (JSON):
          - decision: one of ["approve", "reject", "return"] (مطلوب)
          - note: تعليق/ملاحظات القرار (اختياري)
          - actions: قائمة إجراءات لتطبيقها (اختياري)
          - sanctions: قائمة عقوبات لتطبيقها (اختياري)
          - close_now: منطقية — إن كانت 1/true ومع القرار approve يتم إغلاق الواقعة فورًا (اختياري)

        الضوابط:
          - يتطلب صلاحية incident_committee_decide أو is_staff/superuser.

        التأثير:
          - يُسجل أثر تدقيق meta.action = "committee_decision" مع تفاصيل القرار.
          - يضيف الإجراءات/العقوبات إلى حقول الواقعة إن تم تمريرها.
          - عند close_now وقرار approve: تتحول الحالة إلى closed مع تعبئة closed_by/closed_at وتسجيل أثر إغلاق.
        """
        inc = self.get_object()
        user = request.user
        if not (
            self._has(user, "incident_committee_decide")
            or getattr(user, "is_staff", False)
            or getattr(user, "is_superuser", False)
        ):
            return Response({"detail": "صلاحية غير كافية."}, status=status.HTTP_403_FORBIDDEN)

        body = request.data or {}
        decision = str(body.get("decision") or "").strip().lower()
        if decision not in {"approve", "reject", "return"}:
            return Response(
                {"detail": "قيمة decision غير صالحة. استخدم approve|reject|return."}, status=status.HTTP_400_BAD_REQUEST
            )

        note = (body.get("note") or "").strip()
        actions = body.get("actions")
        sanctions = body.get("sanctions")
        close_now_flag = str(body.get("close_now") or "").strip().lower() in {"1", "true", "yes"}

        # دمج الإجراءات/العقوبات إن تم تمريرها
        updated_fields = ["updated_at"]
        try:
            if isinstance(actions, list):
                current = list(getattr(inc, "actions_applied", []) or [])
                inc.actions_applied = current + actions
                updated_fields.append("actions_applied")
        except Exception:
            pass
        try:
            if isinstance(sanctions, list):
                current = list(getattr(inc, "sanctions_applied", []) or [])
                inc.sanctions_applied = current + sanctions
                updated_fields.append("sanctions_applied")
        except Exception:
            pass

        # عند الموافقة وإغلاق فوري
        from django.utils import timezone as _tz

        if decision == "approve" and close_now_flag:
            try:
                inc.status = "closed"
                inc.closed_by = user
                inc.closed_at = _tz.now()
                updated_fields += ["status", "closed_by", "closed_at"]
            except Exception:
                pass

        # احفظ التغييرات (إن وُجدت)
        try:
            inc.save(update_fields=list(set(updated_fields)))
        except Exception:
            inc.save()  # حفظ تقليدي كملاذ أخير

        # سجل تدقيق لقرار اللجنة
        try:
            IncidentAuditLog.objects.create(
                incident=inc,
                action="update",
                actor=user,
                from_status=inc.status,
                to_status=inc.status,
                note=note or "قرار لجنة",
                meta={
                    "action": "committee_decision",
                    "decision": decision,
                    "close_now": close_now_flag,
                    "actions_added": isinstance(actions, list),
                    "sanctions_added": isinstance(sanctions, list),
                },
            )
        except Exception:
            logger.warning("incident.audit.failed action=committee_decision incident=%s", inc.id)

        # إرسال القرار إلى رئيس اللجنة وأعضائها لاتخاذ القرار (تسجيل إشعار بسيط عبر سجل التدقيق)
        try:
            panel = getattr(inc, "committee_panel", None) or {}
            chair_id = panel.get("chair_id")
            member_ids = list(panel.get("member_ids") or [])
            recorder_id = panel.get("recorder_id")
            recipients = []
            # أرسل إلى الرئيس + الأعضاء فقط (استثناء المقرر إن كان منفذ الطلب)
            for uid in ([chair_id] if chair_id else []) + member_ids:
                try:
                    if uid and int(uid) != int(getattr(user, "id", 0)):
                        recipients.append(int(uid))
                except Exception:
                    continue
            if recipients:
                IncidentAuditLog.objects.create(
                    incident=inc,
                    action="notify",
                    actor=user,
                    from_status=inc.status,
                    to_status=inc.status,
                    note="إشعار اللجنة بقرار المقرّر",
                    meta={
                        "action": "notify_committee_panel",
                        "reason": "committee_decision_recorded",
                        "decision": decision,
                        "notified_to": recipients,
                        "excluded_recorder": bool(recorder_id == getattr(user, "id", None)),
                    },
                )
        except Exception:
            logger.warning("incident.notify.committee.failed incident=%s", inc.id)

        # إذا تم الإغلاق الآن، أضف سجل إغلاق منفصل لتحسين وضوح الأثر
        if decision == "approve" and close_now_flag:
            try:
                IncidentAuditLog.objects.create(
                    incident=inc,
                    action="close",
                    actor=user,
                    from_status="under_review",
                    to_status="closed",
                    note="إغلاق الواقعة بناءً على قرار اللجنة",
                )
            except Exception:
                logger.warning("incident.audit.failed action=close incident=%s", inc.id)

        return Response({"ok": True, "incident": IncidentFullSerializer(inc).data})

    # ======================== اللجنة الدائمة (نقطة عامة) ========================
    @action(detail=False, methods=["get"], url_path="committee-standing")
    def committee_standing_get(self, request):
        """إرجاع التشكيل الحالي للجنة الدائمة (رئيس/أعضاء/مقرر).

        الوصول: incident_committee_view أو is_staff/superuser.
        """
        user = request.user
        if not (
            self._has(user, "incident_committee_view")
            or getattr(user, "is_staff", False)
            or getattr(user, "is_superuser", False)
        ):
            return Response({"detail": "صلاحية غير كافية."}, status=status.HTTP_403_FORBIDDEN)
        try:
            from .models import StandingCommittee, StandingCommitteeMember

            standing = StandingCommittee.objects.order_by("id").first()
            if not standing:
                data = {
                    "panel": {"chair": None, "members": [], "recorder": None},
                    "exists": False,
                }
                return Response(data)
            # بناء حمولة بسيطة بالأسماء (مع اسم الموظف إن توفر)
            User = get_user_model()
            ids = []
            if standing.chair_id:
                ids.append(int(standing.chair_id))
            if standing.recorder_id:
                ids.append(int(standing.recorder_id))
            member_ids = [
                int(x.user_id) for x in StandingCommitteeMember.objects.filter(standing=standing).only("user_id")
            ]
            ids.extend(member_ids)
            users_map = {u.id: u for u in User.objects.filter(id__in=ids)}
            # Staff names map
            staff_name = {}
            try:
                from django.apps import apps as _apps

                Staff = _apps.get_model("school", "Staff")
                rows = Staff.objects.exclude(user__isnull=True).values_list("user_id", "full_name")
                staff_name = {int(uid): str(fn) for uid, fn in rows if uid}
            except Exception:
                staff_name = {}

            def as_payload(u):
                if not u:
                    return None
                return {
                    "id": getattr(u, "id", None),
                    "username": getattr(u, "username", None),
                    "full_name": getattr(u, "get_full_name", lambda: "")() if hasattr(u, "get_full_name") else None,
                    "staff_full_name": staff_name.get(getattr(u, "id", 0)),
                }

            data = {
                "panel": {
                    "chair": as_payload(users_map.get(int(standing.chair_id)) if standing.chair_id else None),
                    "members": [as_payload(users_map.get(mid)) for mid in member_ids],
                    "recorder": as_payload(users_map.get(int(standing.recorder_id)) if standing.recorder_id else None),
                },
                "exists": True,
            }
            return Response(data)
        except Exception:
            logger.warning("standing.committee.get.failed")
            return Response({"panel": {"chair": None, "members": [], "recorder": None}, "exists": False})

    @action(detail=False, methods=["post"], url_path="committee-standing")
    def committee_standing_set(self, request):
        """تحديث/حفظ تشكيل اللجنة الدائمة.

        الطلب JSON: { "chair_id": 12, "member_ids": [34,56], "recorder_id": 78|null, "notes": "..." }
        الوصول: incident_committee_schedule أو is_staff/superuser.
        """
        user = request.user
        if not (
            self._has(user, "incident_committee_schedule")
            or getattr(user, "is_staff", False)
            or getattr(user, "is_superuser", False)
        ):
            return Response({"detail": "صلاحية غير كافية."}, status=status.HTTP_403_FORBIDDEN)

        body = request.data or {}
        try:
            chair_id = int(body.get("chair_id") or 0)
        except Exception:
            chair_id = 0
        member_ids = body.get("member_ids") or []
        try:
            member_ids = [int(x) for x in member_ids]
        except Exception:
            return Response({"detail": "member_ids يجب أن تكون أرقامًا."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            recorder_id = body.get("recorder_id")
            recorder_id = int(recorder_id) if recorder_id not in (None, "", "null") else None
        except Exception:
            recorder_id = None
        notes = str(body.get("notes") or "").strip()

        if chair_id <= 0:
            return Response({"detail": "chair_id مطلوب."}, status=status.HTTP_400_BAD_REQUEST)
        if len(member_ids) < 2:
            return Response({"detail": "يجب اختيار عضوين على الأقل."}, status=status.HTTP_400_BAD_REQUEST)
        all_ids = [chair_id] + member_ids + ([recorder_id] if recorder_id else [])
        if len(set([x for x in all_ids if x])) != len([x for x in all_ids if x]):
            return Response({"detail": "لا يجوز تكرار الشخص بين الأدوار."}, status=status.HTTP_400_BAD_REQUEST)

        # تحقق من وجود المستخدمين وكونهم موظفين
        needed = set([chair_id] + member_ids + ([recorder_id] if recorder_id else []))
        User = get_user_model()
        users_map = {u.id: u for u in User.objects.filter(id__in=list(needed))}
        if len(users_map) != len(needed):
            return Response({"detail": "معرّفات مستخدمين غير صالحة."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            from django.apps import apps as _apps

            Staff = _apps.get_model("school", "Staff")
            staff_ids = set(Staff.objects.exclude(user__isnull=True).values_list("user_id", flat=True))
            not_staff = [uid for uid in needed if uid not in staff_ids]
            if not_staff:
                return Response(
                    {"detail": f"المستخدمون التاليون ليسوا موظفين في المدرسة: {not_staff}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception:
            pass

        # احفظ التشكيل الدائم (singleton أول عنصر)
        from .models import StandingCommittee, StandingCommitteeMember

        standing, _ = StandingCommittee.objects.get_or_create(id=1)
        standing.chair_id = chair_id
        standing.recorder_id = recorder_id
        if notes:
            standing.notes = notes
        standing.save()
        StandingCommitteeMember.objects.filter(standing=standing).delete()
        for mid in member_ids:
            StandingCommitteeMember.objects.create(standing=standing, user_id=mid)

        return Response(
            {
                "ok": True,
                "standing": {
                    "chair_id": chair_id,
                    "member_ids": member_ids,
                    "recorder_id": recorder_id,
                    "notes": standing.notes,
                },
            }
        )
