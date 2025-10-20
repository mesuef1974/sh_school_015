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
from ..models import Staff, TeachingAssignment


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request: Request):
    user = request.user
    # Groups as role names
    roles: List[str] = list(user.groups.values_list("name", flat=True))  # type: ignore
    # Also include Staff.role if linked to a Staff record (e.g., 'teacher')
    try:
        staff_obj = Staff.objects.filter(user=user).only("role").first()
        if staff_obj and staff_obj.role:
            roles.append(staff_obj.role)
    except Exception:
        pass
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

    # Determine if the user is a teacher with actual teaching assignments (has timetable classes)
    # Also get full_name from Staff table (Arabic name)
    has_teaching_assignments = False
    staff_full_name = None
    try:
        staff = Staff.objects.filter(user=user).first()
        if staff:
            staff_full_name = staff.full_name
            if staff.role == "teacher":
                has_teaching_assignments = TeachingAssignment.objects.filter(teacher=staff).exists()
    except Exception:
        has_teaching_assignments = False

    # Capabilities derived from roles for frontend UI gating (non-authoritative; server enforces separately)
    role_set = set(roles)
    can_manage_timetable = bool(
        user.is_superuser
        or role_set.intersection({"principal", "academic_deputy", "timetable_manager"})
    )
    caps = {
        "can_manage_timetable": can_manage_timetable,
        "can_view_general_timetable": True,  # all authenticated users may view; templates may still gate by staff
        "can_take_attendance": bool("teacher" in role_set),
    }

    data = {
        "id": user.id,
        "username": user.username,
        "full_name": staff_full_name or user.get_full_name() or user.username,
        "is_superuser": user.is_superuser,
        "is_staff": user.is_staff,
        "roles": roles,
        "permissions": perms,
        "hasTeachingAssignments": has_teaching_assignments,
        "capabilities": caps,
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
            {"detail": "كلمة المرور الحالية غير صحيحة"}, status=status.HTTP_400_BAD_REQUEST
        )
    # Validate matching
    if new1 != new2:
        return Response(
            {"detail": "كلمتا المرور الجديدتان غير متطابقتين"}, status=status.HTTP_400_BAD_REQUEST
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
def logout(request: Request) -> Response:
    """
    Blacklist the refresh token to log the user out from this device.
    Expects: {"refresh": "<token>"}
    """
    refresh_str = (request.data or {}).get("refresh")
    if not refresh_str:
        return Response(
            {"detail": "رمز التحديث (refresh) مطلوب"}, status=status.HTTP_400_BAD_REQUEST
        )
    try:
        token = RefreshToken(refresh_str)
        # Will raise if blacklist app not configured; we added it in settings
        token.blacklist()
    except Exception:
        return Response({"detail": "رمز التحديث غير صالح"}, status=status.HTTP_400_BAD_REQUEST)
    return Response({"detail": "تم تسجيل الخروج بنجاح"}, status=status.HTTP_200_OK)
