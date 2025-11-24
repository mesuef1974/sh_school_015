from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "تم إيقاف وإزالة أداة توليد بيانات شهرية للجناح. لن يقوم هذا الأمر بأي عمل بعد الآن."

    def add_arguments(self, parser):
        return

    def handle(self, *args, **opts):
        raise CommandError(
            "تم حذف أداة seed_wing_month_demo بالتبعية بعد إزالة أدوات الزراعة التجريبية اليومية/الأسبوعية. "
            "للحصول على بيانات أولية، يُنصح باستخدام بدائل مثل: الاستيراد عبر CSV/JSON من لوحة الإدارة، "
            "أو تجهيز Fixtures رسمية لبيئة التجربة والاختبار."
        )
