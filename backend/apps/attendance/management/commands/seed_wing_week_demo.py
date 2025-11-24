from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "تم إيقاف وإزالة أدوات توليد البيانات التجريبية للأسبوع بالكامل. لن يقوم هذا الأمر بأي عمل بعد الآن."

    def add_arguments(self, parser):
        return

    def handle(self, *args, **opts):
        raise CommandError(
            "تم حذف أداة seed_wing_week_demo بالتبعية بعد إزالة أدوات الزراعة التجريبية اليومية. "
            "للحصول على بيانات أولية، يُنصح باستخدام بدائل مثل: الاستيراد عبر CSV/JSON من لوحة الإدارة، "
            "أو تجهيز Fixtures رسمية لبيئة التجربة والاختبار."
        )
