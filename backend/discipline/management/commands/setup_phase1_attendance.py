from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import transaction


class Command(BaseCommand):
    help = (
        "تهيئة المرحلة 1: إنشاء مجموعة 'WingSupervisor' مع الصلاحيات الخاصة بإدارة أعذار الغياب والإجراءات، "
        "ومحاولة التأكد من توفر الصلاحيات المطلوبة على النماذج ذات الصلة (ExcuseRequest/Action/IncidentAttachment)."
    )

    GROUP_NAME = "WingSupervisor"
    # صلاحيات ExcuseRequest
    EXCUSE_PERMS = [
        "can_review_excuse_requests",
        "can_convert_absence_status",
        "can_request_attachment_corrections",
    ]
    # صلاحيات Action
    ACTION_PERMS = [
        "action_view",
        "action_create",
        "action_complete",
    ]
    # صلاحيات IncidentAttachment
    ATTACHMENT_PERMS = [
        "incident_attachment_upload",
    ]
    # صلاحيات Incident (إشعار ولي الأمر)
    INCIDENT_PERMS = [
        "incident_notify_guardian",
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="عرض ما سيتم دون كتابة أي تغييرات.",
        )

    def handle(self, *args, **options):
        dry = bool(options.get("dry_run"))
        # اجلب ContentTypes للنماذج المستهدفة داخل تطبيق discipline
        try:
            ct_excuse = ContentType.objects.get(app_label="discipline", model="excuserequest")
        except ContentType.DoesNotExist:
            self.stdout.write(
                self.style.WARNING(
                    "تعذر إيجاد ContentType لـ ExcuseRequest. تأكد من تشغيل المهاجرات: python manage.py migrate"
                )
            )
            ct_excuse = None
        try:
            ct_action = ContentType.objects.get(app_label="discipline", model="action")
        except ContentType.DoesNotExist:
            self.stdout.write(
                self.style.WARNING(
                    "تعذر إيجاد ContentType لـ Action. تأكد من تشغيل المهاجرات: python manage.py migrate"
                )
            )
            ct_action = None
        try:
            ct_attach = ContentType.objects.get(app_label="discipline", model="incidentattachment")
        except ContentType.DoesNotExist:
            self.stdout.write(
                self.style.WARNING(
                    "تعذر إيجاد ContentType لـ IncidentAttachment. تأكد من تشغيل المهاجرات: python manage.py migrate"
                )
            )
            ct_attach = None

        with transaction.atomic():
            # أنشئ/احصل على المجموعة
            group, created = Group.objects.get_or_create(name=self.GROUP_NAME)
            if created:
                self.stdout.write(self.style.SUCCESS(f"تم إنشاء المجموعة: {group.name}"))
            else:
                self.stdout.write(self.style.NOTICE(f"المجموعة موجودة مسبقًا: {group.name}"))

            # اجلب الصلاحيات إن وُجدت
            to_add = []
            missing = []

            def collect_perms(ct: ContentType, codes):
                acc_found, acc_missing = [], []
                if ct is None:
                    acc_missing.extend(codes)
                    return acc_found, acc_missing
                for code in codes:
                    try:
                        acc_found.append(Permission.objects.get(content_type=ct, codename=code))
                    except Permission.DoesNotExist:
                        acc_missing.append(code)
                return acc_found, acc_missing

            f, m = collect_perms(ct_excuse, self.EXCUSE_PERMS)
            to_add += f
            missing += m
            f, m = collect_perms(ct_action, self.ACTION_PERMS)
            to_add += f
            missing += m
            f, m = collect_perms(ct_attach, self.ATTACHMENT_PERMS)
            to_add += f
            missing += m
            # Incident permissions (notify guardian)
            try:
                ct_incident = ContentType.objects.get(app_label="discipline", model="incident")
            except ContentType.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(
                        "تعذر إيجاد ContentType لـ Incident. تأكد من تشغيل المهاجرات: python manage.py migrate"
                    )
                )
                ct_incident = None
            f, m = collect_perms(ct_incident, self.INCIDENT_PERMS)
            to_add += f
            missing += m

            if dry:
                self.stdout.write(self.style.WARNING("تشغيل جاف (Dry Run): لن يتم تعديل الصلاحيات."))
            else:
                if to_add:
                    group.permissions.add(*to_add)
                    self.stdout.write(self.style.SUCCESS(f"أُضيفت {len(to_add)} صلاحية إلى المجموعة '{group.name}'."))
                if missing:
                    self.stdout.write(
                        self.style.WARNING(
                            "لم يتم العثور على الصلاحيات التالية (ربما تحتاج migrate): " + ", ".join(missing)
                        )
                    )

            self.stdout.write(self.style.SUCCESS("اكتملت تهيئة صلاحيات المرحلة 1 (أعذار الغياب)."))
