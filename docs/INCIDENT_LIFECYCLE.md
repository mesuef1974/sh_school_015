### دورة حياة الواقعة (البلاغ) — توثيق عملي احترافي

يوضّح هذا المستند كيف تعمل دورة حياة «الواقعة/البلاغ» في النظام من لحظة الإنشاء حتى الإغلاق، مع توضيح الأدوار والصلاحيات، نقاط الـ API، ما يحدث في الواجهة، وآليات الرؤية والتصفية. كما يتضمن قسمًا يبيّن ما اكتمل بالفعل وما تبقّى لتحسين المسار.

---

## دورة «من → إلى» (مختصر احترافي)
يوضّح هذا القسم دورة الحياة كاملة بأسلوب خطّي واضح — من نقطة البداية إلى النهاية — مع ذكر الهدف، الصلاحيات، نقاط الـ API، وأثر كل خطوة على البيانات وسجل التدقيق. التفاصيل الموسّعة لباقي الجوانب (النماذج، الرؤية، التشخيص… إلخ) تبقى بالأسفل.

1) إنشاء الواقعة
- الهدف: تسجيل واقعة (طالب/مخالفة/تاريخ/وصف).
- الصلاحية: incident_create.
- API: POST /api/v1/discipline/incidents/
- الأثر: severity ← violation.severity، و committee_required ← violation.requires_committee، وتسجيل Audit=create.

2) إرسال للمراجعة
- الهدف: نقلها من open إلى under_review.
- الصلاحية: incident_submit.
- API: POST /{id}/submit/
- الأثر: submitted_at=now()، Audit=submit.

3) الاستلام/المراجعة
- الهدف: تثبيت بدء المعالجة.
- الصلاحية: incident_review.
- API: POST /{id}/review/
- الأثر: reviewed_by/at، Audit=review.

4) إشعار وليّ الأمر (اختياري)
- الهدف: توثيق الإشعار (قناة + ملاحظة).
- الصلاحية: incident_notify_guardian.
- API: POST /{id}/notify-guardian/ { channel, note? }
- الأثر: يُضاف إلى actions_applied، Audit=notify_guardian.

5) التصعيد (قد يفعّل اللجنة)
- الهدف: تعليم الواقعة لتحتاج لجنة بسبب الشدة/التكرار/سياسة الكتالوج.
- الصلاحية: incident_escalate.
- API: POST /{id}/escalate/
- الأثر: escalated_due_to_repeat=true (عند التكرار)، وتفعيل committee_required، Audit=escalate.

6) اللجنة (عند الحاجة)
6.1) جدولة اللجنة (تشكيلها وحفظها)
- الصلاحية: incident_committee_schedule أو is_staff/superuser.
- API: POST /{id}/schedule-committee/ { chair_id, member_ids[], recorder_id? } أو use_standing=1 لاستخدام «اللجنة الدائمة».
- الأثر: حفظ committee_panel + إنشاء IncidentCommittee/IncidentCommitteeMember + ضبط committee_scheduled_by/at + Audit (meta.action=schedule_committee).

6.2) قرار اللجنة
- الصلاحية: incident_committee_decide أو is_staff/superuser.
- API: POST /{id}/committee-decision/ { decision: approve|reject|return, note?, actions?[], sanctions?[], close_now? }
- الأثر: Audit (meta.action=committee_decision)، ودمج الإجراءات/العقوبات، وإغلاق فوري إذا approve+close_now.

7) الإغلاق
- الصلاحية: incident_close.
- API: POST /{id}/close/
- الأثر: status=closed, closed_by/at، Audit=close.

8) التظلّم (اختياري)
- API: POST /{id}/appeal/ { reason? } → Audit=appeal.

9) إعادة الفتح (اختياري)
- API: POST /{id}/reopen/ { note? } → status=open، Audit=reopen.

ملاحظات سريعة:
- اللجنة لا تغيّر الحالة العامة (تظل ضمن open/under_review/closed) بل تضيف طبقة اعتماد أعلى.
- تُفعّل committee_required عند: شدة مرتفعة (3/4) أو Violation.requires_committee أو التصعيد.
- الأسماء تظهر دائمًا باسم الموظف الكامل Staff.full_name متى توفّر (ثم اسم المستخدم الكامل، ثم اسم المستخدم).

اختبار سريع (Quick‑Start)
1) migrate discipline → 2) إنشاء واقعة → 3) إرسال → 4) استلام → 5) (اختياري) تصعيد → 6) جدولة لجنة (أو use_standing) → 7) قرار لجنة (close_now=true للتجربة) → 8) مراجعة /summary و/overview وسجل التدقيق.

معايير القبول (Acceptance)
- انتقالات الحالة والتدقيق متسقة، و/summary يطابق الجدول عند نفس الفلاتر.
- تظهر أسماء الموظفين كاملة.
- use_standing يعمل ويملأ التشكيل من «اللجنة الدائمة» تلقائيًا.

---

#### 1) نموذج البيانات بإيجاز
- النموذج: `discipline.Incident`
  - الحقول المهمة:
    - `status`: حالات العمل: `open | under_review | closed`
    - `occurred_at`، وبديل العرض/الترشيح: `event_date = COALESCE(date(occurred_at), date(created_at))`
    - تتبّع دورة الحياة: `submitted_at`, `reviewed_by`, `reviewed_at`, `closed_by`, `closed_at`
    - الإغناء: `severity`, `committee_required`, `actions_applied` (JSON), `sanctions_applied` (JSON)
  - فهارس وترتيب افتراضي حسب التاريخ.

#### 2) الأدوار والصلاحيات
- الخادم يفرض الصلاحيات من خلال Codenames مخصّصة على النموذج:
  - `discipline.incident_create`، `incident_submit`، `incident_review`، `incident_notify_guardian`، `incident_escalate`، `incident_close`.
- رؤية البيانات (scoping):
  - موظفو النظام/المشرفون: رؤية عامة.
  - «مشرف الجناح»: يرى وقائع فصول الأجنحة التي يشرف عليها. يدعم الربط عبر:
    - `Wing.supervisor` (Staff)، أو `Wing.supervisor_user` (User)، أو `Wing.supervisor_id` (عام)
    - كمسار احتياطي: إذا كان المستخدم ضمن مجموعة `wing_supervisor/supervisor` ومرّر `wing_id` يتم السماح بالنطاق المطلوب.
  - بقية المستخدمين غير المصرّح لهم: يرون ما قاموا هم بالإبلاغ عنه فقط.

#### 3) الحالات والانتقالات (Workflow)
الحالات الأساسية:
- Open (افتراضي بعد الإنشاء)
- Under Review (بعد الإرسال/الاستلام)
- Closed (بعد الإغلاق)

العمليات المتاحة وزمن الانتقال:
- Submit → يضع الواقعة في `under_review` ويملأ `submitted_at`.
- Review → يبقيها في `under_review` مع ضبط `reviewed_by/at`.
- Notify guardian → يسجل عنصرًا في `actions_applied` (مع قناة ونص)، لا يغيّر الحالة.
- Escalate → يسجّل التصعيد (قد يستخدم لاحقًا لتفعيل لجنة)، لا يغيّر الحالة افتراضيًا.
- Close → يغيّر الحالة إلى `closed` ويملأ `closed_by/at`.
- Appeal → يسجّل سبب التظلّم في `actions_applied`، لا يغيّر الحالة.
- Reopen → يعيد الحالة إلى `open` (يُستخدم بعد التظلّم أو لأسباب وجيهة).

ملاحظة حول «اللجنة»: عند تصعيد الواقعة أو عندما تكون شدة المخالفة مرتفعة (عادةً 3 أو 4)، أو إذا كانت المخالفة في الكتالوج موسومة بأنها تتطلب لجنة (`Violation.requires_committee = true`)، يتم تفعيل علامة `committee_required` على الواقعة. هذا يعني أن الواقعة تحتاج إحالة/عرضًا على لجنة الانضباط المدرسية لاعتماد القرار قبل الإغلاق النهائي. لا تغيّر هذه العلامة حالة الواقعة بحد ذاتها، لكنها تؤثّر على مسار الاعتماد.

##### مسار «اللجنة» — توضيح مهني وبرمجي
يوضح هذا القسم «ما هي اللجنة»، «ممن تتكوّن»، و«كيف تُتخذ القرارات» مع ربط ذلك بسير العمل البرمجي الحالي والمقترح.

- وظائف اللجنة (وظيفيًا):
  - مراجعة الوقائع ذات الأثر العالي (عادةً شدة 3 أو 4) أو الوقائع الموسومة بأنها تتطلب لجنة.
  - سماع الأطراف المعنية (مربّي الصف/الطالب/الوليّ) حسب السياسة.
  - اتخاذ قرار مهني نهائي بالتوصية بإجراءات أو عقوبات، أو إعادة الواقعة للمزيد من الاستيضاح.
  - توثيق قرارها وأسبابه، واعتماده قبل الإغلاق النهائي.

- تركيبة اللجنة (حوكمة):
  - قوام: 3–5 أعضاء.
  - الأدوار: رئيس اللجنة (Chair)، أعضاء (Members)، مقرر/كاتب محضر (Recorder).
  - النصاب: 3 أعضاء على الأقل (بمن فيهم الرئيس).
  - تضارب المصالح: يُستبعد أي عضو لديه علاقة مباشرة بالواقعة/الطالب.

- آلية اتخاذ القرار:
  - تصويت بالأغلبية البسيطة للأعضاء الحاضرين.
  - عند التعادل يُرجّح صوت الرئيس.
  - مخرجات القرار: `approve` (اعتماد توصية الإجراء/العقوبة)، `reject` (رفض المقترح)، `return` (إعادة للمراجعة/استيضاح بملاحظات محددة).
  - يتم توثيق الأسباب والاعتبارات في المحضر.

- ماذا يعني ذلك برمجيًا في النظام الحالي:
  - لدينا اليوم علم `committee_required` على نموذج Incident يُنبّه بأن الواقعة تحتاج مسار لجنة قبل الإغلاق.
  - لا يوجد (حتى الآن) «حالة لجنة» منفصلة داخل الواقعة؛ أي أن الحالة العامة تبقى ضمن `open/under_review/closed` بينما تعمل اللجنة ضمن مستوى «اعتماد أعلى» فوق حالة `under_review`.

- تصميم برمجي مقترح خفيف (اختياري للتفعيل لاحقًا):
  - حقول قراءة/توثيق على Incident (لا تغيّر الحالة العامة):
    - `committee_status`: `none | pending | scheduled | decided`
    - `committee_decision`: `approve | reject | return | null`
    - `committee_notes`: نص حر لملخص القرار/المبررات.
    - `committee_decided_at`: تاريخ ووقت اعتماد القرار.
    - `committee_panel`: JSON يُسجّل رئيس وأعضاء اللجنة الحاضرين.
  - نقاط API مساندة: (غير مفعّلة حاليًا — للتوسعة المستقبلية دون كسر التوافق)
    - POST `/api/v1/discipline/incidents/{id}/schedule-committee/`
      - body اختياري: `{ when?: 'YYYY-MM-DDTHH:MM', panel?: { chair: {id,name}, members: [...] } }`
      - الأثر: تعيين `committee_status=pending|scheduled` وتخزين panel المقترح.
    - POST `/api/v1/discipline/incidents/{id}/committee-decision/`
      - body: `{ decision: 'approve'|'reject'|'return', notes?: string, panel?: {...} }`
      - الأثر: تعيين `committee_status='decided'`, `committee_decision`, `committee_notes`, `committee_decided_at=now()`، وتسجيل ذلك في سجل التدقيق.
  - التكامل مع دورة الحالة العامة:
    - عند `committee_decision='approve'` يمكن لمراجع L2 استكمال الإغلاق عبر `close/` بعد تنفيذ/إسناد الإجراءات.
    - عند `return` تبقى الواقعة `under_review` مع ملاحظات اللجنة.
    - عند `reject` قد تُعاد صياغة الإجراء المقترح أو تُغلق دون عقوبة وفق السياسة.

ملاحظة مهمة: الإطار أعلاه «توضيحي» ومُوثّق لتمكين الفريق من اتخاذ قرار تفعيل مسار اللجنة لاحقًا بأقل تغييرات. السلوك الحالي يكتفي بعلم `committee_required` مع شرح واضح في الواجهة والتوثيق، دون فرض خطوات إضافية.

قواعد السماحية في الواجهة (إرشادية؛ الخادم يتحقق فعليًا):
- Submit: فقط من `open` → `under_review`
- Review: متاحة إذا لم تكن `closed`
- Notify: في `open` أو `under_review`
- Escalate: في `under_review`
- Close: في `open` أو `under_review`
- Appeal/Reopen: عندما تكون `closed`

#### 4) واجهات API ذات الصلة
- عرض الوقائع ضمن نطاق الرؤية والفلاتر:
  - GET `/api/v1/discipline/incidents/visible/?expand=all&wing_id=...&from=YYYY-MM-DD&to=YYYY-MM-DD&status=...&q=...&limit=&offset=`
  - الاستجابة: `{ total, items, limit, offset }` مع تمثيل غني `IncidentFullSerializer` عند `expand=all`.
  - تطبيع الحالة: تقبل مرادفات الواجهة `in_progress→under_review` و`resolved/archived→closed`.
  - الترتيب: `-occurred_at, -created_at`.

- ملخّص KPIs متسق مع visible:
  - GET `/api/v1/discipline/incidents/summary/` → `{ total, by_status, by_severity }`
  - يطبّق نفس سياسة الرؤية والفلاتر ونفس تطبيع الحالة والتاريخ المشتق `event_date`.

- نظرة عامة موسّعة (اختيارية للمشرفين):
  - GET `/api/v1/discipline/incidents/overview/?days=7|30`
  - تعيد: `{ since, totals, by_status, by_severity, top_violations, overdue }`
  - ملاحظة: تختلف عن `/summary/` بأنها تضيف أكثر المخالفات تكرارًا ومؤشرات تجاوز مهلة المراجعة/الإشعار. تبقى `/summary/` هي المرجع لعدادات الصفحة الأساسية.

- تصدير بيانات الأدمن (للموظفين فقط):
  - GET `/api/v1/discipline/incidents/admin-export/` → `{ total, items, ... }` (تمثيل كامل)

- الإجراءات (Transitions):
  - POST `/api/v1/discipline/incidents/{id}/submit/`
  - POST `/api/v1/discipline/incidents/{id}/review/`
  - POST `/api/v1/discipline/incidents/{id}/notify-guardian/` (body: `{ channel, note }` اختياري)
  - POST `/api/v1/discipline/incidents/{id}/escalate/`
  - POST `/api/v1/discipline/incidents/{id}/close/`
  - POST `/api/v1/discipline/incidents/{id}/appeal/` (body: `{ reason }`)
  - POST `/api/v1/discipline/incidents/{id}/reopen/` (body: `{ note }`)

#### 5) ما تفعله الواجهة (صفحة وقائع الجناح)
- الملف: `frontend/src/features/wings/pages/WingIncidents.vue`
  - يجلب البيانات من `/visible/` مع `expand=all` ويعرض جدولًا شاملًا للحقول، مع صف تفصيلي موسّع.
  - فلاتر: من/إلى/الحالة/بحث، وتصفّح limit/offset.
  - عمود «عمليات» ينفّذ الأزرار المذكورة أعلاه ويحدّث الصف من استجابة الخادم، مع إدارة «حالة انشغال» لكل صف وتوستات عربية.

#### 6) الرؤية والتصفية بعمق
- الرؤية:
  - تحديد أجنحة المستخدم المشرف عليها عبر (Staff/Wing) بمختلف الحقول المدعومة.
  - في حال عدم وجود ربط صريح ولكن المستخدم ضمن مجموعة `wing_supervisor/supervisor` ومرّر `wing_id`، يتم القصر على هذا الجناح كمسار احتياطي.
  - المستخدم العادي: يرى ما أبلغ عنه فقط.
- التاريخ: يعتمد النظام على `event_date = date(occurred_at) OR date(created_at)` لتفادي فقد السجلات القديمة التي تخلو من `occurred_at`.
- الحالة: يتم تطبيع مرادفات الواجهة.
- الصف/الجناح: يمكن فلترة `class_id`/`wing_id`، مع احترام نطاق الإشراف.
- البحث: على `narrative/location/violation(category,code)/student.full_name`.

#### 7) أدوات التشخيص (لتحديد «أين المشكلة»)
- GET `/api/v1/discipline/incidents/diagnostics/` يعيد لقطات أعداد بعد كل مرحلة فلترة، والأجنحة المكتشفة.
- سكربت جاهز: `scripts/diag_incidents.ps1` يحفظ أربع استجابات JSON (admin-export, visible, summary, diagnostics) تحت `backend/.runtime/diag/`.

---

### ما الذي اكتمل بالفعل
- توحيد سياسة الرؤية بين `visible` و`summary`، مع دعم مشرف الجناح سواء بالربط الصريح أو عبر المجموعة + `wing_id`.
- تطبيع مرادفات الحالة في جميع النهايات (`visible`, `summary`, `admin-export`).
- اعتماد `event_date` لضمان شمول السجلات بلا `occurred_at` في العدّ والجداول.
- صفحة «وقائع الجناح» مبسّطة وشاملة الأعمدة، مع صف تفصيلي موسّع، وفلاتر وتصفح، وربط كامل لدورة الحياة.
- تنفيذ عمليات الدورة: إرسال، استلام، إشعار ولي الأمر، تصعيد، إغلاق، تظلّم، إعادة فتح — مع تحديث الصف فورًا.
- نقطة تصدير الأدمن JSON، ونقطة تشخيص مفصلة، وسكربت تجميعي للتشخيص.

معلومة للمستخدمين: يظهر في الجدول عمود «لجنة؟». عندما تظهر القيمة «نعم»، فهذا يعبّر عن أن الواقعة تتطلب إحالة للجنة الانضباط، وغالبًا يحدث ذلك في الحالات التالية:
- شدة المخالفة مرتفعة (3 أو 4)؛ يتم تفعيل `committee_required` تلقائيًا عند الشدة العالية.
- تم إجراء «تصعيد» على الواقعة (مثلًا بسبب تكرار مخالفات الطالب)، فيتم تفعيل العلم كجزء من سياسة الانضباط.
- المخالفة نفسها في الكتالوج موسومة بأنها تحتاج لجنة (`Violation.requires_committee`).

هذه العلامة لا تغيّر حالة الواقعة (ما تزال ضمن `open/under_review/closed`) لكنها تنبّه الفريق إلى ضرورة اتخاذ مسار اعتماد أعلى/لجنة قبل إغلاقها نهائيًا.

### ما الذي تبقّى/تحسينات مقترحة (اختيارية)
1) «مسار لجنة» رسمي: عند `committee_required`، تعريف خطوات/اعتمادات إضافية وربطها بـ `escalate` وقرارات اللجنة.
   - تفعيل الحقول المقترحة أعلاه وإنشاء هجرتِها ونقطتَي API (`schedule-committee`, `committee-decision`).
   - إضافة شارات قراءة فقط في واجهة الجناح لحالة اللجنة وقرارها.
   - تمهيد صلاحيات مسار اللجنة ضمن مجموعة جاهزة اسمها «اللجنة السلوكية». انظر قسم الصلاحيات أدناه.
2) مرفقات وشواهد: دعم رفع ملفات/صور وربطها بالواقعة، وسياسة صلاحيات/إخفاء.
3) ضبط SLA آليًا: إنفاذ مهلة الاستلام/الإشعار برسائل تنبيهية وتنبيهات للمتأخرات (مع tasks/cron).
4) قوالب إشعارات: قنوات SMS/اتصال/داخلي مع قوالب عربية موحّدة وتتبّع حالة التسليم.
5) سجل تدقيق (Audit log): تتبّع كل تغيير حالة/حقل مع من/متى ولماذا.
6) تصدير CSV/Excel: زر في الواجهة يستدعي `admin-export` أو `visible` وفق الصلاحيات، مع نفس الفلاتر.
7) مؤشرات KPIs في الصفحة: شريط أعلى يعرض إجماليات من `/summary/` متطابقة مع الجدول.
8) كانبان/لوحة متابعة: عرض بصري حسب الحالة/الشدة مع سحب وإفلات (إن لزم للمعالجة السريعة).
9) مصفوفة صلاحيات UI أوضح: إظهار/إخفاء الأزرار حسب `caps` من `/api/school/me` لتجربة أدق.
10) اختبارات تكامل: سيناريوهات تغطي الرؤية، التاريخ، التطبيع، والتحولات لضمان عدم تراجع السلوك مستقبلًا.

---

### روابط سريعة (للمطورين)
- Backend
  - Views: `backend/discipline/views.py` (إجراءات visible/summary/admin-export/diagnostics + التحولات)
  - Serializers: `backend/discipline/serializers.py` (`IncidentSerializer` و`IncidentFullSerializer`)
  - Models: `backend/discipline/models.py` (Incident/Violation/BehaviorLevel)
  - School models (الأجنحة/الموظفون): `backend/school/models.py` (Staff/Wing)
- RBAC: تُنشئ الهجرة `discipline/0004_committee_group.py` مجموعة «اللجنة السلوكية» مع صلاحياتها.
- Frontend
  - صفحة الجناح: `frontend/src/features/wings/pages/WingIncidents.vue`
  - واجهات الانضباط: `frontend/src/features/discipline/api.ts`
- أدوات تشغيل/تشخيص
  - سكربت التطوير: `scripts/dev_all.ps1`
  - تشخيص الوقائع: `scripts/diag_incidents.ps1`

---

إن رغبت بإضافة أي من «التحسينات المقترحة» أعلاه، أخبرنا بالأولوية لنقوم بتنفيذها بتغييرات صغيرة ومتدرجة، مع الحفاظ على التوافق مع ما تمّ إنجازه.

---

### تحديث هام — إزالة «مجموعة اللجنة السلوكية» واستبدالها بجداول مخصّصة
- تم التخلص من مجموعة «اللجنة السلوكية» نهائيًا داخل auth.groups وكل ما يتبعها.
- بدلاً من ذلك، تمت إضافة جداول متخصصة لإدارة تشكيل اللجنة لكل واقعة:
  - IncidentCommittee: رئيس اللجنة، المقرر، من قام بالجدولة ومتى.
  - IncidentCommitteeMember: أعضاء اللجنة المرتبطون بتلك الواقعة.
- تبقى صلاحيات نموذج Incident موجودة للاستخدام في ضبط الوصول: `incident_committee_view`, `incident_committee_schedule`, `incident_committee_decide` (لا تتطلب عضوية مجموعة).

هجرات ذات صلة:
- `discipline/0008_incident_committee_models.py`: إنشاء الجداول الجديدة.
- `discipline/0009_backfill_committee_from_panel.py`: تهجير أي بيانات قديمة من الحقل JSON `committee_panel` إلى الجداول الجديدة.
- `discipline/0010_remove_committee_group.py`: إزالة مجموعة «اللجنة السلوكية» إن وُجدت أو وسمها Deprecated عند وجود أعضاء.

كيفية التطبيق محليًا:
1) شغّل الهجرات: `python manage.py migrate discipline`
2) لا حاجة لإدارة مجموعات؛ الوصول محكوم بصلاحيات نموذج Incident أو بأعلام `is_staff/superuser`.

### آلية احترافية لاختيار الرئيس والأعضاء (Backend-only)
تم نقل «تشكيل اللجنة» إلى الباكند بالكامل عبر جداول IncidentCommittee/IncidentCommitteeMember، مع توفير أدوات بحث احترافية من الخادم، ودعم الحفظ في سجل الواقعة.

- GET `/api/v1/discipline/incidents/{id}/committee-suggest/?member_count=2&exclude=12,34`
  - member_count: عدد الأعضاء المطلوب اقتراحهم (بدون الرئيس)، المدى 2..4 (إجمالي 3..5). افتراضي 2.
  - exclude: قائمة CSV لمعرفات مستخدمين لاستبعادهم (مثلاً لتضارب مصالح). يتم استبعاد المبلّغ تلقائيًا.

قواعد الاقتراح:
- مصدر المرشحين: جميع موظفي المدرسة (Staff) الذين لديهم حساب User مرتبط. برمجيًا يتم جمع `Staff.user_id` غير الفارغ.
- يتم ترتيب المرشحين ترتيبًا ثابتًا باستخدام تجزئة SHA256 على `(incident_id:user_id)` لضمان عدالة وتوزيع عبر القضايا بمرور الوقت (Deterministic stable selection).
- تُستبعد المعرفات في exclude والمبلّغ من كل المجاميع.
- لا توجد مجموعات أدوار فرعية؛ التشكيل المقترح يوزّع الأدوار (رئيس/أعضاء/مقرر) من نفس المجمّع بشكل حتمي.

الاستجابة:
```
{
  "panel": {
    "chair": { "id": 7, "username": "chair1", "full_name": "..." },
    "members": [ {"id": 9, ...}, {"id": 11, ...} ],
    "recorder": { "id": 18, ... } | null
  },
  "pools": { "chairs": 3, "members": 8, "recorders": 2 },
  "algorithm": "stable_hash_v1"
}
```

حقول إضافية لتحديد الصلاحيات بدقة في الاستجابة:
- access_caps: قدرات المستخدم الحالي على مسار اللجنة (لتمكين/تعطيل أزرار الواجهة)
  - can_schedule: هل يملك صلاحية إحالة الواقعة للجنة (incident_committee_schedule)
  - can_decide: هل يملك صلاحية تسجيل قرار اللجنة (incident_committee_decide)
  - is_committee_member: هل هو عضو في مجموعة «اللجنة السلوكية»
  - is_staff/is_superuser: أعلام Django القياسية
- role_powers: توصيف مرجعي لأدوار اللجنة وما يُتوقع منها برمجيًا:
  - chair: ["view", "schedule", "decide"]
  - member: ["view"]
  - recorder: ["view", "record_notes"]

ملاحظات تشغيلية:
- هذه نقطة مساعدة للاقتراح فقط.
- الوصول مقصور على من يملك `incident_committee_schedule` أو `incident_committee_decide` أو من هو `is_staff/superuser`.

#### بحث مرشّحي اللجنة (احترافي — من الخادم)
- GET `/api/v1/discipline/incidents/{id}/committee-candidates/?q=&limit=25&offset=0`
  - q: نص البحث (يدعم Staff.full_name وjob_title وrole واسم المستخدم واسم المستخدم الكامل).
  - limit/offset: ترقيم صفحات (حد أعلى 100).
  - المصدر: جميع موظفي المدرسة المرتبطين بحساب User (Staff.user).
  - الوصول: incident_committee_view/schedule/decide أو is_staff/superuser.
  - الاستجابة: `{ items: [{id, username, full_name, staff_full_name, job_title, role}], total, limit, offset }`، بترتيب حتمي مستقر بحسب الواقعة.

#### حفظ تشكيل اللجنة (Backend-only)
- POST `/api/v1/discipline/incidents/{id}/schedule-committee/`
  - جسم الطلب JSON:
    ```json
    { "chair_id": 12, "member_ids": [34,56], "recorder_id": 78 }
    ```
  - قواعد التحقق:
    - صلاحية `incident_committee_schedule` أو is_staff/superuser.
    - رئيس إجباري، أعضاء عددهم ≥ 2، تمييز الأدوار (لا تكرار).
    - المستخدمون المختارون يجب أن يكونوا موظفين (سجلات Staff مع User مرتبط).
  - التأثير:
    - يحفظ التشكيل داخل حقول الواقعة: `committee_panel = {chair_id, member_ids[], recorder_id}`.
    - يحدّث `committee_required = true` ويضبط `committee_scheduled_by/at`.
    - يسجّل في سجل التدقيق IncidentAuditLog مع `meta.action = schedule_committee`.
  - الاستجابة: `{ ok: true, incident: IncidentFullSerializer, saved_panel }`.

ملاحظة: تم إزالة زر «تشكيل اللجنة» من الواجهة الحالية. التشكيل يتم عبر الباكند والنهايات أعلاه، ويمكن لاحقًا إضافة شاشة إدارة مخصّصة للأدمن إن دعت الحاجة.

---

## اللجنة السلوكية الدائمة (Standing Committee)
للاستجابة لمتطلب «أريدها لجنة دائمة وليس لكل بلاغ»، تمت إضافة «لجنة سلوكية دائمة» على مستوى النظام بحيث:
- يتم اختيار «رئيس اللجنة الدائم» و«أعضاء دائمون» و«مقرر دائم» مرّة واحدة فقط.
- يمكن إعادة استخدام هذا التشكيل تلقائيًا عند جدولة أي واقعة للجنة عبر خيار use_standing.

### نماذج قاعدة البيانات
- StandingCommittee: يحفظ الرئيس والمقرر وملاحظات عامة مع طوابع زمنية.
- StandingCommitteeMember: جدول الأعضاء الدائمين (باستثناء الرئيس)، مرتبط بـ StandingCommittee.

الهجرة ذات الصلة: `discipline/0011_standing_committee_models.py`

### واجهات API
- GET `/api/v1/discipline/incidents/committee-standing/`
  - الوصول: incident_committee_view أو is_staff/superuser.
  - يعيد مثالًا (JSON صالح):
    ```json
    {
      "panel": {
        "chair": { "id": 12, "username": "chair1", "full_name": "الاسم الكامل", "staff_full_name": "اسم الموظف" },
        "members": [ {"id": 34, "username": "m1"}, {"id": 56, "username": "m2"} ],
        "recorder": { "id": 78, "username": "rec1" }
      },
      "exists": true
    }
    ```

- POST `/api/v1/discipline/incidents/committee-standing/`
  - الوصول: incident_committee_schedule أو is_staff/superuser.
  - جسم الطلب:
    ```json
    { "chair_id": 12, "member_ids": [34,56], "recorder_id": 78, "notes": "اختياري" }
    ```
  - قواعد التحقق: رئيس إلزامي، عضوان على الأقل، لا تكرار بين الأدوار، وكلهم موظفون (Staff.user).
  - التأثير: يحفظ التشكيل الدائم ويستبدل قائمة الأعضاء بالكامل.

### استخدام اللجنة الدائمة أثناء جدولة واقعة
- POST `/api/v1/discipline/incidents/{incident_id}/schedule-committee/?use_standing=1`
  - أو تمرير `{"use_standing": 1}` داخل جسم الطلب.
  - إن لم يُرسل جسم كامل للرئيس/الأعضاء/المقرر، سيتم تعبئة التشكيل تلقائيًا من اللجنة الدائمة وحفظه في الواقعة.
  - تبقى نفس قواعد التحقق والصلاحيات سارية.

### ملاحظات تشغيلية
- ما يزال بإمكان المسؤول تمرير تشكيل مخصص لواقعة بعينها؛ خيار use_standing اختياري ويُسهل إعادة استخدام التشكيل الدائم.
- أسماء العرض ترجع «اسم الموظف» من جدول Staff إن وجد، وإلا تُستخدم أسماء المستخدم الكاملة.
- لا توجد مجموعات RBAC خاصة باللجنة؛ الوصول محكوم بصلاحيات نموذج Incident أو is_staff/superuser.

---

## بعد «التصعيد» وتحويل الواقعة إلى اللجنة — ماذا بعد؟
عند الحاجة إلى لجنة، يمرّ المسار العملي بالخطوات التالية:

1) جدولة اللجنة (تشكيلها وحفظها)
- POST `/api/v1/discipline/incidents/{incident_id}/schedule-committee/`
  - إمّا تمرير التشكيل صراحة أو استخدام اللجنة الدائمة `?use_standing=1`.
  - الأثر: حفظ التشكيل داخل الواقعة وفي جداول IncidentCommittee/IncidentCommitteeMember، وتسجيل أثر تدقيقي.

2) انعقاد اللجنة واتخاذ القرار
- بعد اجتماع اللجنة، سجّل القرار برمجيًا عبر نقطة جديدة:
- POST `/api/v1/discipline/incidents/{incident_id}/committee-decision/`
  - صلاحيات: `incident_committee_decide` أو `is_staff/superuser`.
  - جسم الطلب (JSON):
    ```json
    {
      "decision": "approve|reject|return",
      "note": "ملاحظات القرار (اختياري)",
      "actions": ["إجراء 1", "إجراء 2"],
      "sanctions": ["عقوبة 1"],
      "close_now": true
    }
    ```
  - السلوك:
    - يسجل أثر تدقيق meta.action = `committee_decision` مع تفاصيل القرار.
    - يضيف أي إجراءات/عقوبات ممررة إلى حقول الواقعة `actions_applied/sanctions_applied`.
    - إن كانت `decision=approve` ومع `close_now=true`، تُغلق الواقعة فورًا (ضبط `closed_by/closed_at` وتسجيل أثر إغلاق).
  - الاستجابة: `{ ok: true, incident: IncidentFullSerializer }`.

3) إشعار وليّ الأمر (إن اقتضت السياسة)
- قد يتم إشعار وليّ الأمر بنتيجة اللجنة: `POST /api/v1/discipline/incidents/{id}/notify-guardian/` مع قناة الإشعار.

4) إغلاق الواقعة (إن لم يُغلق تلقائيًا)
- إذا لم يُستخدم `close_now` مع الموافقة، يمكن الإغلاق لاحقًا: `POST /api/v1/discipline/incidents/{id}/close/`.

5) التظلّم ثم إعادة الفتح (اختياري)
- يتيح النظام تقديم تظلّم ثم إعادة فتح وفق السياسات: `appeal` ثم `reopen`.

ملاحظات تشغيلية:
- يُفضّل استخدام `committee-candidates` للبحث عن المرشحين، أو `committee-suggest` للاقتراح الحتمي قبل الحفظ.
- تُعاد أسماء الموظفين كاملة عبر `staff_full_name` في كل النهايات ذات الصلة.
