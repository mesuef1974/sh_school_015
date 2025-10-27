from __future__ import annotations

from typing import List

from django.contrib.auth import password_validation
from django.contrib.auth.models import Permission
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.views.decorators.cache import never_cache
from ..models import Staff, TeachingAssignment, Wing


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
        staff_obj = Staff.objects.filter(user=user).only("id","role").first()
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
                roles_norm.add('teacher')
    except Exception:
        has_teaching_assignments = False

    # Permissions as "app_label.codename"
    perms: List[str] = [
        f"{p.content_type.app_label}.{p.codename}" for p in Permission.objects.filter(user=user)
    ]
    # Also include group-granted permissions
    group_perms_qs = Permission.objects.filter(group__user=user).values_list(
        "content_type__app_label", "codename"
    )
    perms += [f"{app}.{code}" for app, code in group_perms_qs]
    # Deduplicate
    perms = sorted(set(perms))

    # Capabilities derived from roles for frontend UI gating (non-authoritative; server enforces separately)
    role_set = set(roles_norm)
    can_manage_timetable = bool(
        user.is_superuser
        or role_set.intersection({"principal", "academic_deputy", "timetable_manager"})
    )
    caps = {
        "can_manage_timetable": can_manage_timetable,
        "can_view_general_timetable": True,  # all authenticated users may view; templates may still gate by staff
        "can_take_attendance": bool("teacher" in role_set),
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

    data = {
        "id": user.id,
        "username": user.username,
        "full_name": staff_full_name or user.get_full_name() or user.username,
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