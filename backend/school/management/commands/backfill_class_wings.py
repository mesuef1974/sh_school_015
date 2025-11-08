from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = (
        "Backfill Class.wing for classes missing linkage based on grade/section mapping to wings. "
        "Ground wings: 1,2; Upper wings: 3,4,5."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Do not write changes, only print what would be done.",
        )

    def _infer_wing_no(self, cls):
        try:
            # If already has a wing, keep it
            if getattr(cls, "wing_id", None):
                return None
            # Grade
            grade = int(getattr(cls, "grade", 0) or 0)
            # Section number from Class.section or from name like '11/2'
            import re

            sec_num = None
            sec_raw = str(getattr(cls, "section", "") or "").strip()
            m = re.match(r"^(\d+)", sec_raw)
            if m:
                sec_num = int(m.group(1))
            else:
                name = str(getattr(cls, "name", "") or "")
                m2 = re.search(r"^(\d+)[\-\./](\d+)", name.strip())
                if m2:
                    grade = grade or int(m2.group(1))
                    sec_num = int(m2.group(2))
            if not grade or sec_num is None:
                return None
            # Mapping rules
            if grade == 7 and 1 <= sec_num <= 5:
                return 1
            if grade == 8 and 1 <= sec_num <= 4:
                return 2
            if grade == 9 and sec_num == 1:
                return 2
            if grade == 9 and 2 <= sec_num <= 4:
                return 3
            if grade == 10 and 1 <= sec_num <= 2:
                return 3
            if grade == 10 and 3 <= sec_num <= 4:
                return 4
            if grade == 11 and 1 <= sec_num <= 3:
                return 4
            if grade == 11 and sec_num == 4:
                return 5
            if grade == 12 and 1 <= sec_num <= 4:
                return 5
        except Exception:
            return None
        return None

    def handle(self, *args, **options):
        from django.apps import apps

        Class = apps.get_model("school", "Class")
        Wing = apps.get_model("school", "Wing")

        dry = bool(options.get("dry_run"))
        qs = Class.objects.filter(wing__isnull=True).order_by("grade", "name")
        total = qs.count()
        self.stdout.write(f"Classes without wing: {total}")
        updated = 0
        skipped = 0

        with transaction.atomic():
            for cls in qs:
                wing_no = self._infer_wing_no(cls)
                if not wing_no:
                    skipped += 1
                    continue
                wing_obj = (
                    Wing.objects.filter(id=wing_no).first() or Wing.objects.filter(name__icontains=str(wing_no)).first()
                )
                if not wing_obj:
                    skipped += 1
                    continue
                self.stdout.write(f"Assign {cls.name} -> Wing {wing_obj.id} ({wing_obj.name})")
                if not dry:
                    cls.wing = wing_obj
                    (cls.save(update_fields=["wing", "updated_at"]) if hasattr(cls, "updated_at") else cls.save())
                    updated += 1
            if dry:
                transaction.set_rollback(True)
        self.stdout.write(self.style.SUCCESS(f"Updated: {updated}, Skipped: {skipped}, Total: {total}"))
