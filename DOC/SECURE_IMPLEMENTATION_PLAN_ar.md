# خطة تنفيذ احترافية آمنة وفق أفضل الممارسات

> هذه الخطة التنفيذية موجهة للفريق لتطبيق المنصة بأعلى معايير الأمن والجودة والموثوقية. تعتمد على أطر OWASP ASVS/Top10، CIS Benchmarks، WCAG 2.1 AA، وممارسات DevSecOps العملية. تتضمن مراحل واضحة، مسؤوليات، ضوابط أمنية، معايير قبول، وقياسات نجاح.

---

## 1) المبادئ الأساسية
- الأمن بالتصميم وبالافتراض (Secure by Design & Default).
- بساطة قابلة للتوسع (KISS → Scale later).
- جودة مفروضة عبر الأنابيب (Pipelines enforce quality gates).
- الخصوصية أولًا: تقليل البيانات، التشفير، حوكمة الوصول.
- المراقبة الشاملة: Logs + Metrics + Traces + Alerts.
- قابلية الاستعادة: نسخ احتياطي مجدول + تمرينات استعادة.

## 2) نظرة معمارية مستهدفة
- Backend: Django + DRF (Modular Monolith، DDD مبسط).
- DB: PostgreSQL (UUID keys، فهارس حرجة، سياسات احتفاظ).
- Cache/Tasks: Redis + RQ/Channels.
- Frontend: Vite + Vue 3 + Pinia + Vue Router + Vue Query + i18n + PWA.
- Auth: JWT (Access قصير + Refresh HttpOnly) أو جلسات مع CSRF؛ يحدد بالبيئة.
- RBAC: أدوار وصلاحيات دقيقة قابلة للتوسع لكل وحدة (attendance, grades, timetable, notifications).
- مراقبة: Sentry (FE/BE) + Logging JSON + Health/Live probes.

## 3) خارطة تنفيذ على مراحل (عملي + آمن)

### المرحلة 0 — تشغيل آمن محليًا (Day 0–1)
- تشغيل Postgres/Redis عبر scripts/dev_up.ps1.
- تشغيل الباك والفرونت عبر scripts/dev_all.ps1.
- تمكين HTTPS dev (شهادة محلية) + /healthz و /livez.
- تهيئة ملفات .env (انظر الأمثلة المضافة) دون تخزين أسرار حقيقية في Git.
- DoD:
  - /admin و /healthz و /livez تعمل، HTTPS dev يعمل، لا أسرار حقيقية داخل المستودع.

### المرحلة 1 — الحوكمة والمعمارية (Day 2–3)
- فرونت: تثبيت pinia/vue-router/vue-query/vue-i18n/vee-validate/zod/vue-toastification/vite-plugin-pwa.
- إنشاء services/http.ts مع Interceptors (Token attach، Refresh، Retry backoff، معالجة الأخطاء).
- حراس Router + RBAC مبدئي (أدوار/صلاحيات من الباك أو Token claims).
- باك: تمكين DRF + SimpleJWT، إعداد CORS/CSRF، إعداد سياسات Password (Argon2id/Bcrypt).
- Linters/Formatters: eslint+prettier للفرونت، black/ruff/isort/flake8 للباك.
- DoD: بناء محلي بلا أخطاء لِنتر، هيكل مجلدات موحد، توثيق معماري مختصر.

### المرحلة 2 — i18n + RTL + الوصولية (Day 3–4)
- i18n: ar افتراضي، en احتياطي، تبديل dir ديناميكي.
- RTL: ضبط إطار الواجهة/الأدوات لدعم RTL بالكامل.
- A11y: تباين ألوان، تنقل لوحة مفاتيح، ARIA للمكونات، تركيز داخل الحوارات.
- DoD: axe-core خالٍ من المخالفات الحرجة، تبديل اللغات يعمل.

### المرحلة 3 — وحدة الحضور Pilot E2E (Day 5–9)
- نموذج Attendance + فهارس (class_id,date) و (student_id,date) + قيود فريدة.
- DRF ViewSet + فلاتر (date,classId) + Permissions (attendance:read/write).
- فرونت: صفحات/مكونات إدخال سريع + Vue Query بالتفاؤل + اختصارات P/A/L + Toasts.
- Offline: PWA + Workbox Queue لطلبات POST عند انقطاع الشبكة.
- Realtime: Channels/WebSocket أو بث مبسط لتحديث الشاشات.
- اختبارات: Backend (pytest) + Frontend (vitest) + مسار E2E أساسي.
- DoD: إدخال الحضور سريع، يصمد للأوفلاين، يزامن تلقائيًا.

### المرحلة 4 — الدرجات والجداول والإشعارات (Day 10–13)
- درجات: سير عمل draft → pending → published + RBAC + Audit log.
- Timetable: CRUD وفلاتر.
- Notifications: نموذج + Socket + واجهة شارات/Toasts.
- DoD: نشر درجات بموافقة، إشعارات فورية موثوقة.

### المرحلة 5 — الأمن والمراقبة (Day 10–14 بالتوازي)
- JWT: Access 10–15 دقيقة، Refresh قصير (7–14 يوم)، تدوير Tokens.
- Cookies: Secure + HttpOnly + SameSite.
- Headers: CSP، HSTS (إنتاج)، X-Frame-Options، X-Content-Type-Options، Referrer-Policy.
- Rate Limiting (nginx/DRF throttling)، CORS آمن بالمنشأ.
- Sentry FE/BE + Logging JSON مع request_id + structured user context.
- نسخ PostgreSQL مجدول + تمرين استعادة ربع سنوي.
- DoD: OWASP Top10 checks أساسية ناجحة، تنبيهات مفعلة، خطة نسخ مختبرة.

### المرحلة 6 — الأداء (بعد الأساسيات)
- Backend: فهارس دقيقة، select_related/prefetch_related، Caching للثوابت، Paginate افتراضيًا.
- Frontend: Lazy loading، Code splitting، ضبط cacheTime/staleTime، ضغط Brotli/Gzip.
- DoD: P95 API ≤ 300–400ms، تقليل TTI وحجم الحزم.

### المرحلة 7 — CI/CD (Day 7–14 تدريجيًا)
- GitHub Actions: Lint → Test → Security Scan → Build → Preview/Deploy.
- Secrets: GitHub Environments + Protected branches.
- Smoke tests بعد النشر.
- DoD: كل PR يُبنى ويُختبر تلقائيًا، Artefacts جاهزة، معاينات.

## 4) ضوابط أمنية مفصلة
- المصادقة: SimpleJWT، عدم تخزين Tokens طويلة في LocalStorage، تجديد صامت بواسطة Refresh HttpOnly.
- التفويض: RBAC على مستوى النطاق والكيان (Scope + Object constraints) مع حراس Router.
- المدخلات: Validation (zod/vee-validate) + Sanitization للحقول الغنية.
- الإخراج: Escaping سياقي في القوالب.
- نقل البيانات: HTTPS فقط، منع Mixed content، pin للمنشأ في CORS.
- التخزين: Encryption at rest (DB-level أو via cloud)، تجزئة كلمات المرور Argon2id.
- السجلات: JSON + إخفاء الحقول الحساسة، حدود احتفاظ مناسبة.
- التبعيات: فحص دوري (pip-audit, safety, npm audit) وتحديث ربع سنوي.

## 5) سياسة البيانات والخصوصية
- تصنيف: عام/داخلي/سري/سري للغاية.
- تقليل البيانات: لا تجمع ما لا تستخدمه.
- إخفاء الهوية للبيانات المستخدمة في التطوير والاختبار.
- حقوق الوصول: أقل امتياز، مراجعة فصلية.

## 6) النسخ الاحتياطي والاستعادة
- PostgreSQL: pg_dump ليلي + لقطات أسبوعية (حسب المنصة).
- تحقق استعادة ربع سنوي (Fire drill) موثّق بخطوات واضحة ومؤشرات RTO/RPO.

## 7) المراقبة والإنذارات
- Sentry: أخطاء FE/BE مع سياق المستخدم والإصدار.
- Healthz/Livez: تستخدم في CI والـ Load balancer.
- مقاييس: عدد الطلبات، زمن الاستجابة (P95)، أخطاء 5xx، طوابير RQ، مساحة القرص.
- تنبيهات: على الانحرافات (عتبات) وقنوات معتمدة.

## 8) معايير القبول (Definition of Done)
- أمن: 0 ثغرات حرجة في الفحص، رؤوس أمان مفعّلة، CORS آمن.
- جودة: linters خضراء، تغطية ≥ 70% للوحدات الحرجة، اختبارات أساسية تمر.
- موثوقية: نسخ احتياطي نشط + تمرين استعادة حديث.
- وثائق: محدثة (SECRETS_AND_ENV، README، OpenAPI).

## 9) المسارات والمهام العملية
- استكمل SECRETS_AND_ENV_ar.md وفق هذا الدليل.
- أضف backend/.env.example و frontend/.env.example (تم تضمينهما في المستودع كمثال).
- أضف GitHub Actions لاحقًا: .github/workflows/ci.yml (Lint/Test/Build/Security).
- أضف وحدة الحضور (backend/apps/attendance/ ... + frontend/src/modules/attendance/ ...).

## 10) مؤشرات قياس النجاح
- الأداء: P95 ≤ 300ms للواجهات الحرجة.
- الأخطاء: معدل 5xx ≤ 0.5%، أخطاء FE الحادة ≤ 2 لكل 1k جلسة.
- الأمن: 0 حرجة في الفحوص، تدوير مفاتيح نصف سنوي.
- الموثوقية: MTTR ≤ 4h، نجاح تمرين الاستعادة ربع سنوي.

— هذه الوثيقة مرجع عملي للتنفيذ؛ يجب تحديثها مع كل قرار معماري مهم ومع كل إطلاق رئيسي.