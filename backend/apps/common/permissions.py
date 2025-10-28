from __future__ import annotations

from typing import Iterable

from rest_framework.permissions import BasePermission

# Domain models (optional imports; avoid hard dependency at import time)
try:
    from school.models import Class, Staff, TeachingAssignment  # type: ignore
except Exception:  # pragma: no cover - during early migrations
    Staff = None  # type: ignore
    TeachingAssignment = None  # type: ignore
    Class = None  # type: ignore


# ---------- Helpers ----------


def user_in_any_role(user, roles: Iterable[str]) -> bool:
    if getattr(user, "is_superuser", False):
        return True
    # Normalize group names (Arabic/legacy) to canonical role codes
    try:
        raw_roles = set(user.groups.values_list("name", flat=True))  # type: ignore
    except Exception:
        raw_roles = set()
    # Also consider Staff.role if present (some deployments store role code/name there)
    try:
        if Staff is not None:
            st = Staff.objects.filter(user_id=user.id).only("role").first()
            if st and getattr(st, "role", None):
                raw_roles.add(st.role)
    except Exception:
        pass
    try:
        from apps.common.roles import normalize_roles  # type: ignore

        user_roles = normalize_roles(raw_roles)
    except Exception:
        user_roles = raw_roles
    # Required roles are expected to be canonical codes already
    return any(r in user_roles for r in roles)


def user_can_access_class(user, class_id: int) -> bool:
    """Centralized object access for a classroom.
    - superuser: allow
    - teacher: allowed if has a TeachingAssignment for the class
    - wing_supervisor: allowed if Class has wing relation and it's within supervised wings
    - principal/academic_deputy: allow
    """
    if not class_id:
        return False
    if getattr(user, "is_superuser", False):
        return True
    # Resolve Staff (if exists)
    staff = None
    if Staff is not None:
        try:
            staff = Staff.objects.filter(user_id=user.id).first()
        except Exception:
            staff = None
    try:
        raw_roles = set(user.groups.values_list("name", flat=True))  # type: ignore
    except Exception:
        raw_roles = set()
    # Include Staff.role for normalization
    try:
        if staff is None and Staff is not None:
            staff = Staff.objects.filter(user_id=user.id).only("role").first()
        if staff and getattr(staff, "role", None):
            raw_roles.add(staff.role)
    except Exception:
        pass
    try:
        from apps.common.roles import normalize_roles  # type: ignore

        roles = normalize_roles(raw_roles)
    except Exception:
        roles = raw_roles

    if "principal" in roles or "academic_deputy" in roles:
        return True

    # Allow any mapped Staff with a direct TeachingAssignment for the class (no hard dependency on 'teacher' group)
    if staff is not None and TeachingAssignment is not None:
        try:
            if TeachingAssignment.objects.filter(teacher_id=staff.id, classroom_id=class_id).exists():
                return True
        except Exception:
            return False

    if "wing_supervisor" in roles and staff is not None and Class is not None:
        # If the data model exposes managed_wings on Staff and wing on Class, enforce it
        try:
            if hasattr(staff, "managed_wings") and hasattr(Class, "wing_id"):
                wing_ids = list(getattr(staff, "managed_wings").values_list("id", flat=True))
                if not wing_ids:
                    return False
                return Class.objects.filter(id=class_id, wing_id__in=wing_ids).exists()
        except Exception:
            return False

    return False


# ---------- DRF Permissions ----------


class IsInRole(BasePermission):
    roles: tuple[str, ...] = ()

    def has_permission(self, request, view) -> bool:
        if getattr(request.user, "is_superuser", False):
            return True
        return user_in_any_role(request.user, self.roles)


class IsTeacher(IsInRole):
    roles = ("teacher",)


class IsWingSupervisor(IsInRole):
    roles = ("wing_supervisor",)


class IsTimetableManager(IsInRole):
    """Roles allowed to create/edit timetable globally."""

    roles = ("principal", "academic_deputy", "timetable_manager")


class CanAccessClass(BasePermission):
    """Object-level permission for class access.
    Expects the view to pass the class_id to has_object_permission or for the
    view to call user_can_access_class explicitly.
    """

    def has_object_permission(self, request, view, obj) -> bool:
        class_id = None
        # obj can be id or a model instance with id
        if isinstance(obj, int):
            class_id = obj
        else:
            class_id = getattr(obj, "id", None)
        if class_id is None:
            return False
        return user_can_access_class(request.user, int(class_id))
