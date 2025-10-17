<!-- ملف README لواجهة المستخدم -->
<div dir="rtl" lang="ar">

# واجهة نظام الشحانية — Frontend (Vue 3 + Vite + TypeScript)

هذه الواجهة هي تطبيق SPA مبني باستخدام Vue 3 وVite مع TypeScript، ومهيأ افتراضيًا للغة العربية واتجاه RTL. تم إعداد Proxy للتطوير لتمرير طلبات /api إلى Django محليًا دون مشاكل CORS.

## ما الذي بالداخل
- Vue 3 + Vite + TypeScript
- Vue Router + Pinia (إدارة الحالة)
- عميل Axios موحّد مع baseURL = /api
- دعم RTL افتراضيًا (lang="ar" dir="rtl")

## البدء السريع
- تثبيت الاعتمادات: npm install (أو pnpm/yarn حسب تفضيلك)
- تشغيل وضع التطوير: npm run dev (سيفتح http://localhost:5173)
- بناء الإنتاج: npm run build
- معاينة البناء: npm run preview

## Proxy أثناء التطوير
- يقوم Vite بتوجيه /api إلى http://127.0.0.1:8000 بحيث تتواصل الواجهة مع Django بدون إعدادات CORS إضافية أثناء التطوير.

## هيكل المشروع (مبدئي)
- src/app: قشرة التطبيق والراوتر
- src/home: صفحة البداية
- src/features/attendance/pages: صفحة غياب المعلم (أول صفحة منقولة)
- src/shared/api: عميل Axios ومساعدات الاستدعاء

## ملاحظات
- يوجد علم في الباك-إند FRONTEND_SPA_ENABLED (القيمة الافتراضية False) لتفعيل/تعطيل تقديم الواجهة الجديدة تدريجيًا مع الحفاظ على قوالب Django الحالية.
- التركيز الأولي على صفحة غياب المعلم مع استهلاك نقاط /api/v1/attendance.

## كيفية التشغيل محليًا
1) backend: شغّل Django على http://127.0.0.1:8000.
2) frontend:
   - cd frontend
   - npm install
   - npm run dev
3) افتح المتصفح على http://localhost:5173 وانتقل إلى صفحة "غياب المعلم".

## روابط مفيدة
- نقاط API الحالية: /api/v1/attendance (students, records, bulk_save)
- إعدادات الراوتر والمداخل موجودة تحت src/app.

</div>