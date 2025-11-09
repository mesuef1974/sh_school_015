# RBAC Seeding (Discipline)

This note explains how to grant the new granular Incident permissions to role groups for quick testing. You can do it via Django Admin or with a quick shell snippet.

## Permissions (codename)
- discipline.incident_create
- discipline.incident_submit
- discipline.incident_review
- discipline.incident_escalate
- discipline.incident_notify_guardian
- discipline.incident_close

Superusers and staff bypass checks automatically.

## Suggested groups
- Teacher
- WingSupervisor
- Counselor
- Leadership

### Suggested mapping
- Teacher: incident_create, incident_submit
- WingSupervisor: incident_review, incident_escalate, incident_notify_guardian, incident_close
- Counselor: incident_review, incident_notify_guardian
- Leadership: incident_review, incident_escalate, incident_notify_guardian, incident_close

## Grant via Admin
1) /admin/auth/group/ → add groups named above (if not present).
2) Add permissions to each group under app "discipline" using the codenames listed.
3) Assign users to the groups.

## Grant via Django shell (example)
```python
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from discipline.models import Incident

ct = ContentType.objects.get_for_model(Incident)
perms = {
    'incident_create': Permission.objects.get(codename='incident_create', content_type=ct),
    'incident_submit': Permission.objects.get(codename='incident_submit', content_type=ct),
    'incident_review': Permission.objects.get(codename='incident_review', content_type=ct),
    'incident_escalate': Permission.objects.get(codename='incident_escalate', content_type=ct),
    'incident_notify_guardian': Permission.objects.get(codename='incident_notify_guardian', content_type=ct),
    'incident_close': Permission.objects.get(codename='incident_close', content_type=ct),
}

def ensure_group(name, perm_keys):
    g, _ = Group.objects.get_or_create(name=name)
    g.permissions.set([perms[k] for k in perm_keys])
    g.save()
    return g

ensure_group('Teacher', ['incident_create', 'incident_submit'])
ensure_group('WingSupervisor', ['incident_review', 'incident_escalate', 'incident_notify_guardian', 'incident_close'])
ensure_group('Counselor', ['incident_review', 'incident_notify_guardian'])
ensure_group('Leadership', ['incident_review', 'incident_escalate', 'incident_notify_guardian', 'incident_close'])
print('RBAC discipline groups updated.')
```

Run the snippet in: `python manage.py shell`.

Note: permissions are created automatically by Django after migrations (`post_migrate`). If you added permissions recently, restarting the server or running a no-op `migrate` ensures they exist.