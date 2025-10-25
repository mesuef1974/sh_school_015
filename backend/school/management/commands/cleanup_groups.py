import os
import sys
from typing import Dict, List, Set, Tuple

# Optional bootstrap to allow running this file directly with Python
if not os.environ.get('DJANGO_SETTINGS_MODULE'):
    try:
        _HERE = os.path.abspath(os.path.dirname(__file__))
        _BACKEND_DIR = os.path.normpath(os.path.join(_HERE, '..', '..', '..'))
        if _BACKEND_DIR not in sys.path:
            sys.path.insert(0, _BACKEND_DIR)
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
        import django as _django  # type: ignore
        _django.setup()
    except Exception:
        pass

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from django.db import transaction

# Reuse canonical roles from sync_rbac if available
try:
    from .sync_rbac import ROLE_GROUPS  # type: ignore
except Exception:
    ROLE_GROUPS = [
        'teacher','wing_supervisor','subject_coordinator','principal',
        'academic_deputy','admin_deputy','student_affairs','finance','it','admin'
    ]

# Legacy aliases we commonly see in deployments (case/spacing variants)
LEGACY_ALIASES: Dict[str, str] = {
    'admin': 'admin', 'Admin': 'admin', 'Super Admin': 'admin', 'super admin': 'admin',
    'principal': 'principal', 'Principal': 'principal', 'Vice Principal': 'principal', 'vice_principal': 'principal',
    'academic_deputy': 'academic_deputy', 'academic deputy': 'academic_deputy', 'Academic Deputy': 'academic_deputy',
    'admin_deputy': 'admin_deputy', 'Admin Deputy': 'admin_deputy', 'Administrative Deputy': 'admin_deputy',
    'student_affairs': 'student_affairs', 'Student Affairs': 'student_affairs',
    'finance': 'finance', 'Finance': 'finance',
    'it': 'it', 'IT': 'it', 'IT Support': 'it', 'It Support': 'it',
    'teacher': 'teacher', 'Teacher': 'teacher', 'Subject Teacher': 'teacher', 'Homeroom Teacher': 'teacher',
    'wing_supervisor': 'wing_supervisor', 'Wing Supervisor': 'wing_supervisor', 'supervisor': 'wing_supervisor',
    'subject_coordinator': 'subject_coordinator', 'Subject Coordinator': 'subject_coordinator', 'coordinator': 'subject_coordinator',
}


def normalize(name: str) -> str:
    n = (name or '').strip()
    if n in LEGACY_ALIASES:
        return LEGACY_ALIASES[n]
    # Generic normalization: lowercase, replace spaces/hyphens with underscores
    n2 = n.lower().replace(' ', '_').replace('-', '_')
    return LEGACY_ALIASES.get(n2, n2)


class Command(BaseCommand):
    help = (
        'Identify and remove duplicate/legacy Django auth groups by merging them into canonical RBAC groups. '
        'Transfers user memberships and permissions, then deletes duplicates. Idempotent and safe with --dry-run.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Show actions without applying changes')
        parser.add_argument('--force', action='store_true', help='Proceed even if a non-canonical group would be deleted')

    @transaction.atomic
    def handle(self, *args, **opts):
        dry = bool(opts.get('dry_run'))
        force = bool(opts.get('force'))
        self.stdout.write(self.style.MIGRATE_HEADING('Groups cleanup starting'))

        # Load all groups and bucket them by normalized key
        groups = list(Group.objects.all())
        buckets: Dict[str, List[Group]] = {}
        for g in groups:
            key = normalize(g.name)
            buckets.setdefault(key, []).append(g)

        # Ensure canonical buckets exist (create canonical group if bucket missing)
        created: List[str] = []
        for key in ROLE_GROUPS:
            if key not in buckets:
                if not dry:
                    cg, _ = Group.objects.get_or_create(name=key)
                    buckets[key] = [cg]
                created.append(key)

        merged_memberships = 0
        merged_perms = 0
        deleted_groups: List[Tuple[int, str]] = []
        skipped: List[str] = []

        for key, items in buckets.items():
            if not items:
                continue
            # Choose canonical target: prefer exact canonical name if present, else the first by oldest id
            canonical_name = key if key in ROLE_GROUPS else None
            target: Group
            if canonical_name:
                target = next((g for g in items if g.name == canonical_name), items[0])
            else:
                # Non-canonical category: keep first, optionally skip deletion unless --force
                items_sorted = sorted(items, key=lambda g: g.id or 0)
                target = items_sorted[0]
                if not force and len(items) > 1:
                    skipped.append(key)
                    # Still merge remaining into target to reduce duplicates, but won't delete if not canonical and --force not set
            # Merge others into target
            for g in items:
                if g.id == target.id:
                    continue
                # Transfer users
                src_user_ids = list(g.user_set.values_list('id', flat=True))
                add_ids = [uid for uid in src_user_ids if not target.user_set.filter(id=uid).exists()]
                if add_ids and not dry:
                    target.user_set.add(*add_ids)
                merged_memberships += len(add_ids)
                # Transfer permissions
                src_perm_ids = set(g.permissions.values_list('id', flat=True))
                tgt_perm_ids = set(target.permissions.values_list('id', flat=True))
                add_perm_ids = list(src_perm_ids - tgt_perm_ids)
                if add_perm_ids and not dry:
                    target.permissions.add(*add_perm_ids)
                merged_perms += len(add_perm_ids)
                # Delete the source group when allowed
                can_delete = (key in ROLE_GROUPS) or force
                if can_delete:
                    if not dry:
                        g.delete()
                    deleted_groups.append((g.id or 0, g.name))
                else:
                    skipped.append(g.name)

            # Ensure target bears canonical name if bucket is canonical but target has different name
            if key in ROLE_GROUPS and target.name != key:
                if not dry:
                    target.name = key
                    target.save(update_fields=['name'])

        # Report
        if created:
            self.stdout.write(self.style.HTTP_INFO('Created canonical groups: ' + ', '.join(created)))
        self.stdout.write(self.style.SUCCESS(f'Merged memberships: +{merged_memberships} users'))
        self.stdout.write(self.style.SUCCESS(f'Merged permissions: +{merged_perms} perms'))
        if deleted_groups:
            self.stdout.write(self.style.WARNING('Deleted duplicate groups: ' + ', '.join(f'#{gid}:{name}' for gid, name in deleted_groups)))
        else:
            self.stdout.write(self.style.HTTP_INFO('No groups deleted'))
        if skipped:
            # De-duplicate skip list for brevity
            uniq_skipped = sorted(set(skipped))
            self.stdout.write(self.style.HTTP_INFO('Skipped (kept): ' + ', '.join(uniq_skipped)))
        if dry:
            self.stdout.write(self.style.WARNING('Dry-run mode: transaction rolled back; no changes committed.'))


if __name__ == '__main__':
    # Standalone direct execution support
    import argparse
    from django.core import management

    parser = argparse.ArgumentParser(description='Cleanup duplicate Django auth groups by merging into canonical RBAC groups.')
    parser.add_argument('--dry-run', action='store_true', help='Show actions without applying changes')
    parser.add_argument('--force', action='store_true', help='Proceed even if a non-canonical group would be deleted')
    args = parser.parse_args()
    management.call_command('cleanup_groups', dry_run=bool(getattr(args, 'dry_run', False)), force=bool(getattr(args, 'force', False)))