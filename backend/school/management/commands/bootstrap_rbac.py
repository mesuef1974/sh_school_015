from django.core.management import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from school.models import Class, Student, Staff


class Command(BaseCommand):
    help = "Create default groups and attach permissions"

    def handle(self, *args, **kwargs):
        mapping = {
            "Admin": {"all": [Class, Student, Staff]},
            "Teacher": {"view_add_change": [Student, Class]},
            "Staff": {"view_change": [Student, Staff]},
            "Student": {"view": [Student]},
        }
        for group_name, perms in mapping.items():
            g, _ = Group.objects.get_or_create(name=group_name)
            for mode, models_ in perms.items():
                for m in models_:
                    ct = ContentType.objects.get_for_model(m)
                    if mode == "all":
                        codes = ["add", "change", "delete", "view"]
                    elif mode == "view_add_change":
                        codes = ["view", "add", "change"]
                    elif mode == "view_change":
                        codes = ["view", "change"]
                    else:
                        codes = ["view"]
                    for c in codes:
                        p = Permission.objects.get(
                            codename=f"{c}_{m._meta.model_name}", content_type=ct
                        )
                        g.permissions.add(p)
        self.stdout.write(self.style.SUCCESS("RBAC groups initialized"))
