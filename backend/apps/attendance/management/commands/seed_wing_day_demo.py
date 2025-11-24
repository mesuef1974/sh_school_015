from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "تم إيقاف وإزالة أداة توليد البيانات التجريبية. لن تقوم هذه الأداة بأي عمل بعد الآن."

    def add_arguments(self, parser):
        # نُبقي التواقيع فارغة لتوضيح الإيقاف فقط
        return

    def handle(self, *args, **options):
        # رسالة واضحة بالعربية تشرح سبب الإيقاف وما البدائل المقترحة
        raise CommandError(
            "تم حذف أداة seed_wing_day_demo بناءً على الطلب لأنها لا تعمل كما ينبغي ولأن قاعدة البيانات بقيت فارغة. "
            "إن احتجت بيانات أولية، يُفضّل استخدام طرق بديلة مثل: استيراد ملفات CSV/JSON عبر المشرف، "
            "أو استخدام هجرات/Fixtures رسمية مخصّصة للبيئة."
        )
