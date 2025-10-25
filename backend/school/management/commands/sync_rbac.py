import os
import sys

# Bootstrap Django when executed directly (outside manage.py)
if not os.environ.get('DJANGO_SETTINGS_MODULE'):
    try:
        _HERE = os.path.abspath(os.path.dirname(__file__))
        # Go up three levels: backend/school/management/commands -> backend
        _BACKEND_DIR = os.path.normpath(os.path.join(_HERE, '..', '..', '..'))
        if _BACKEND_DIR not in sys.path:
            sys.path.insert(0, _BACKEND_DIR)
        # Project settings module lives under core.settings
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
        import django as _django  # type: ignore
        _django.setup()
    except Exception:
        # If setup fails here, manage.py execution path will handle it.
        pass

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from typing import Dict, List, Set, Tuple

# Domain models used to derive roles from existing data
try:
    from school.models import Staff, Wing, TeachingAssignment, TimetableEntry, Term
except Exception:  # pragma: no cover - allow import in partial environments
    Staff = None  # type: ignore
    Wing = None  # type: ignore
    TeachingAssignment = None  # type: ignore
    TimetableEntry = None  # type: ignore
    Term = None  # type: ignore

# IMPORTANT: This RBAC map is derived from the backend icons catalog (/data/icons/)
# Each role maps to a set of semantic permission codes used by the frontend.
# We materialize them as Django Permissions (under content type school.Staff) so
# they can be assigned to Groups and surfaced via /api/me/ if desired.
RBAC_MAP: Dict[str, Set[str]] = {
    # Teacher
    'teacher': {
        'academics.classes.read',
        'academics.timetable.read',
        'attendance.session.write',
        'attendance.history.read',
        'communications.announcements.write',
        'academics.assignments',
        'academics.quizzes',
        'academics.grades',
        'academics.lesson_plans',
        'academics.resources',
        'communications.messages',
    },
    # Wing supervisor
    'wing_supervisor': {
        'attendance.wing.read',
        'attendance.daily.read',
        'attendance.missing.read',
        'attendance.exits.manage',
        'behavior.incidents.manage',
        'academics.timetable.read',
        'reports.wing',
    },
    # Subject coordinator
    'subject_coordinator': {
        'analytics.subject.read',
        'academics.question_bank',
        'academics.rubrics',
    },
    # Principal
    'principal': {
        'analytics.kpi',
        'reports.official',
        'it.users',
    },
    # Academic deputy
    'academic_deputy': {
        'academics.timetable.manage',
        'academics.assessments.manage',
        'academics.curricula',
    },
    # Administrative deputy (operations)
    'admin_deputy': {
        'admin_ops.hr',
        'admin_ops.finance',
        'admin_ops.procurement',
        'admin_ops.assets',
        'admin_ops.facilities',
        'admin_ops.transport',
    },
    # Student affairs
    'student_affairs': {
        'student_affairs.admissions',
        'student_affairs.records',
    },
    # IT, Admin, Finance, and general Staff roles
    'it': set(),
    'admin': set(),
    'finance': set(),
    'staff': set(),
}

ROLE_GROUPS: List[str] = list(RBAC_MAP.keys())


def _normalize_perm(code: str) -> Tuple[str, str]:
    """Return (codename, name) for a given semantic permission code.
    We store all semantic permissions as Django Permission objects attached to
    ContentType(school.Staff) with codename using dots replaced by underscores.
    """
    code = code.strip()
    codename = code.replace('.', '_').replace('-', '_')
    name = f"RBAC: {code}"
    return codename, name


def _get_staff_content_type() -> ContentType:
    # Attach custom semantic perms to Staff model content type (exists in app 'school')
    try:
        return ContentType.objects.get(app_label='school', model='staff')
    except ContentType.DoesNotExist:
        # Fallback to auth | user to ensure existence; but in this project Staff exists.
        return ContentType.objects.get(app_label='auth', model='user')


class Command(BaseCommand):
    help = (
        "Synchronize RBAC: create groups for roles, materialize semantic permissions, "
        "assign permissions to groups per the icons catalog, and auto-assign users to groups."
    )

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Show what would change without applying it.')
        parser.add_argument('--no-user-sync', action='store_true', help='Skip user/group membership synchronization.')

    @transaction.atomic
    def handle(self, *args, **opts):
        dry = bool(opts.get('dry_run'))
        skip_users = bool(opts.get('no_user_sync'))

        self.stdout.write(self.style.MIGRATE_HEADING('RBAC sync starting'))

        # 1) Ensure Groups exist
        groups: Dict[str, Group] = {}
        created_groups: List[str] = []
        for name in ROLE_GROUPS:
            g, created = Group.objects.get_or_create(name=name)
            groups[name] = g
            if created:
                created_groups.append(name)
        
        # 2) Ensure Permission objects exist for all semantic perms
        ct = _get_staff_content_type()
        ensured_perms: List[str] = []
        perm_objects: Dict[str, Permission] = {}
        for role, perms in RBAC_MAP.items():
            for p in perms:
                codename, pname = _normalize_perm(p)
                perm, created = Permission.objects.get_or_create(codename=codename, content_type=ct, defaults={'name': pname})
                if created:
                    ensured_perms.append(p)
                perm_objects[p] = perm

        # 3) Assign permissions to groups (idempotent)
        changed_assignments: List[str] = []
        for role, perms in RBAC_MAP.items():
            g = groups[role]
            want_ids = {perm_objects[p].id for p in perms if p in perm_objects}
            have_ids = set(g.permissions.values_list('id', flat=True))
            to_add = want_ids - have_ids
            to_remove = have_ids - want_ids
            if to_add or to_remove:
                changed_assignments.append(f"{role}: +{len(to_add)} -{len(to_remove)}")
            if not dry:
                if to_add:
                    g.permissions.add(*to_add)
                if to_remove:
                    g.permissions.remove(*to_remove)

        # 4) User-group synchronization from domain data
        added_memberships = 0
        removed_wing_supervisor = 0
        if not skip_users and Staff is not None:
            # Build helper maps
            teacher_user_ids: Set[int] = set()
            try:
                # From Staff.role
                for st in Staff.objects.select_related('user').all():
                    if not st.user_id:
                        continue
                    if (st.role or '').strip().lower() == 'teacher':
                        teacher_user_ids.add(st.user_id)
                # From TeachingAssignment (any assignment qualifies user as teacher)
                if TeachingAssignment is not None:
                    ids = TeachingAssignment.objects.exclude(teacher__user_id=None).values_list('teacher__user_id', flat=True).distinct()
                    teacher_user_ids.update(int(i) for i in ids if i)
                # From TimetableEntry in current term
                if Term is not None and TimetableEntry is not None:
                    term = Term.objects.filter(is_current=True).first()
                    if term:
                        ids = TimetableEntry.objects.filter(term=term).exclude(teacher__user_id=None).values_list('teacher__user_id', flat=True).distinct()
                        teacher_user_ids.update(int(i) for i in ids if i)
            except Exception:
                pass

            # Ensure teacher memberships
            teacher_group = groups.get('teacher')
            if teacher_group:
                have = set(teacher_group.user_set.values_list('id', flat=True))
                to_add = teacher_user_ids - have
                if to_add and not dry:
                    teacher_group.user_set.add(*to_add)
                added_memberships += len(to_add)

            # Wing supervisors
            wing_user_ids: Set[int] = set()
            try:
                if Wing is not None:
                    for w in Wing.objects.select_related('supervisor__user').all():
                        u = getattr(getattr(w, 'supervisor', None), 'user', None)
                        if u and u.id:
                            wing_user_ids.add(u.id)
            except Exception:
                pass

            wing_group = groups.get('wing_supervisor')
            if wing_group:
                have = set(wing_group.user_set.values_list('id', flat=True))
                to_add = wing_user_ids - have
                to_remove = have - wing_user_ids
                if to_add and not dry:
                    wing_group.user_set.add(*to_add)
                if to_remove and not dry:
                    wing_group.user_set.remove(*to_remove)
                added_memberships += len(to_add)
                removed_wing_supervisor += len(to_remove)

            # Ensure ALL staff-linked users belong to the 'staff' group (baseline membership)
            try:
                staff_group = groups.get('staff')
                if staff_group and Staff is not None:
                    all_staff_user_ids: Set[int] = set(
                        int(uid) for uid in Staff.objects.exclude(user_id=None).values_list('user_id', flat=True)
                    )
                    have_staff = set(staff_group.user_set.values_list('id', flat=True))
                    staff_to_add = all_staff_user_ids - have_staff
                    if staff_to_add and not dry:
                        staff_group.user_set.add(*staff_to_add)
                    added_memberships += len(staff_to_add)
            except Exception:
                pass

            # Generic: map Staff.role to group of same name (case-insensitive)
            role_to_group = {k.lower(): v for k, v in groups.items()}
            try:
                for st in Staff.objects.select_related('user').all():
                    if not st.user_id:
                        continue
                    r = (st.role or '').strip().lower()
                    if not r:
                        continue
                    g = role_to_group.get(r)
                    if not g:
                        continue
                    if not g.user_set.filter(id=st.user_id).exists():
                        if not dry:
                            g.user_set.add(st.user_id)
                        added_memberships += 1
            except Exception:
                pass

        # 5) Report summary
        self.stdout.write(self.style.HTTP_INFO(f"Created groups: {created_groups or 'none'}"))
        self.stdout.write(self.style.HTTP_INFO(f"Ensured semantic permissions: {len(ensured_perms)} new"))
        if changed_assignments:
            self.stdout.write(self.style.SUCCESS("Group permission assignments updated: " + ", ".join(changed_assignments)))
        else:
            self.stdout.write(self.style.HTTP_INFO("Group permission assignments already up-to-date"))
        if not skip_users:
            self.stdout.write(self.style.SUCCESS(f"User memberships: +{added_memberships} added, -{removed_wing_supervisor} wing_supervisor removed"))
        if dry:
            self.stdout.write(self.style.WARNING('Dry-run mode: no changes were committed.'))
# Standalone runner support: allow executing this file directly with Python
if __name__ == '__main__':
    # Ensure Django is bootstrapped (handled above). Now invoke the command via Django's management framework.
    import argparse
    from django.core import management

    parser = argparse.ArgumentParser(description='Synchronize RBAC (standalone runner)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would change without applying it.')
    parser.add_argument('--no-user-sync', action='store_true', help='Skip user/group membership synchronization.')
    args = parser.parse_args()

    # Map argparse options to command options
    opts = {
        'dry_run': bool(getattr(args, 'dry_run', False)),
        'no_user_sync': bool(getattr(args, 'no_user_sync', False)),
    }
    management.call_command('sync_rbac', **opts)