from __future__ import annotations

from typing import List

from django.contrib.auth import password_validation
from django.contrib.auth.models import Permission
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from ..models import Staff, TeachingAssignment, Wing, ApprovalRequest, TaskLog
from django.db.models import Q


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@never_cache
def me(request: Request):
    from apps.common.roles import normalize_roles, pick_primary_route  # type: ignore

    user = request.user
    # Roles from Django groups
    roles_set = set(user.groups.values_list("name", flat=True))  # type: ignore
    # Also include Staff.role if linked (some deployments store role code here)
    staff_obj = None
    try:
        staff_obj = Staff.objects.filter(user=user).only("id", "role").first()
        if staff_obj and staff_obj.role:
            roles_set.add(staff_obj.role)
    except Exception:
        staff_obj = None
    # Derive 'wing_supervisor' if this staff supervises any wings (even if not in group)
    try:
        if staff_obj and Wing.objects.filter(supervisor=staff_obj).exists():
            roles_set.add("wing_supervisor")
    except Exception:
        pass
    # Normalize roles to canonical codes
    roles_norm = normalize_roles(roles_set)

    # Determine if the user is a teacher with actual teaching assignments (has timetable classes)
    # Also get full_name from Staff table (Arabic name)
    has_teaching_assignments = False
    staff_full_name = None
    try:
        staff = Staff.objects.filter(user=user).first()
        if staff:
            staff_full_name = staff.full_name
            # Treat as teacher if actual assignments exist, regardless of group naming
            if TeachingAssignment.objects.filter(teacher=staff).exists():
                has_teaching_assignments = True
                roles_norm.add("teacher")
    except Exception:
        has_teaching_assignments = False

    # Permissions as "app_label.codename"
    perms: List[str] = [f"{p.content_type.app_label}.{p.codename}" for p in Permission.objects.filter(user=user)]
    # Also include group-granted permissions
    group_perms_qs = Permission.objects.filter(group__user=user).values_list("content_type__app_label", "codename")
    perms += [f"{app}.{code}" for app, code in group_perms_qs]
    # Deduplicate
    perms = sorted(set(perms))

    # Capabilities derived from roles for frontend UI gating (non-authoritative; server enforces separately)
    role_set = set(roles_norm)
    can_manage_timetable = bool(
        user.is_superuser or role_set.intersection({"principal", "academic_deputy", "timetable_manager"})
    )
    # Discipline capabilities (UI gating; server enforces separately per endpoint)
    is_principal = "principal" in role_set
    is_vice = "academic_deputy" in role_set or "vice_principal" in role_set
    is_d_l1 = "discipline_l1" in role_set or "homeroom" in role_set
    is_d_l2 = "discipline_l2" in role_set
    is_exams = "exams" in role_set or "exams_officer" in role_set
    is_nurse = "nurse" in role_set
    is_counselor = "counselor" in role_set

    caps = {
        "can_manage_timetable": can_manage_timetable,
        "can_view_general_timetable": True,  # all authenticated users may view; templates may still gate by staff
        "can_take_attendance": bool("teacher" in role_set),
        # Discipline
        "discipline_l1": bool(is_d_l1),
        "discipline_l2": bool(is_d_l2 or is_principal or is_vice),
        # Exams governance
        "exams_manage": bool(is_exams or is_principal or is_vice),
        # Health privacy
        "health_can_view_masked": bool(is_counselor or is_nurse or is_principal or is_vice),
        # سياسة صحية صارمة: فك الإخفاء للممرض فقط
        "health_can_unmask": bool(is_nurse),
        # Approvals (dual control)
        "can_propose_irreversible": bool(is_d_l2 or is_exams or is_vice or is_principal),
        "can_approve_irreversible": bool(is_vice or is_principal),
    }

    primary_route = pick_primary_route(role_set)

    # Optional cumulative history ribbon per user (lightweight, role-aware)
    history = None
    try:
        if staff_obj:
            from ..models import AttendanceRecord  # type: ignore

            qs = AttendanceRecord.objects.filter(teacher_id=staff_obj.id)
            total_entries = qs.count()
            first_date = qs.order_by("date").values_list("date", flat=True).first()
            last_date = qs.order_by("-date").values_list("date", flat=True).first()
            active_days = qs.values("date").distinct().count()
            by_status = {
                "present": qs.filter(status="present").count(),
                "late": qs.filter(status="late").count(),
                "absent": qs.filter(status="absent").count(),
                "excused": qs.filter(status="excused").count(),
                "runaway": qs.filter(status="runaway").count(),
            }
            history = {
                "scope": "teacher" if has_teaching_assignments else "staff",
                "total_entries": int(total_entries),
                "active_days": int(active_days),
                "first_date": first_date.isoformat() if first_date else None,
                "last_date": last_date.isoformat() if last_date else None,
                "by_status": by_status,
            }
    except Exception:
        history = None

    # سياسة عرض الأسماء: نُفضِّل دائمًا اسم الموظف الكامل من Staff إن وُجد، ثم الاسم الكامل للمستخدم، ثم اسم المستخدم
    display_name = staff_full_name or user.get_full_name() or user.username

    data = {
        "id": user.id,
        "username": user.username,
        "full_name": display_name,  # إبقاء التوافق مع الفرونت اند: full_name يُعيد الاسم الأفضل عرضًا
        "staff_full_name": staff_full_name,  # إرجاع الاسم من Staff صراحةً عند الحاجة
        "display_name": display_name,  # مفتاح صريح لسياسة العرض الموحّدة
        "is_superuser": user.is_superuser,
        "is_staff": user.is_staff,
        "roles": sorted(roles_norm),
        "permissions": perms,
        "hasTeachingAssignments": has_teaching_assignments,
        "capabilities": caps,
        "primary_route": primary_route,
        "history": history,
    }
    return JsonResponse(data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@never_cache
def create_approval_request(request: Request) -> Response:
    """إنشاء طلب موافقة لإجراء حساس.

    الحقول المتوقعة:
    - resource_type (str)
    - resource_id (str)
    - action (str)
    - irreversible (bool, اختياري)
    - impact (str, اختياري)
    - justification (str, اختياري)
    - payload (JSON, اختياري)
    """
    user = request.user
    body = request.data or {}

    resource_type = (body.get("resource_type") or "").strip()
    resource_id = (body.get("resource_id") or "").strip()
    action = (body.get("action") or "").strip()
    irreversible = bool(body.get("irreversible") or False)
    impact = (body.get("impact") or "").strip()
    justification = (body.get("justification") or "").strip()
    payload = body.get("payload")

    # Basic validation
    if not resource_type or not resource_id or not action:
        return Response({"detail": "حقول ناقصة: resource_type/resource_id/action"}, status=status.HTTP_400_BAD_REQUEST)

    # Minimal role checks (authoritative enforcement should exist on resource endpoints as well)
    roles = set(user.groups.values_list("name", flat=True))  # type: ignore
    # Include potential Staff.role
    try:
        staff = Staff.objects.filter(user=user).only("role").first()
        if staff and staff.role:
            roles.add(staff.role)
    except Exception:
        pass
    is_principal = "principal" in roles
    is_vice = "academic_deputy" in roles or "vice_principal" in roles
    is_d_l2 = "discipline_l2" in roles
    is_exams = "exams" in roles or "exams_officer" in roles

    if irreversible and not (is_d_l2 or is_exams or is_vice or is_principal or user.is_superuser):
        return Response({"detail": "ليست لديك صلاحية طلب إجراء غير قابل للعكس"}, status=status.HTTP_403_FORBIDDEN)

    # Idempotency/Dedupe window: تجنّب تكرار طلبات متطابقة خلال 10 دقائق
    try:
        from django.utils import timezone

        window_minutes = 10
        since = timezone.now() - timezone.timedelta(minutes=window_minutes)
        existing = (
            ApprovalRequest.objects.filter(
                proposed_by=user,
                resource_type=resource_type,
                resource_id=str(resource_id),
                action=action,
                status="pending",
                created_at__gte=since,
            )
            .order_by("-id")
            .first()
        )
        if existing:
            return Response({"id": existing.id, "status": existing.status, "detail": "duplicate_reused"})
    except Exception:
        # Non-blocking: continue to create
        pass

    obj = ApprovalRequest.objects.create(
        resource_type=resource_type,
        resource_id=str(resource_id),
        action=action,
        irreversible=irreversible,
        impact=impact or ("high" if irreversible else "medium"),
        justification=justification,
        payload=payload if isinstance(payload, (dict, list)) else None,
        proposed_by=user,
    )
    # سجل مهمة لإنشاء طلب موافقة
    try:
        TaskLog.objects.create(
            resource_type="approval",
            resource_id=str(obj.id),
            action="approval.request",
            status="open",
            actor=user,
            message=f"طلب موافقة: {action}",
            payload={
                "resource_type": resource_type,
                "resource_id": str(resource_id),
                "impact": obj.impact,
                "irreversible": obj.irreversible,
            },
        )
    except Exception:
        pass
    return Response({"id": obj.id, "status": obj.status}, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@never_cache
def approve_approval_request(request: Request, id: int) -> Response:
    """اعتماد طلب موافقة (الموافَق يظل بحاجة لتنفيذ حسب نوع المورد)."""
    user = request.user
    try:
        obj = ApprovalRequest.objects.get(id=id)
    except ApprovalRequest.DoesNotExist:
        return Response({"detail": "العنصر غير موجود"}, status=status.HTTP_404_NOT_FOUND)

    roles = set(user.groups.values_list("name", flat=True))  # type: ignore
    try:
        staff = Staff.objects.filter(user=user).only("role").first()
        if staff and staff.role:
            roles.add(staff.role)
    except Exception:
        pass

    is_principal = "principal" in roles
    is_vice = "academic_deputy" in roles or "vice_principal" in roles
    if not (is_principal or is_vice or user.is_superuser):
        return Response({"detail": "لا تملك صلاحية الاعتماد"}, status=status.HTTP_403_FORBIDDEN)

    # منع الموافقة الذاتية: نفس من قدَّم الطلب لا يستطيع اعتماده
    if obj.proposed_by_id and obj.proposed_by_id == user.id and not user.is_superuser:
        return Response({"detail": "لا يمكن لمقدّم الطلب اعتماده بنفسه"}, status=status.HTTP_403_FORBIDDEN)

    # السماح بالاعتماد فقط من حالة pending (وليس rejected/approved/executed)
    if obj.status != "pending":
        return Response(
            {"detail": "لا يمكن اعتماد هذا الطلب إلا إذا كانت حالته قيد الانتظار"}, status=status.HTTP_400_BAD_REQUEST
        )

    obj.status = "approved"
    obj.approved_by = user
    obj.save(update_fields=["status", "approved_by", "updated_at"])
    # سجل مهمة لاعتماد الطلب
    try:
        TaskLog.objects.create(
            resource_type="approval",
            resource_id=str(obj.id),
            action="approval.approved",
            status="done",
            actor=user,
            message=f"تم اعتماد طلب: {obj.action}",
            payload={"proposed_by": getattr(obj.proposed_by, "id", None)},
        )
    except Exception:
        pass
    return Response({"detail": "تم الاعتماد", "id": obj.id, "status": obj.status})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@never_cache
def tasks_log(request: Request) -> Response:
    """واجهة بسيطة لتسجيل مهمة/نشاط.

    body:
      resource_type, resource_id, action, status(optional), message(optional), payload(optional), assignee_id(optional), due_at(optional ISO)
    """
    b = request.data or {}
    resource_type = (b.get("resource_type") or "").strip()
    resource_id = str(b.get("resource_id") or "").strip()
    action = (b.get("action") or "").strip()
    status_val = (b.get("status") or "open").strip() or "open"
    message = (b.get("message") or "").strip()
    payload = b.get("payload") if isinstance(b.get("payload"), (dict, list)) else None
    assignee_id = b.get("assignee_id")
    due_at_iso = (b.get("due_at") or "").strip()

    if not resource_type or not resource_id or not action:
        return Response({"detail": "resource_type/resource_id/action مطلوبة"}, status=status.HTTP_400_BAD_REQUEST)

    from django.contrib.auth.models import User as DjangoUser

    assignee = None
    if assignee_id:
        try:
            assignee = DjangoUser.objects.get(id=int(assignee_id))
        except Exception:
            assignee = None
    due_at = None
    if due_at_iso:
        from django.utils.dateparse import parse_datetime

        due_at = parse_datetime(due_at_iso)

    obj = TaskLog.objects.create(
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        status=status_val if status_val in {"open", "in_progress", "done", "canceled"} else "open",
        actor=request.user,
        assignee=assignee,
        message=message,
        payload=payload,
        due_at=due_at,
    )
    return Response({"id": obj.id}, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@never_cache
def tasks_list(request: Request) -> Response:
    """قائمة المهام مع فلاتر بسيطة."""
    qs = TaskLog.objects.all()
    p = request.query_params
    rt = (p.get("resource_type") or "").strip()
    rid = (p.get("resource_id") or "").strip()
    status_f = (p.get("status") or "").strip()
    mine = (p.get("mine") or "").strip().lower() in {"1", "true", "yes"}
    if rt:
        qs = qs.filter(resource_type=rt)
    if rid:
        qs = qs.filter(resource_id=str(rid))
    if status_f in {"open", "in_progress", "done", "canceled"}:
        qs = qs.filter(status=status_f)
    # افتراضياً، غير المشرفين يرون مهامهم فقط
    user = request.user
    if mine or not (user.is_staff or user.is_superuser):
        qs = qs.filter(Q(actor=user) | Q(assignee=user))
    qs = qs.order_by("-created_at")[:500]

    data = [
        {
            "id": t.id,
            "action": t.action,
            "status": t.status,
            "resource_type": t.resource_type,
            "resource_id": t.resource_id,
            "actor_id": t.actor_id,
            "assignee_id": t.assignee_id,
            "message": t.message,
            "due_at": t.due_at.isoformat() if t.due_at else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in qs
    ]
    return Response(data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@never_cache
def tasks_mine(request: Request) -> Response:
    request.GET._mutable = True  # type: ignore
    request.GET["mine"] = "1"  # type: ignore
    return tasks_list(request)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
@never_cache
def task_update(request: Request, id: int) -> Response:
    """تحديث حالة/إسناد/ملاحظة لمهمة."""
    try:
        t = TaskLog.objects.get(id=id)
    except TaskLog.DoesNotExist:
        return Response({"detail": "غير موجود"}, status=status.HTTP_404_NOT_FOUND)
    # السماح بالتحديث لمالك المهمة (actor/assignee) أو موظفي الإدارة
    u = request.user
    if not (u.is_superuser or u.is_staff or t.actor_id == u.id or t.assignee_id == u.id):
        return Response({"detail": "صلاحية غير كافية"}, status=status.HTTP_403_FORBIDDEN)
    b = request.data or {}
    changed = False
    st = (b.get("status") or "").strip()
    if st in {"open", "in_progress", "done", "canceled"}:
        t.status = st
        changed = True
    msg = b.get("message")
    if isinstance(msg, str):
        t.message = msg[:300]
        changed = True
    assignee_id = b.get("assignee_id")
    if assignee_id is not None:
        try:
            from django.contrib.auth.models import User as DjangoUser

            t.assignee = DjangoUser.objects.get(id=int(assignee_id))
            changed = True
        except Exception:
            pass
    if changed:
        t.save()
    return Response({"detail": "ok", "id": t.id, "status": t.status})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@never_cache
def reject_approval_request(request: Request, id: int) -> Response:
    """رفض طلب موافقة (يظل التنفيذ بحسب نوع المورد خارج هذا النطاق)."""
    user = request.user
    try:
        obj = ApprovalRequest.objects.get(id=id)
    except ApprovalRequest.DoesNotExist:
        return Response({"detail": "العنصر غير موجود"}, status=status.HTTP_404_NOT_FOUND)

    roles = set(user.groups.values_list("name", flat=True))  # type: ignore
    try:
        staff = Staff.objects.filter(user=user).only("role").first()
        if staff and staff.role:
            roles.add(staff.role)
    except Exception:
        pass

    is_principal = "principal" in roles
    is_vice = "academic_deputy" in roles or "vice_principal" in roles
    if not (is_principal or is_vice or user.is_superuser):
        return Response({"detail": "لا تملك صلاحية الرفض"}, status=status.HTTP_403_FORBIDDEN)

    if obj.status != "pending":
        return Response({"detail": "لا يمكن رفض هذا الطلب في حالته الحالية"}, status=status.HTTP_400_BAD_REQUEST)

    # Optional: امنع مقدم الطلب من رفضه ذاتيًا؟ سنسمح لأن الرفض إداري عادة، لكن نحافظ على نفس قاعدة عدم الاعتماد الذاتي فقط.
    obj.status = "rejected"
    obj.save(update_fields=["status", "updated_at"])
    return Response({"detail": "تم الرفض", "id": obj.id, "status": obj.status})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_password(request: Request) -> Response:
    user = request.user
    payload = request.data or {}
    current = payload.get("current_password") or ""
    new1 = payload.get("new_password1") or ""
    new2 = payload.get("new_password2") or ""
    # Validate current
    if not user.check_password(current):
        return Response(
            {"detail": "كلمة المرور الحالية غير صحيحة"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    # Validate matching
    if new1 != new2:
        return Response(
            {"detail": "كلمتا المرور الجديدتان غير متطابقتين"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    # Run Django validators
    try:
        password_validation.validate_password(new1, user)
    except Exception as exc:
        # Collect messages
        messages = []
        try:
            messages = [str(e) for e in exc.error_list]  # type: ignore[attr-defined]
        except Exception:
            messages = [str(exc)]
        return Response({"detail": "", "errors": messages}, status=status.HTTP_400_BAD_REQUEST)
    # Save new password
    user.set_password(new1)
    user.save(update_fields=["password"])
    return Response({"detail": "تم تغيير كلمة المرور بنجاح"}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@never_cache
def logout(request: Request) -> Response:
    """
    Blacklist the refresh token to log the user out from this device.
    Accepts refresh token from JSON body or from HttpOnly cookie.
    Also clears the refresh cookie on successful logout.
    """
    # Try to get refresh from body; if missing, fallback to cookie
    refresh_str = (request.data or {}).get("refresh")
    if not refresh_str:
        try:
            from ..auth import REFRESH_COOKIE_NAME  # local constant
        except Exception:
            REFRESH_COOKIE_NAME = "refresh_token"  # fallback
        refresh_str = request.COOKIES.get(REFRESH_COOKIE_NAME)
    if not refresh_str:
        # Nothing to do, but clear cookie if present and return 200
        resp = Response({"detail": "لا يوجد رمز تحديث لإلغائه"}, status=status.HTTP_200_OK)
        try:
            from django.conf import settings as _settings

            from ..auth import REFRESH_COOKIE_SAMESITE, REFRESH_COOKIE_SECURE

            resp.delete_cookie(
                key=getattr(_settings, "SIMPLE_JWT_REFRESH_COOKIE_NAME", "refresh_token"),
                samesite=REFRESH_COOKIE_SAMESITE,
                secure=REFRESH_COOKIE_SECURE,
            )
        except Exception:
            pass
        return resp
    # Blacklist provided refresh token
    try:
        token = RefreshToken(refresh_str)
        token.blacklist()
    except Exception:
        # Even if blacklist fails (e.g., invalid), still clear cookie and return 200
        resp = Response({"detail": "تمت محاولة تسجيل الخروج"}, status=status.HTTP_200_OK)
        try:
            from django.conf import settings as _settings

            from ..auth import REFRESH_COOKIE_SAMESITE, REFRESH_COOKIE_SECURE

            resp.delete_cookie(
                key=getattr(_settings, "SIMPLE_JWT_REFRESH_COOKIE_NAME", "refresh_token"),
                samesite=REFRESH_COOKIE_SAMESITE,
                secure=REFRESH_COOKIE_SECURE,
            )
        except Exception:
            pass
        return resp
    # Success: clear cookie and confirm
    resp = Response({"detail": "تم تسجيل الخروج بنجاح"}, status=status.HTTP_200_OK)
    try:
        from django.conf import settings as _settings

        from ..auth import REFRESH_COOKIE_SAMESITE, REFRESH_COOKIE_SECURE

        resp.delete_cookie(
            key=getattr(_settings, "SIMPLE_JWT_REFRESH_COOKIE_NAME", "refresh_token"),
            samesite=REFRESH_COOKIE_SAMESITE,
            secure=REFRESH_COOKIE_SECURE,
        )
    except Exception:
        pass
    return resp
