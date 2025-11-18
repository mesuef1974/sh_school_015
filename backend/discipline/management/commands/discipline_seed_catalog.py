from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = "Seed BehaviorLevel (1-4) and a minimal Violation catalog derived from the policy document. Idempotent."

    @transaction.atomic
    def handle(self, *args, **options):
        from backend.discipline.models import BehaviorLevel, Violation

        # Seed behavior levels 1..4
        lvls = {
            1: ("الدرجة الأولى", "سلوكيات بسيطة تُعالج تربويًا وتنبيهات أولية"),
            2: ("الدرجة الثانية", "سلوكيات متوسطة التأثير: إنذارات واستدعاء ولي أمر"),
            3: ("الدرجة الثالثة", "سلوكيات عالية الخطورة النسبية وإحالة للجنة"),
            4: ("الدرجة الرابعة", "سلوكيات جسيمة وإجراءات قصوى"),
        }
        created_levels = 0
        for code, (name, desc) in lvls.items():
            obj, created = BehaviorLevel.objects.update_or_create(
                code=code, defaults={"name": name, "description": desc}
            )
            if created:
                created_levels += 1
        self.stdout.write(self.style.SUCCESS(f"BehaviorLevel upserted. New created: {created_levels}"))

        # Minimal violations per degree (subset sufficient to unblock flows)
        catalog = [
            # degree 1
            {
                "code": "V1-LATE-PERIOD",
                "category": "التأخر عن حضور الحصة",
                "desc": "دخول بعد المعلم/الجرس دون عذر",
                "severity": 1,
                "requires_committee": False,
            },
            {
                "code": "V1-DISRUPTION",
                "category": "إثارة الفوضى داخل الفصل",
                "desc": "ضوضاء/حديث جانبي يعوق الدرس",
                "severity": 1,
                "requires_committee": False,
            },
            # degree 2
            {
                "code": "V2-SKIP-PERIOD",
                "category": "الهروب من الحصص",
                "desc": "التغيب عن بعض الحصص دون عذر",
                "severity": 2,
                "requires_committee": False,
            },
            {
                "code": "V2-PHONE",
                "category": "إحضار الهاتف بالمخالفة",
                "desc": "إحضار/استخدام الهاتف خلاف الأنظمة",
                "severity": 2,
                "requires_committee": False,
            },
            # degree 3
            {
                "code": "V3-SKIP-SCHOOL",
                "category": "الهروب من المدرسة",
                "desc": "مغادرة المدرسة أثناء الدوام دون إذن",
                "severity": 3,
                "requires_committee": True,
            },
            {
                "code": "V3-DAMAGE",
                "category": "إتلاف مصادر التعلم",
                "desc": "إتلاف كتب/أدوات/أجهزة بشكل مؤثر",
                "severity": 3,
                "requires_committee": True,
            },
            # degree 4
            {
                "code": "V4-DRUGS",
                "category": "مخدرات وممنوعات",
                "desc": "حيازة/تعاطي/ترويج مواد مخدرة",
                "severity": 4,
                "requires_committee": True,
            },
            {
                "code": "V4-WEAPON",
                "category": "حيازة أو استخدام سلاح/أداة حادة",
                "desc": "سكاكين ونحوها داخل المدرسة",
                "severity": 4,
                "requires_committee": True,
            },
        ]

        created_violations = 0
        for item in catalog:
            level = BehaviorLevel.objects.get(code=item["severity"])
            defaults = {
                "level": level,
                "category": item["category"],
                "description": item["desc"],
                "default_actions": [],
                "default_sanctions": [],
                "severity": item["severity"],
                "requires_committee": item["requires_committee"],
                "policy": {"window_days": 365},
            }
            obj, created = Violation.objects.update_or_create(code=item["code"], defaults=defaults)
            if created:
                created_violations += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Violations upserted. New created: {created_violations}. Total now: {Violation.objects.count()}"
            )
        )
