### محتويات بطاقات «مشرف الجناح» — تعريف حقول وعناصر التحكم وحالات العرض

آخر تحديث: 2025-10-31

الغرض: توحيد مواصفات البطاقات والشرائط والشارات التي تظهر لمشرف الجناح عبر الصفحات التالية، وربطها مباشرةً بنقاط خطة الاختبارات في DOC/WingSupervisor_TestPlan.md لضمان تغطية متسقة بين الواجهة الأمامية والـ API والاختبارات.

الصفحات المستهدفة:
- لوحة الغياب اليومية: /wing/attendance/daily
- طلبات الاعتماد: /wing/approvals
- إدارة الغيابات وتنبيهات الغياب: /wing/absences
- (اختياري) تصدير CSV

ملاحظات عامة (تنطبق على الصفحات الثلاث):
- توحيد الشارات الخاصة بحالة اليوم والحصص عبر CSS: frontend/src/styles/attendance-status.css، ووجود StatusLegend مرئي يشرح الدلالات اللونية والرمزية. [E2E-Daily-Cards] / [AX-Smoke]
- جميع الأزرار الأساسية تحمل aria-label واضحًا وتعمل بالكامل عبر لوحة المفاتيح. [AX-*]
- كل بطاقة تعرض العنوان المختصر، وصفًا صغيرًا أو تلميحًا، قيمًا رقمية مختصرة (KPI)، وشارات الحالة، وأزرارًا سريعة للفعل.
- في حال غياب البيانات: تظهر رسالة فارغة Empty State موحّدة داخل بطاقة أو فوق الشبكة وفق السياق.

---

1) لوحة الغياب اليومية (/wing/attendance/daily)
- الهدف: منح المشرف لمحة فورية عن مؤشرات حضور اليوم ضمن نطاق جناحه، مع القدرة على التنقل السريع إلى التفاصيل.
- مصادر البيانات (ملخص):
  - GET /api/v1/wing/overview/ → إجمالي السجلات، الملخصات المجمّعة، حالة الكاش. [IT-Overview-200] [IT-Overview-Cache]
  - GET /api/v1/wing/daily-absences/ → عناصر اليوم بالحقلين p1/p2 وstate. [IT-DailyAbs-200]
  - GET /api/v1/wing/entered/, /api/v1/wing/missing/ → إحصاءات الإدخال والاكتشاف الناقص. [IT-Entered-200] [IT-Missing-200]

- البطاقات والحقول:
  1. بطاقة «مؤشرات اليوم» (KPIs Top):
     - الحقول: total (إجمالي طلاب اليوم ضمن الجناح)، present, absent, excused, unexcused.
     - شارات: day-state موحدة الألوان (e.g., none/normal, warning, danger) بناءً على نسبة الغياب غير المبرر. [UT-Daily-Policy]
     - أزرار: «تحديث» يعيد جلب المؤشرات؛ رابط «التفاصيل» ينقل إلى جدول اليوم.
     - إمكانية الوصول: aria-live="polite" لتحديث القيم دون إرباك القارئ الآلي. [AX-Daily-Buttons]
  2. بطاقة «غيابات اليوم حسب الحصتين»:
     - الحقول في كل عنصر: student, class, p1 (state), p2 (state), state (خلاصة اليوم وفق السياسة: unexcused/excused/none). [UT-Daily-Policy]
     - الفلاتر: حسب الصف/الفصل، حالة اليوم، أو الحصة الأولى/الثانية.
     - أزرار: «تصدير CSV» عند التمكين (?format=csv). [IT-CSV-Exports]
  3. بطاقة «الإدخالات المنجزة/الناقصة»:
     - الحقول: entered.count, entered.items[] (اختيارية للعرض)، missing.count, missing.items[].
     - الشارات: success لعدد المُدخل، warning/attention للناقص.
     - أزرار سريعة: «انتقل لإكمال الإدخال» تنقل لصفحة المسؤول/المعلم المعني إن توفّر المسار.

- حالات وأخطاء:
  - لا بيانات: تعرض البطاقة «لا توجد بيانات حضور لهذا اليوم ضمن جناحك». [E2E-Daily-Cards]
  - أخطاء الشبكة/API: alert داخل البطاقة يوضح الخطأ ويعرض «إعادة المحاولة».
  - الأداء: احترام سقف 10k عنصر/يوم، واستخدام كاش قصير للـ overview مع إبراز شارة «Cached» اختيارية في UI. [UT-Perf-Cap] [IT-Overview-Cache]

---

2) طلبات الاعتماد (/wing/approvals)
- الهدف: تمكين مشرف الجناح من استعراض الطلبات المعلّقة واعتمادها/رفضها أو اعتبارها بعذر ضمن صلاحياته.
- مصادر البيانات:
  - GET /api/v1/wing/pending/ → قائمة المعلّق. [IT-Pending-200]
  - POST /api/v1/wing/decide/ → تنفيذ اعتماد/رفض وإرجاع {updated, action}. [IT-Decide-200]
  - POST /api/v1/wing/set-excused/ → تحديث الحالة وقفل السجل، مع دعم رفع مستند إثبات اختياري (صورة/ PDF). يقبل JSON أو multipart/form-data. الحقول: ids[], comment?, evidence(file)?, evidence_note?. [IT-Excused-200] [IT-Excused-Evidence]

- البطاقات/الجداول والحقول:
  1. بطاقة/جدول «طلبات اليوم»:
     - الأعمدة: student, class, date, period (daily/period), reason (إن وجد), submitted_by, submitted_at.
     - شارات: status (pending/approved/rejected) بألوان موحدة؛ excused (نعم/لا) بشارة ثانوية.
     - مفاتيح تحكم أعلى البطاقة: تبديل نمط العرض (daily ↔ period) مع حفظ الاختيار. [E2E-Approvals-Flow]
     - أزرار صفية: «اعتماد»، «رفض»، «اعتبار بعذر». تعرض Toast نجاح وتحدّث الصف. [E2E-Approvals-Flow]
     - RBAC: إخفاء/تعطيل الأزرار إن لم يكن للمستخدم دور مشرف الجناح. [UT-Approvals-RBAC]

- الوصولية:
  - رؤوس الجدول قابلة للفرز بلوحة المفاتيح، مع aria-sort وtabindex وتباين ألوان الشارات. [AX-Approvals-Table]

- حالات:
  - عند نجاح الفعل: تحديث الصف محليًا وإظهار رسالة ملائمة «تم اعتماد الطلب/رفضه…». [IT-Decide-200]
  - عند اعتبار بعذر: تتحول حالة السجل ويُقفل عن مزيد من التعديلات. [IT-Excused-200]

---

3) إدارة الغيابات وتنبيهات الغياب (/wing/absences)
- الهدف: حساب الأيام O/X وإصدار تنبيه رسمي للطالب ضمن العام الأكاديمي الحالي مع ترقيم فريد.
- مصادر البيانات:
  - GET /api/v1/attendance/absence/compute-days → يحسب O/X لفترة محددة. [IT-ComputeDays-200]
  - POST /api/v1/absence-alerts/ → إنشاء تنبيه يتضمن O/X ورقمًا سنويًا. [IT-Alerts-Create-200]
  - GET /api/v1/absence-alerts/{id}/docx → توليد ملف Word للتنبيه أو 404 عند غياب القالب. [IT-Alerts-Docx]

- بطاقات الصفحة:
  1. بطاقة «اختيار الطالب والفترة»:
     - الحقول: student (مطلوب)، term/date-range (مطلوب)، class.
     - أزرار: «احسب O/X». يعرض النتائج أسفل البطاقة. [E2E-Alerts-Issue]
  2. بطاقة «نتائج O/X»:
     - الحقول: total_days, O_count, X_count، وقائمة الأيام التفصيلية عند الحاجة.
     - شارات: O باللون القياسي الأخضر، X باللون القياسي الأحمر/العنّابي وفق الـ CSS الموحد. [AX-Alerts-Form]
     - أزرار: «إصدار تنبيه». [E2E-Alerts-Issue]
  3. بطاقة «بيانات التنبيه» بعد الإصدار:
     - الحقول: alert_no (ترقيم سنوي فريد مربوط بالعام الدراسي)، issued_at، الطالب/الصف.
     - روابط: «تنزيل Word» عبر endpoint docx. يظهر فقط عند نجاح الإنشاء. [IT-Alerts-Docx]

- حالات وأخطاء:
  - غياب قالب Word: يظهر تنبيه بالواجهة «القالب غير متوفر» ويتطابق مع 404 من الـ API. [IT-Alerts-Docx]
  - قواعد الترقيم: يُتحقق من فريدية الرقم ضمن العام الحالي. [UT-Alerts-Numbering]

---

4) CSV (اختياري)
- في الصفحات التي تدعم ذلك (خاصة daily-absences وentered/missing):
  - زر «تصدير CSV» يظهر عند التمكين ويستخدم نفس الفلاتر الحالية في الاستعلام. [IT-CSV-Exports] [E2E-CSV-Buttons]
  - عند النقر، يرسل نفس طلب GET مع ?format=csv ويفتح التنزيل.

---

5) اعتبارات الأداء والموثوقية
- سقف العناصر اليومية 10k، والواجهة قد تعرض رسالة «عرض جزئي» عند تجاوز العتبة أو تقترح فلترة إضافية. [UT-Perf-Cap]
- كاش overview بمهلة قصيرة (TTL)، مع إمكانية إظهار شارة صغيرة «Cached» للمعلومة البارزة حتى لا تُفاجئ القيم المتغيرة المستخدم. [IT-Overview-Cache]

---

6) الوصولية العامة (A11y)
- فحص axe دخاني للصفحات الثلاث لضمان خلوّها من الأخطاء الحرجة: أدوار landmarks، تسلسل تبويب منطقي، نصوص بديلة للأيقونات، وتباين ألوان الشارات. [AX-Smoke]
- الأزرار «تحديث» و«الانتقال» تحمل aria-label وتدعم Enter/Space. [AX-Daily-Buttons]
- رؤوس الجداول قابلة للفرز مع إعلانات حالة الفرز عبر aria-live أو aria-sort. [AX-Approvals-Table]

---

7) خريطة سريعة بين البطاقات والاختبارات (تعقب)
- Daily KPIs/Absences/Entered-Missing → [UT-Daily-Policy], [IT-Overview-200], [IT-DailyAbs-200], [IT-Entered-200], [IT-Missing-200], [E2E-Daily-Cards], [AX-Daily-Buttons]
- Approvals (Table + Actions) → [UT-Approvals-RBAC], [IT-Pending-200], [IT-Decide-200], [IT-Excused-200], [E2E-Approvals-Flow], [AX-Approvals-Table]
- Absence Alerts (Compute + Issue + Docx) → [UT-Alerts-Numbering], [IT-ComputeDays-200], [IT-Alerts-Create-200], [IT-Alerts-Docx], [E2E-Alerts-Issue], [AX-Alerts-Form]
- CSV Buttons → [IT-CSV-Exports], [E2E-CSV-Buttons]
- Perf/Cache → [UT-Perf-Cap], [IT-Overview-Cache]

---

ملاحظات تنفيذية للفريق
- حافظوا على توحيد أسماء الحقول في الواجهة مع استجابات الـ API المذكورة أعلاه لتقليل محولات البيانات.
- اجعلوا الشارات والألوان والـ Legend مشتركة بين الصفحات الثلاث لإحساس بصري موحد وتقليل الأكواد المكررة.
- غطّوا حالات عدم توفر الأجنحة للمستخدم برسالة تشخيصية ودية (كما في WingDashboard.vue) وتأكدوا من ظهورها في E2E.