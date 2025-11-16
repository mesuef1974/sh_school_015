### دورة حياة الواقعة (البلاغ) — توثيق عملي احترافي

يوضّح هذا المستند كيف تعمل دورة حياة «الواقعة/البلاغ» في النظام من لحظة الإنشاء حتى الإغلاق، مع توضيح الأدوار والصلاحيات، نقاط الـ API، ما يحدث في الواجهة، وآليات الرؤية والتصفية. كما يتضمن قسمًا يبيّن ما اكتمل بالفعل وما تبقّى لتحسين المسار.

---

## الوضع الحالي مقابل الوضع المطلوب (Executive Summary)

- الوضع الحالي (Implemented):
  - دورة حياة كاملة «إنشاء → إرسال → استلام/مراجعة → إشعار وليّ الأمر → تصعيد → لجنة (عند الحاجة) → إغلاق → تظلّم/إعادة فتح». جميع النهايات البرمجية موجودة وموثّقة أدناه.
  - تفعيل committee_required يتم حسب شدة المخالفة/سياسة الكتالوج أو التصعيد.
  - توثيق «من الذي يَجدول اللجنة» مع ختم committee_scheduled_by/at.
  - سياسة «اللجنة الدائمة فقط» مفعّلة افتراضيًا: عند جدولة أي لجنة لواقعة، تُستخدَم «اللجنة السلوكية الدائمة» حصريًا، ويُتجاهَل أي تشكيل مخصّص يُرسل من العميل. يمكن إيقاف ذلك عبر إعدادات الخادم إن لزم.
  - جدولة تلقائية للجنة عند الإرسال: إذا استوفت الواقعة شرط اللجنة (حسب السياسة/الشدة/التكرار) ولم تكن مجدولة، يقوم الخادم تلقائيًا بجدولتها على «اللجنة الدائمة» أثناء submit دون الحاجة لأي تدخل يدوي. تُحفَظ تشكيلة اللجنة في incident.committee_panel، وتُنشأ سجلات IncidentCommittee/IncidentCommitteeMember، وتُمنَح صلاحيات عرض/قرار خفيفة للمشاركين، مع تسجيل تدقيق.

- الوضع المطلوب (To‑Be — مؤتمت احترافيًا):
  - تفعيل «سياسة إجراء آلية لكل مخالفة» بحيث:
    1) عند التسجيل الأول لمخالفة قليلة الشدة (Level 1) يتم تطبيق أو اقتراح «تنبيه شفهي من المعلم» تلقائيًا.
    2) عند التكرار ضمن نافذة زمنية محددة، ترتقي الإجراءات والعقوبات تدريجيًا (إنذار خطي، اتصال بولي الأمر، حرمان نشاط… إلخ).
    3) عند بلوغ حدّ تكرار/شدة معيّن، يتم تفعيل committee_required تلقائيًا وإحالة الواقعة للجنة.
  - إبراز هذه السياسة شفّافًا في التمثيل المقروء للواقعة وفي التقارير.
  - المحافظة على قابلية الضبط لكل مخالفة على حدة مع نافذة زمنية للتكرار.

ملاحظة مهمة: هذا المستند يضم مواصفات جاهزة للتنفيذ فوريًا دون كسر توافق واجهات الـ API، عبر استخدام حقل Violation.policy. التنفيذ البرمجي للتطبيق/الاقتراح يمكن تشغيله تدريجيًا بفلاغ إعدادات.

---

## دورة حياة الواقعة مع «اللجنة الدائمة فقط» — معيار احترافي

ينفّذ النظام مسار لجنة السلوك حصريًا عبر «اللجنة السلوكية الدائمة» وفق أفضل الممارسات الحوكمية. لا تُستخدم أي لجان بديلة أو تشكيلات مخصّصة عند التفعيل الافتراضي لهذه السياسة.

إعداد التحكم:
- DISCIPLINE_ONLY_STANDING_COMMITTEE = true (افتراضي)
  - true: يُفرَض استخدام اللجنة الدائمة فقط، ويُتجاهَل أي chair_id/member_ids/recorder_id يرسله العميل إلى schedule-committee.
  - false: يعود السلوك السابق (السماح بتشكيل مخصّص عند تمريره، أو الاستكمال تلقائيًا من اللجنة الدائمة عند نقص التشكيل).

المسار العملي خطوة بخطوة (من التسجيل حتى الإغلاق):
1) إنشاء الواقعة
   - POST /incidents/ → تُحدَّد الشدة حسب الكتالوج وتُهيّأ حقول التتبع.
2) إرسال ثم استلام/مراجعة
   - POST /{id}/submit/ ثم POST /{id}/review/.
3) التصعيد (إن لزم) لتفعيل committee_required حسب الشدة/السياسة
   - POST /{id}/escalate/.
4) إحالة إلى اللجنة الدائمة (حصريًا)
   - POST /{id}/schedule-committee/
   - مع DISCIPLINE_ONLY_STANDING_COMMITTEE=true: يتجاهل الخادم أي body، ويحمّل تلقائيًا الرئيس/الأعضاء/المقرر من «اللجنة الدائمة». يعيد 400 إن لم تكن اللجنة الدائمة مهيّأة (رئيس + عضوان على الأقل).
   - يُسجَّل committee_scheduled_by/at وسجل تدقيق.
   - أتمتة مساندة: إذا كانت الواقعة تتطلّب لجنة وبمجرد تنفيذ submit، فسيقوم الخادم بمحاولة جدولة اللجنة تلقائيًا لنفس «اللجنة الدائمة». إذا لم تكن اللجنة الدائمة مهيّأة، لا يُمنَع الإرسال وسيُترك التشكيل لاحقًا يدويًا.
5) التصويت من الأعضاء (اختياري كتتبّع مهني)
   - POST /{id}/committee-vote/ { decision: approve|reject|return }
   - GET /{id}/committee-votes/ لتجميع الأصوات والنصاب والأغلبية (كمرشد).
6) اعتماد القرار النهائي للجنة
   - POST /{id}/committee-decision/ { decision, note?, actions?[], sanctions?[], close_now? }
   - عند approve+close_now=true تُغلق الواقعة فورًا.
7) الإغلاق وسجل التدقيق
   - عند الإغلاق تُحدّث status/closed_by/closed_at وتظهر في لوحات المؤشرات.

أفضل الممارسات:
- ضمان تهيئة «اللجنة الدائمة» دائمًا (رئيس، عضوان على الأقل، ومقرر إن أمكن) قبل بدء العام الدراسي.
- استخدام صفحة «لوحة رئيس لجنة السلوك» لمراقبة: وقائع تحتاج تشكيل (سيتم تشكيلها مباشرةً إلى الدائمة)، وقائع مجدولة قيد القرار، وآخر القرارات.
- الالتزام بحوكمة التصويت والأغلبية، مع استخدام تصويت الرئيس ككاسر تعادل إذا لزم.

معايير القبول:
- أي استدعاء لـ schedule-committee ينتهي بتشكيل اللجنة الدائمة حصريًا أو بخطأ واضح إن لم تكن مهيّأة.
- تظهر مُعطيات اللجنة الدائمة في لجنة الواقعة، وتسمح نقاط التصويت/القرار بإتمام الإجراء حتى الإغلاق.

إشارات واجهة الاستخدام (Home Tiles):
- تظهر بطاقة «لوحة رئيس لجنة السلوك» فقط للرئيس الدائم أو للأدوار القيادية (مدير، وكيل، انضباط L2، مشرف جناح) أو للسوبر يوزر.
- تظهر بطاقة «عضو لجنة السلوك» فقط للعضو الدائم وليس للرئيس/المقرر.
- تظهر بطاقة «مقرر لجنة السلوك» فقط للمقرر الدائم.
- يتم تحديد ذلك عبر endpoint: GET /incidents/committee-caps/ الذي يُرجع access_caps.{is_standing_chair,is_standing_member,is_standing_recorder}.

---

## إطار الأتمتة الاحترافي (Policy Engine)

يعتمد النظام على الحقل Violation.policy لتعريف سياسة كل مخالفة بصورة قابلة للتهيئة دون هجرات إضافية. الصيغة المقترحة:

```
{
  "window_days": 365,                   // نافذة احتساب التكرار (بالأيام)
  "committee": {                        // قواعد إحالة اللجنة
    "requires_on_severity_gte": 3,     // تتطلب لجنة إذا الشدة ≥ 3
    "after_repeats": 2                 // أو بعد تكرارين ضمن النافذة
  },
  "actions_by_repeat": {                // إجراءات تتدرج حسب التكرار (0 = أول مرة)
    "0": ["تنبيه شفهي من المعلم"],
    "1": ["إنذار خطي"],
    "2": ["اتصال بولي الأمر"],
    "3": ["تعهد خطي"]
  },
  "sanctions_by_repeat": {             // عقوبات اختيارية حسب التكرار
    "2": ["حرمان من نشاط"],
    "3": ["إحالة للجنة"]
  },
  "guardian_notify": {                  // سياسة إشعار ولي الأمر
    "on_repeat_gte": 2,                 // إشعار ابتداءً من التكرار 2
    "channels": ["اتصال", "رسالة نصية"]
  }
}
```

وضع التشغيل (Toggle) المقترح من إعدادات الخادم:
- DISCIPLINE_AUTO_ACTIONS = off | suggest | apply
  - off: لا أتمتة (الوضع الافتراضي الحالي).
  - suggest: يقترح الإجراءات/العقوبات المحسوبة في استجابة القراءة فقط (لا يكتب).
  - apply: يدمج الإجراءات/العقوبات تلقائيًا عند نقاط محدّدة (create/submit/escalate) مع تسجيل تدقيق.

أتمتة جدولة اللجنة عند الإرسال:
- لا يتطلب فلاغًا خاصًا؛ تعمل تلقائيًا عندما يكون incident.committee_required=true ولم تكن الواقعة مجدولة سابقًا.
- تعتمد التشكيل من «اللجنة الدائمة» (StandingCommittee + StandingCommitteeMember).
- في حال غياب إعداد اللجنة الدائمة، يتم تجاوز الخطأ بهدوء ويُكمل submit بنجاح.

قائمة فحص للمشرف/المدير (Admin Checklist):
- تأكد من تهيئة «اللجنة الدائمة» في لوحة الإدارة:
  - تعيين رئيس (chair).
  - إضافة عضوين على الأقل (StandingCommitteeMember).
  - تعيين مقرر (recorder) إن وُجد.
- امنح الأدوار والصلاحيات المناسبة:
  - المشاركون في اللجنة يحصلون تلقائيًا على incident_committee_view عند جدولة واقعة، ويحصل الرئيس/المقرر أيضًا على incident_committee_decide.
  - يمكن منح discipline.access لمن يحتاج الاطلاع على الكتالوج.

نقاط التفعيل المقترحة دون كسر التوافق:
- عند إنشاء الواقعة (POST /incidents/):
  - إذا severity=1 وكان repeat=0 وpolicy.actions_by_repeat["0"] موجودًا، يتم:
    - suggest: تعرض الحقول المقروءة suggested_actions.
    - apply: يُضاف "تنبيه شفهي من المعلم" تلقائيًا إلى actions_applied مع Audit=auto_action.
- عند الإرسال submit: يُعاد حساب repeat ضمن window_days ويُدمج ما يلزم.
- عند التصعيد escalate: يُتحقق من حدود اللجنة ويُفعَّل committee_required إذا انطبقت السياسة.

حساب التكرار (repeat index):
- يتم عدّ الوقائع السابقة لنفس الطالب ونفس رمز المخالفة Violation.code خلال window_days بحد أقصى حتى تاريخ الواقعة الحالية (event_date).

حقول قراءة جديدة (لا تتطلب هجرات — تُضاف في التمثيل فقط):
- suggested_actions: قائمة إجراءات مقترحة حسب السياسة والحالة.
- suggested_sanctions: قائمة عقوبات مقترحة.
- repeat_index: رقم التكرار المحسوب.

ملاحظة: يمكن دعم هذه الحقول في Serializers كإغناء فقط. وعند الانتقال إلى apply، يتم الكتابة إلى actions_applied/sanctions_applied مع IncidentAuditLog مناسب.

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
6.1) جدولة اللجنة (اللجنة الدائمة فقط)
- الصلاحية: incident_committee_schedule أو is_staff/superuser.
- API: POST /{id}/schedule-committee/
  - مع تفعيل DISCIPLINE_ONLY_STANDING_COMMITTEE=true (افتراضي): يتم تجاهل أي body يحدد chair_id/member_ids/recorder_id، ويُحمَّل التشكيل حصريًا من «اللجنة الدائمة». إن لم تكن الدائمة مهيّأة يعاد 400 برسالة عربية واضحة.
  - عند إيقاف السياسة (false): يعود السلوك السابق (يمكن تمرير تشكيل مخصّص، ويُستكمل الناقص من اللجنة الدائمة).
- الأثر: حفظ committee_panel + إنشاء IncidentCommittee/IncidentCommitteeMember + ضبط committee_scheduled_by/at + Audit (meta.action=schedule_committee).

ملاحظة تشغيلية مهمة: مع السياسة الافتراضية «اللجنة الدائمة فقط»، «تحويل الواقعة إلى اللجنة» يعني إحالتها إلى «اللجنة الدائمة» حصريًا. أي تشكيل بديل يتم تجاهله لضمان سرعة الانعقاد واتساق الحوكمة والمعايير.

س: من الذي «يُجدول» الواقعة للجنة السلوك؟
ج: المستخدم الذي يستدعي نقطة API الخاصة بالجدولة (schedule-committee) وهو يمتلك صلاحية incident_committee_schedule. يُسجَّل هذا المستخدم تلقائيًا في الحقل committee_scheduled_by مع التاريخ committee_scheduled_at، ويظهر اسمه الكامل في واجهات العرض عندما يتوفر اسم الموظف في جدول Staff.

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

أتمتة مقترحة ضمن نفس الانتقالات:
- Create: اقتراح/تطبيق «تنبيه شفهي من المعلم» تلقائيًا للمخالفة ذات الشدة 1 عند repeat=0.
- Submit: عند repeat ≥ policy.guardian_notify.on_repeat_gte يتم تسجيل إشعار وليّ الأمر كإجراء أو تذكير في suggested_actions.
- Escalate: يُفعّل committee_required إذا بلغ repeat حد after_repeats أو severity ≥ requires_on_severity_gte.

---

## كيف يتم اتخاذ القرار في الواقعة برمجياً (اللجنة)

هذا القسم يشرح بدقة مسار اتخاذ القرار عبر واجهة API، مع الصلاحيات والتحققات وأثر القرار على بيانات الواقعة.

1) نقطة النهاية والصلاحيات
- URL: POST /api/v1/discipline/incidents/{incident_id}/committee-decision/
- يتطلب أحد التالي:
  - صلاحية discipline.incident_committee_decide
  - أو is_staff / is_superuser

2) جسم الطلب (JSON)
- decision: أحد القيم approve | reject | return (مطلوب)
- note: ملاحظات نصية اختيارية (اختياري)
- actions: قائمة إجراءات ستُدمج داخل incident.actions_applied (اختياري)
- sanctions: قائمة عقوبات ستُدمج داخل incident.sanctions_applied (اختياري)
- close_now: منطقية؛ عند true مع قرار approve سيجري إغلاق الواقعة فورًا (اختياري)

3) منطق المعالجة (باختصار من الخادم)
- يتحقق من الصلاحية.
- يقرأ decision ويطبّعها إلى lowercase.
- يدمج actions/sanctions مع الحقول الموجودة في الواقعة (لا يستبدل بالكامل، بل يضيف).
- يسجّل أثر تدقيق IncidentAuditLog مع meta:
  - meta.action = "committee_decision"
  - meta.decision = decision
  - meta.note = note (إن وُجد)
- عند close_now=true وdecision=approve:
  - status ← closed
  - closed_by ← المستخدم الحالي
  - closed_at ← الوقت الحالي
  - تسجيل Audit إضافي للإغلاق.

4) أمثلة عملية (curl)

الموافقة مع إغلاق فوري:
```
curl -k -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  https://127.0.0.1:8443/api/v1/discipline/incidents/<INCIDENT_ID>/committee-decision/ \
  -d '{
    "decision": "approve",
    "note": "إقرار توصية المعلم مع تنبيه ولي الأمر",
    "actions": ["اتصال بولي الأمر"],
    "sanctions": ["تنبيه خطي"],
    "close_now": true
  }'
```

رفض مع ملاحظات دون إغلاق:
```
curl -k -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  https://127.0.0.1:8443/api/v1/discipline/incidents/<INCIDENT_ID>/committee-decision/ \
  -d '{
    "decision": "reject",
    "note": "لا توجد أدلة كافية"
  }'
```

إعادة (إرجاع) للمعالجة:
```
curl -k -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  https://127.0.0.1:8443/api/v1/discipline/incidents/<INCIDENT_ID>/committee-decision/ \
  -d '{
    "decision": "return",
    "note": "مطلوب معلومات إضافية من المرشد الطلابي"
  }'
```

5) شكل الاستجابة
- 200 OK عند نجاح التسجيل (مع تمثيل للواقعة محدثة)
- 403 Forbidden عند نقص الصلاحية
- 400 Bad Request إذا كانت قيمة decision غير صالحة

6) نقاط تكامل واجهة المستخدم
- بعد القرار، تعرض لوحة «رئيس اللجنة» أثر القرار ضمن «أحدث قرارات اللجنة».
- في حالة close_now، تنتقل الواقعة إلى عمود «مغلقة» ويُحدّث الملخص /summary تلقائيًا عند الطلب التالي.

7) ظهور «إجراء المقرِّرة» في لوحات اللجنة

- تعرض لوحة «رئيس اللجنة» الآن ضمن قائمة «مجدولة وتنتظر القرار» سطرًا ملخّصًا بعنوان proposed_summary يوضّح ما اقترحته المراجِعة/المقرِّرة من إجراءات أو عقوبات (إن وُجدت) استنادًا إلى حقلي incident.actions_applied وincident.sanctions_applied.
- عند فتح بطاقة الواقعة، يظهر نفس الملخص تحت قسم معلومات الجدولة عندما تكون الواقعة مُجدولة للجنة. هذا يساعد الرئيس والأعضاء على الاطلاع السريع على توصية المقرِّرة قبل اتخاذ قرار (موافقة/رفض/إعادة).

ملاحظات تنفيذية:
- الحقل proposed_summary قراءة فقط ومُشتق من بيانات الواقعة الموجودة، ولا يغيّر مخطط قاعدة البيانات.
- لا يتطلب أي صلاحيات إضافية، ويظهر لكل من لديه حق الوصول لمسار اللجنة (incident_committee_view) أو صلاحيات الموظفين ذات الصلة.

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

تنبيه شفهي (Use‑Case تطبيقي):
- مثال سياسة مخالفة تأخير بسيط (Severity=1):
  - التسجيل الأول: إجراء تلقائي/مقترح «تنبيه شفهي من المعلم».
  - التكرار الأول: "إنذار خطي".
  - التكرار الثاني: "اتصال ولي الأمر" وتفعيل إشعار guardian_notify.
  - التكرارات الأعلى: حسب السياسة قد يُوصى بـ "حرمان نشاط" أو إحالة للجنة بحسب المدرسة.

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
1) أتمتة الإجراءات بحسب السياسة (هذا الطلب):
   - طور 1 (suggest): حساب repeat والسلوك المقترح وإظهاره في الحقول المقروءة suggested_* دون كتابة. ✓ المواصفات جاهزة أعلاه.
   - طور 2 (apply): دمج المقترحات تلقائيًا عند create/submit/escalate مع Audit=auto_action. إضافة فلاغ DISCIPLINE_AUTO_ACTIONS.
   - طور 3: تقارير متابعة «الإجراءات المؤتمتة» ومؤشرات الالتزام.
2) «مسار لجنة» رسمي: عند `committee_required`، تعريف خطوات/اعتمادات إضافية وربطها بـ `escalate` وقرارات اللجنة.
   - تفعيل الحقول المقترحة أعلاه وإنشاء هجرتِها ونقطتَي API (`schedule-committee`, `committee-decision`).
   - إضافة شارات قراءة فقط في واجهة الجناح لحالة اللجنة وقرارها.
3) مرفقات وشواهد: دعم رفع ملفات/صور وربطها بالواقعة، وسياسة صلاحيات/إخفاء.
4) ضبط SLA آليًا: إنفاذ مهلة الاستلام/الإشعار برسائل تنبيهية وتنبيهات للمتأخرات (مع tasks/cron).
5) قوالب إشعارات: قنوات SMS/اتصال/داخلي مع قوالب عربية موحّدة وتتبّع حالة التسليم.
6) سجل تدقيق (Audit log): تتبّع كل تغيير حالة/حقل مع من/متى ولماذا.
7) تصدير CSV/Excel: زر في الواجهة يستدعي `admin-export` أو `visible` وفق الصلاحيات، مع نفس الفلاتر.
8) مؤشرات KPIs في الصفحة: شريط أعلى يعرض إجماليات من `/summary/` متطابقة مع الجدول.
9) كانبان/لوحة متابعة: عرض بصري حسب الحالة/الشدة مع سحب وإفلات (إن لزم للمعالجة السريعة).
10) اختبارات تكامل: سيناريوهات تغطي الرؤية، التاريخ، التطبيع، والتحولات لضمان عدم تراجع السلوك مستقبلًا.

---

## مصفوفة «المخالفات الأربعين» — قالب احترافي قابل للتعبئة

الغرض: توحيد سياسة الإجراءات والعقوبات للمخالفات الأربعين الأكثر شيوعًا في المدرسة، مع عدالة تصاعدية ووضوح إشعار وليّ الأمر وإحالة اللجنة.

أعمدة القالب المقترح لكل مخالفة:
- code | category | severity | requires_committee
- window_days | actions_by_repeat (0..3) | sanctions_by_repeat (2..3)
- guardian_notify.on_repeat_gte | channels | committee.after_repeats | committee.requires_on_severity_gte

أمثلة مُعبّأة (نماذج، للتوضيح — القيَم قابلة للتعديل حسب سياسة المدرسة):

1) V-101 | «تأخير بسيط» | severity=1 | requires_committee=false
- window_days=90
- actions_by_repeat: 0=تنبيه شفهي، 1=إنذار خطي، 2=اتصال ولي الأمر
- sanctions_by_repeat: 2=حرمان من نشاط واحد
- guardian_notify.on_repeat_gte=2 (قنوات: اتصال)

2) V-205 | «سلوك غير لائق في الصف» | severity=2 | requires_committee=false
- window_days=180
- actions_by_repeat: 0=تنبيه شفهي، 1=تعهد خطي، 2=اتصال ولي الأمر
- sanctions_by_repeat: 3=حرمان يوم نشاط
- committee.after_repeats=3

3) V-309 | «اعتداء لفظي» | severity=3 | requires_committee=true
- window_days=365
- actions_by_repeat: 0=إنذار خطي + جلسة إرشاد
- sanctions_by_repeat: 0=لا شيء، 1=حرمان نشاط، 2=إحالة للجنة
- committee.requires_on_severity_gte=3 (مفعّلة)

4) V-412 | «تخريب ممتلكات» | severity=4 | requires_committee=true
- window_days=365
- actions_by_repeat: 0=توثيق + إشعار ولي الأمر الفوري
- sanctions_by_repeat: 0=تعويض/إصلاح، 1=حرمان نشاط، 2=إحالة للجنة

طريقة الاعتماد:
- يُراجع «قائد الانضباط» القالب ويضبط لكل رمز Violation.code وفق سياسة المدرسة. تُحفظ السياسة داخل Violation.policy لكل سجل في الكتالوج.
- مع تشغيل suggest/apply تتصرّف المنظومة تلقائيًا وفق ما سبق.

معايير قبول للمصفوفة:
- تغطية 40 مخالفة مع ملء الحقول المذكورة.
- اختبار 10 حالات على الأقل عبر بيانات تجريبية للتحقق من repeat والحسابات.

---

## إجراءات تشغيلية وتكامل API للأتمتة

- حساب repeat_index: يمكن تنفيذه داخل الباكند عند create/submit عبر استعلام على Incident لنفس الطالب ونفس violation.code ضمن window_days.
- التسجيل التلقائي (apply):
  - Audit: meta.action = "auto_action", meta.source = "policy_engine", meta.repeat = n
  - Merge: يُضاف الإجراء/العقوبة دون حذف السابق.
- الإشعار بولي الأمر:
  - إمّا يُسجّل كإجراء داخل actions_applied: "إشعار ولي الأمر (قناة: اتصال)"، أو يُستدعى endpoint notify-guardian عند التنفيذ الفعلي.
- تمثيل القراءة:
  - إضافة suggested_actions/suggested_sanctions/repeat_index في IncidentSerializer/IncidentFullSerializer كحقول مقروءة فقط (لا تتطلب هجرة).

أمثلة تدفق عملي (suggest):
1) إنشاء واقعة تأخير (Severity=1، أول مرة): يستجيب /incidents/ بتمثيل يحتوي suggested_actions=["تنبيه شفهي"].
2) إرسال الواقعة بعد أسبوع وتكرار ثانٍ: عند submit تُظهر القراءة suggested_actions=["اتصال ولي الأمر"], suggested_sanctions=["حرمان نشاط"].
3) بلوغ repeat≥3: تُفعَّل committee_required تلقائيًا عند escalate.

خطة طرح تدريجية (Rollout):
- مرحلة 1: تفعيل suggest على بيئة الاختبار، مراجعة القيم مع المرشدين.
- مرحلة 2: تفعيل apply لجزء من المخالفات منخفضة الشدة (Level 1–2).
- مرحلة 3: تعميم apply وإضافة مراقبة عبر `/overview` و`/summary` ومؤشرات مخصّصة.

### التصويت والاقتراع في لجنة السلوك (مفعل)
يوفّر النظام آلية تصويت احترافية خفيفة دون الحاجة لهجرات جديدة عبر سجل التدقيق Audit:

- تسجيل تصويت عضو اللجنة:
  - POST `/api/v1/discipline/incidents/{id}/committee-vote/`
  - body: `{ "decision": "approve|reject|return", "note"?: "..." }`
  - الوصول: أي مستخدم ضمن لجنة الواقعة (رئيس/عضو/مقرر) أو موظف is_staff/superuser.
  - الأثر: يسجل IncidentAuditLog بعنصر meta: `{ action: "committee_vote", decision, voter_id }`.

- تلخيص الأصوات والحسابات:
  - GET `/api/v1/discipline/incidents/{id}/committee-votes/`
  - الاستجابة (مثال):
    ```json
    {
      "votes": [ {"voter_id": 12, "decision": "approve"} ],
      "summary": {
        "total_voters": 3,
        "participated": 2,
        "quorum": 2,
        "quorum_met": true,
        "counts": { "approve": 1, "reject": 1, "return": 0 },
        "majority": "approve",
        "chair_vote": null
      }
    }
    ```

- الوقائع الخاصة بالمستخدم (عضو/مقرر/رئيس):
  - GET `/api/v1/discipline/incidents/my-committee/`
  - تعيد قائمة وقائع يكون المستخدم جزءًا من لجنتها.

- قواعد الحساب:
  - النصاب = نصف + 1 من إجمالي الناخبين (الأعضاء + الرئيس).
  - الأغلبية البسيطة تحدد الاقتراح.
  - عند التعادل يُستخدم تصويت الرئيس ككاسر تعادل إن وُجد.

- تكامل الواجهة (جاهز):
  - صفحة رئيس اللجنة: `CommitteeDashboard.vue` مع تباعد أفضل وروابط لصفحات الأعضاء/المقرر.
  - صفحة عضو اللجنة: `CommitteeMember.vue` تعرض الوقائع وتسمح بالتصويت السريع وتُظهر ملخص الأصوات.
  - صفحة مقرر اللجنة: `CommitteeRecorder.vue` تعرض الملخصات للمساعدة في تدوين المحضر.

ملاحظة: قرار اللجنة النهائي يُسجّل عبر نقطة `committee-decision` كما في القسم السابق. يمكن اعتماد أغلبية التصويت كمرشد قبل الاعتماد النهائي من الرئيس.

---

### كيف تُجرى «العقوبة» بعد منح الصلاحيات؟ — دليل عملي سريع

بعد منح الصلاحيات المطلوبة لأعضاء لجنة السلوك وللقيادات، لديك مساران رئيسيان لتطبيق «العقوبة» على الواقعة:

1) المسار المباشر (بدون لجنة)
- متى يُستخدم؟ في الحالات الاعتيادية التي لا تتطلب لجنة أو قبل انعقاد اللجنة، لتسجيل إجراءات وعقوبات تشغيلية متدرجة.
- الصلاحية المطلوبة: يمتلكها عادة مشرفو الانضباط أو من لديهم صلاحية تعديل الوقائع ضمن نطاقهم.
- من الواجهة: افتح «بطاقة الواقعة» → قسم «الإجراءات والعقوبات» → اكتب اسم العقوبة في الحقل «إضافة عقوبة» ثم اضغط «إضافة عقوبة».
- من API:
  - POST `/api/v1/discipline/incidents/{id}/add-sanction/`
  - Body مثال:
    ```json
    { "name": "حرمان من نشاط مدرسي", "notes": "لمدة أسبوع" }
    ```
  - الأثر: تُضاف العنصر إلى `sanctions_applied` مع ختم تاريخ/وقت، ويُسجَّل في سجل التدقيق.

2) مسار اللجنة (عند الحاجة إلى قرار لجنة)
- متى يُستخدم؟ عندما تكون الواقعة مفعّل لها `committee_required` (بسبب الشدة/التكرار/السياسة) أو قررتم عرضها على اللجنة.
- الخطوات المختصرة:
  1. جدولة اللجنة للواقعة: رئيس اللجنة (أو من لديه صلاحية) يستخدم:
     - POST `/api/v1/discipline/incidents/{id}/schedule-committee/`
     - Body: `{ "chair_id": 12, "member_ids": [34,56], "recorder_id": 78 }` أو استخدم اللجنة الدائمة: `?use_standing=1` مع Body فارغ.
  2. اعتماد قرار اللجنة وتطبيق العقوبات معًا:
     - POST `/api/v1/discipline/incidents/{id}/committee-decision/`
     - الصلاحية: `discipline.incident_committee_decide` أو is_staff/superuser.
     - Body مثال (اعتماد + إغلاق فوري):
       ```json
       {
         "decision": "approve",
         "note": "اعتماد العقوبة حسب السياسة",
         "actions": ["إشعار ولي الأمر"],
         "sanctions": ["حرمان من نشاط أسبوعي"],
         "close_now": true
       }
       ```
     - الأثر: يندمج ما في `actions` و`sanctions` داخل الواقعة، ويُسجّل IncidentAuditLog مع `meta.action=committee_decision`. إذا `close_now=true` وقرار `approve` تُغلق الواقعة مباشرة.

ملاحظات تشغيلية مهمة:
- تظهر عناصر «الإجراءات والعقوبات» في واجهة «بطاقة الواقعة» وتزداد العدادان «إجراءات/عقوبات» تلقائيًا بعد أي استدعاء ناجح.
- يمكن استخدام «التصعيد» Escalate قبل اللجنة لتمييز الواقعة كمرشحة للجنة وفق السياسة و/أو التكرار.
- توصي الوثيقة بتعبئة سياسة الكتالوج Violation.policy لتوحيد التسميات وآلية التصعيد، ثم استخدام وضع التشغيل `suggest/apply` لاحقًا لأتمتة الاقتراح/التطبيق.

طرق تحقق سريعة (QA):
- أنشئ واقعة تجريبية ثم أضف عقوبة مباشرة عبر الواجهة وتأكد من ظهورها في القائمة.
- نفّذ قرار لجنة بالمثال أعلاه وتحقق من دمج العقوبات وتحديث الحالة عند `close_now=true`.
- راجع «لوحة رئيس اللجنة» لترى القرار ضمن «أحدث قرارات اللجنة» والتحقق من العدادات.

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
    - يمنح النظام تلقائيًا صلاحيات مسار اللجنة (RBAC خفيف) للمشاركين:
      - لجميع المشاركين (الرئيس/الأعضاء/المقرر): `discipline.incident_committee_view`.
      - للرئيس والمقرّر: `discipline.incident_committee_decide`.
      - تُنفّذ المنح بشكل آمن وعديم الأثر عند تكرار الجدولة (idempotent)، وقد تُتخطّى بهدوء إذا لم تكن الأذونات متاحة في البيئة.
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
