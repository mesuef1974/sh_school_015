<template>
  <section class="container py-3" dir="rtl">
    <div class="page-stack" :class="printClass">
      <WingPageHeader
        icon="solar:printer-minimalistic-bold-duotone"
        :title="`مركز طباعة النماذج — واقعة #${id}`"
        :subtitle="it ? (it.student_name ? `الطالب: ${it.student_name}` : '') : 'تحميل البيانات'"
        :color="sevColor"
      >
        <template #actions>
          <div class="d-flex flex-wrap gap-2">
            <RouterLink class="btn btn-outline-secondary" :to="{ name: 'discipline-incident-card', params: { id } }">عودة لبطاقة الواقعة</RouterLink>
            <button class="btn btn-primary" :disabled="loading" @click="printAll">طباعة كل البطاقات</button>
          </div>
        </template>
      </WingPageHeader>

      <div v-if="loading" class="alert alert-info">جاري التحميل…</div>
      <div v-else-if="msg" class="alert alert-warning">{{ msg }}</div>

      <div v-else class="d-grid gap-3 print-area">
        <!-- بطاقة معلومات عامة عن الواقعة -->
        <div class="card p-3" data-section="summary">
          <div class="row g-3">
            <div class="col-md-4 col-6">
              <div class="text-muted small">الطالب</div>
              <div class="fw-semibold">{{ it?.student_name || ('#'+it?.student) }}</div>
            </div>
            <div class="col-md-4 col-6">
              <div class="text-muted small">المخالفة</div>
              <div class="fw-semibold">{{ it?.violation_display || it?.violation?.code }}</div>
            </div>
            <div class="col-md-4 col-6">
              <div class="text-muted small">التاريخ</div>
              <div>{{ fmtDate(it?.occurred_at) }}</div>
            </div>
            <div class="col-md-4 col-6">
              <div class="text-muted small">المكان</div>
              <div>{{ it?.location || '—' }}</div>
            </div>
            <div class="col-md-4 col-6">
              <div class="text-muted small">الشدة</div>
              <span class="badge" :style="{ backgroundColor: sevColor, color: '#fff' }">{{ it?.severity ?? '—' }}</span>
            </div>
            <div class="col-md-4 col-6">
              <div class="text-muted small">عدد مرات التكرار (ضمن نافذة السياسة)</div>
              <div>
                {{ (it as any)?.repeat_count_for_subject ?? (it as any)?.repeat_count_in_window ?? '—' }}
                <span v-if="(it as any)?.repeat_window_term_label" class="text-muted"> — الصف: {{ (it as any).repeat_window_term_label }}</span>
              </div>
            </div>
            <div class="col-12">
              <div class="text-muted small">الوصف</div>
              <div class="prewrap">{{ it?.narrative || '—' }}</div>
            </div>
          </div>
        </div>

        <!-- بطاقة: تنبيه شفهي -->
        <div v-if="showOral" class="card p-3" data-section="oral">
          <div class="d-flex align-items-center gap-2 mb-2">
            <h6 class="m-0">تنبيه شفهي</h6>
            <button class="btn btn-sm btn-outline-dark ms-auto" @click="printSection('oral')">طباعة</button>
          </div>
          <div class="oral-text" v-html="oralHtml"></div>
        </div>

        <!-- بطاقة: تعهد الطالب -->
        <div class="card p-3" data-section="student_pledge">
          <div class="d-flex align-items-center gap-2 mb-2">
            <h6 class="m-0">تعهد الطالب</h6>
            <button class="btn btn-sm btn-outline-dark ms-auto" @click="printSection('student_pledge')">طباعة</button>
          </div>
          <!-- نص التعهد من الملف المرفق مع استبدال الرموز -->
          <div class="pledge-text" v-html="studentPledgeHtml"></div>
        </div>

        <!-- بطاقة: تعهد ولي الأمر -->
        <div class="card p-3" data-section="guardian_pledge">
          <div class="d-flex align-items-center gap-2 mb-2">
            <h6 class="m-0">تعهد ولي الأمر</h6>
            <button class="btn btn-sm btn-outline-dark ms-auto" @click="printSection('guardian_pledge')">طباعة</button>
          </div>
          <!-- نص التعهد من الملف المرفق مع استبدال الرموز -->
          <div class="pledge-text" v-html="guardianPledgeHtml"></div>
        </div>

        <!-- بطاقة: إجراءات الواقعة (قرارات/إجراءات اللجنة) -->
        <div class="card p-3" data-section="actions">
          <div class="d-flex align-items-center gap-2 mb-2">
            <h6 class="m-0">إجراءات الواقعة</h6>
            <button class="btn btn-sm btn-outline-primary ms-auto" @click="printSection('actions')">طباعة</button>
          </div>
          <div v-if="it?.period_time_label" class="small text-muted">وقت الحصة: {{ (it as any).period_time_label }}</div>
          <div v-if="(it as any)?.subject_name" class="small text-muted">المادة: {{ (it as any).subject_name }}</div>
          <div v-if="(it as any)?.repeat_count_for_subject !== undefined" class="small text-muted mb-2">
            تكرار لنفس المادة ضمن الصف: {{ (it as any).repeat_count_for_subject }}
            <span v-if="(it as any)?.repeat_window_term_label"> — الصف: {{ (it as any).repeat_window_term_label }}</span>
          </div>
          <div v-if="Array.isArray(it?.actions_applied) && it!.actions_applied.length>0">
            <ul class="small mb-0 list-unstyled">
              <li v-for="(a,idx) in it!.actions_applied" :key="idx" class="mb-2 pb-2 border-bottom">
                <div class="fw-semibold">
                  {{ a.name || a.code || 'إجراء' }}
                  <span v-if="a.code" class="badge bg-light text-dark ms-1">{{ a.code }}</span>
                </div>
                <div v-if="a.description" class="text-body">{{ a.description }}</div>
                <div v-if="a.notes" class="text-body">ملاحظات: {{ a.notes }}</div>
                <div class="text-muted">
                  <span v-if="a.by_display || a.by_name || a.by || a.actor || a.applied_by">
                    المُنفِّذ: {{ a.by_display || a.by_name || a.by || a.actor || a.applied_by }}
                  </span>
                  <span v-if="(a.by_display || a.by_name || a.by || a.actor || a.applied_by) && (a.at || a.applied_at || a.created_at || a.timestamp)"> • </span>
                  <span v-if="a.at || a.applied_at || a.created_at || a.timestamp">الزمن: {{ fmtDateTime(a.at || a.applied_at || a.created_at || a.timestamp) }}</span>
                  <span v-if="(a.source || a.channel) || a.auto" class="ms-2">
                    <span v-if="a.source || a.channel">المصدر: {{ a.source || a.channel }}</span>
                    <span v-if="a.auto">{{ (a.source? ' • ' : '') }}مضاف تلقائيًا</span>
                  </span>
                </div>
              </li>
            </ul>
          </div>
          <div v-else class="text-muted small">لا توجد إجراءات مسجلة.</div>
        </div>

        <!-- بطاقة: عقوبات الواقعة -->
        <div class="card p-3" data-section="sanctions">
          <div class="d-flex align-items-center gap-2 mb-2">
            <h6 class="m-0">عقوبات الواقعة</h6>
            <button class="btn btn-sm btn-outline-warning ms-auto" @click="printSection('sanctions')">طباعة</button>
          </div>
          <div v-if="it?.period_time_label" class="small text-muted">وقت الحصة: {{ (it as any).period_time_label }}</div>
          <div v-if="(it as any)?.subject_name" class="small text-muted">المادة: {{ (it as any).subject_name }}</div>
          <div v-if="(it as any)?.repeat_count_for_subject !== undefined" class="small text-muted mb-2">
            تكرار لنفس المادة ضمن الصف: {{ (it as any).repeat_count_for_subject }}
            <span v-if="(it as any)?.repeat_window_term_label"> — الصف: {{ (it as any).repeat_window_term_label }}</span>
          </div>
          <div v-if="Array.isArray(it?.sanctions_applied) && it!.sanctions_applied.length>0">
            <ul class="small mb-0 list-unstyled">
              <li v-for="(s,idx) in it!.sanctions_applied" :key="idx" class="mb-2 pb-2 border-bottom">
                <div class="fw-semibold">
                  {{ s.name || s.code || 'عقوبة' }}
                  <span v-if="s.code" class="badge bg-light text-dark ms-1">{{ s.code }}</span>
                </div>
                <div v-if="s.description" class="text-body">{{ s.description }}</div>
                <div v-if="s.notes" class="text-body">ملاحظات: {{ s.notes }}</div>
                <div class="text-muted">
                  <span v-if="s.by_display || s.by_name || s.by || s.actor || s.applied_by">
                    المُقرِّر/الجهة: {{ s.by_display || s.by_name || s.by || s.actor || s.applied_by }}
                  </span>
                  <span v-if="(s.by_display || s.by_name || s.by || s.actor || s.applied_by) && (s.at || s.applied_at || s.created_at || s.timestamp)"> • </span>
                  <span v-if="s.at || s.applied_at || s.created_at || s.timestamp">الزمن: {{ fmtDateTime(s.at || s.applied_at || s.created_at || s.timestamp) }}</span>
                  <span v-if="(s.source || s.channel) || s.auto" class="ms-2">
                    <span v-if="s.source || s.channel">المصدر: {{ s.source || s.channel }}</span>
                    <span v-if="s.auto">{{ (s.source? ' • ' : '') }}مضاف تلقائيًا</span>
                  </span>
                </div>
              </li>
            </ul>
          </div>
          <div v-else class="text-muted small">لا توجد عقوبات مسجلة.</div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref, computed, nextTick, onBeforeUnmount } from 'vue';
import { useRoute } from 'vue-router';
import WingPageHeader from '../../../components/ui/WingPageHeader.vue';
import { getIncidentFull } from '../api';

const route = useRoute();
const id = String(route.params.id || '');
const it = ref<any>(null);
const loading = ref(false);
const msg = ref('');
// تحكم بطباعة قسم واحد فقط
const printOnly = ref<null | 'oral' | 'student_pledge' | 'guardian_pledge' | 'actions' | 'sanctions'>(null);
const printClass = computed(()=> printOnly.value ? `print-only-${printOnly.value}` : '');

const sevColor = computed(()=>{
  const s = Number(it.value?.severity || 1);
  return s>=4? '#d9534f' : s===3? '#f0ad4e' : s===2? '#5bc0de' : '#5cb85c';
});

function fmtDate(x?: string){
  try{ return x ? new Date(x).toLocaleDateString('ar-QA') : '—'; }catch{ return '—'; }
}
function fmtDateTime(x?: string){
  try{
    if (!x) return '—';
    const d = new Date(x);
    return d.toLocaleString('ar-QA', { year:'numeric', month:'2-digit', day:'2-digit', hour:'2-digit', minute:'2-digit' });
  }catch{ return '—'; }
}

// ======= قوالب «التعهد» مستخرجة من الملف المرفق (مع استبدال الرموز) =======
// ======= قالب «التنبيه الشفهي» الاحترافي =======
function renderOralTemplate(): string {
  // تنسيق احترافي موجّه للطباعة يتماشى مع أسلوب التعهدات
  const t = (
`تنبيه شفهي رسمي — المستوى الأول (إرشادي)

بيانات الطالب:
الاسم: {{student_full_name}}  •  الصف: {{class_name}}  •  الرقم المدرسي: {{student_sid}}
وقت الواقعة: {{incident_time_hm}}  •  وقت الحصة: {{period_time_label_or_dash}}

تفاصيل الواقعة:
تم في تاريخ {{incident_date}} تنبيه الطالب بشأن مخالفة: {{violation_display_or_code}} (رقم الواقعة: {{incident_short_id}}).
وصف مختصر للحالة كما ورد: {{incident_narrative_or_dash}}

التوجيهات الفورية المقدَّمة للطالب:
1) الالتزام الفوري بقواعد السلوك والانضباط داخل الصف وخارجه.
2) اتباع توجيهات المعلم والمرشد الطلابي والتعاون لمعالجة أسباب السلوك.
3) الحفاظ على بيئة صفية آمنة ومحترمة وعدم إزعاج سير الدرس.

إقرار الطالب بالعلم:
يُقِرّ الطالب بأنه قد استمع للتنبيه الشفهي وفهم مضمونه وعواقب تكرار المخالفة،
وأن هذا التنبيه يُعدّ إجراءً تمهيديًا قد يتبعه تصعيد تدريجي وفق لائحة السلوك والمواظبة عند التكرار.

معلومة إضافية أو متابعة (إن وُجدت): {{proposed_summary_or_dash}}

التوقيعات:
- اسم المعلم: {{reporter_name}}  •  التوقيع: ____________  •  التاريخ: ____/____/______
- اسم الطالب: {{student_full_name}}  •  التوقيع: ____________  •  التاريخ: ____/____/______

مرجع المستند: ORAL-{{current_year}}-{{incident_short_id}}
`);
  return t;
}
function renderStudentPledgeTemplate(): string {
  // تعهد الطالب — يوجَّه للطالب مباشرةً
  const t = (
`تعهد خطي للطالب بشأن الالتزام بالسلوك المدرسي

أنا الطالب: {{student_full_name}} (الرقم المدرسي: {{student_sid}}) في الصف: {{class_name}}, أُقرّ بأنني اطّلعت على تفاصيل الواقعة رقم {{incident_short_id}} بتاريخ {{incident_date}} المتعلقة بمخالفة: {{violation_display_or_code}}.
وقت الواقعة: {{incident_time_hm}}  •  وقت الحصة: {{period_time_label_or_dash}}

أتعهد أنا الطالب بما يلي:
1) الالتزام التام بقواعد السلوك والانضباط داخل الصف وخارجه، وعدم تكرار المخالفة المذكورة.
2) احترام تعليمات المعلمين والمرشد الطلابي، والتعاون الجاد لمعالجة أسباب السلوك غير المقبول.
3) المواظبة على حضور البرامج/الجلسات الإرشادية أو العلاجية إن طُلِبت مني، والمتابعة خلال مدة {{followup_window}} أيام.
4) العلم بأن تكرار المخالفة قد يترتب عليه إجراءات تصعيدية حسب لائحة السلوك والمواظبة.

ملخص الإجراء/التوصية (إن وُجد): {{proposed_summary_or_dash}}

بيانات التوقيع:
- توقيع الطالب: ____________   الاسم: __________________   التاريخ: ____/____/______
- اسم المستلم (معلم/مرشد): {{reporter_name}}   التوقيع: ____________   التاريخ: ____/____/______

رقم الوثيقة: {{doc_id}}  • نسخة القالب: {{template_version}}  • مرجع الواقعة: {{incident_short_id}}`
  );
  return t;
}

function renderGuardianPledgeTemplate(): string {
  // تعهد ولي الأمر — يوجَّه لولي الأمر مباشرةً
  const t = (
`تعهد خطي لولي الأمر بشأن متابعة سلوك الطالب

أنا ولي أمر الطالب: {{student_full_name}} (الرقم المدرسي: {{student_sid}}) في الصف: {{class_name}}, اطّلعت على الواقعة رقم {{incident_short_id}} بتاريخ {{incident_date}} المتعلقة بمخالفة: {{violation_display_or_code}}.
وقت الواقعة: {{incident_time_hm}}  •  وقت الحصة: {{period_time_label_or_dash}}

أتعهد أنا ولي الأمر بما يلي:
1) متابعة ابني سلوكيًا وأكاديميًا، والتعاون مع المدرسة في تنفيذ ما يلزم من إجراءات علاجية أو إرشادية.
2) حضور الاجتماعات/الاستدعاءات عند الطلب، والتواصل الفعّال مع المدرسة لإحاطة المرشد/الإدارة بأي ظروف مؤثرة.
3) دعم التزام الطالب بقواعد السلوك، والتنبيه إلى عواقب التكرار وفق لائحة السلوك والمواظبة.
4) متابعة الخطة خلال مدة {{followup_window}} أيام والمساهمة في معالجة أسباب المخالفة.

ملخص الإجراء/التوصية (إن وُجد): {{proposed_summary_or_dash}}

بيانات التوقيع:
- توقيع ولي الأمر:   ____________   الاسم: __________________   التاريخ: ____/____/______
- اسم المستلم (معلم/مرشد): {{reporter_name}}   التوقيع: ____________   التاريخ: ____/____/______

رقم الوثيقة: {{doc_id}}  • نسخة القالب: {{template_version}}  • مرجع الواقعة: {{incident_short_id}}`
  );
  return t;
}

function toHtml(text: string): string {
  // تحويل أسطر مرقّمة وبنود إلى HTML بسيط للطباعة
  const esc = (s:string)=> s
    .replace(/&/g,'&amp;')
    .replace(/</g,'&lt;')
    .replace(/>/g,'&gt;');
  const lines = text.split(/\r?\n/);
  const out: string[] = [];
  let inOl = false;
  for (const ln of lines) {
    const m = ln.match(/^\s*(\d+)\)\s+(.*)$/);
    if (m) {
      if (!inOl) { inOl = true; out.push('<ol class="mb-2">'); }
      out.push(`<li>${esc(m[2])}</li>`);
      continue;
    } else if (inOl) {
      inOl = false; out.push('</ol>');
    }
    if (ln.trim() === '') { out.push('<div class="sp-1"></div>'); }
    else { out.push(`<p>${esc(ln)}</p>`); }
  }
  if (inOl) out.push('</ol>');
  return out.join('\n');
}

function placeholderMap() {
  const studentFull = it.value?.student_name || '—';
  // حقول اختيارية قد لا تتوفر في النسخ الحالية من الـ API
  const sid = (it.value?.student && (it.value as any)?.student_sid) || (it.value as any)?.student_sid || '—';
  const className = (it.value as any)?.class_name || (it.value as any)?.student_class || '—';
  const incidentShort = String(it.value?.id || '').slice(-6) || '—';
  const incidentDate = fmtDate(it.value?.occurred_at);
  const incidentTimeHM = (()=>{ try{ return it.value?.occurred_at ? new Date(it.value.occurred_at).toLocaleTimeString('ar-QA', {hour:'2-digit', minute:'2-digit'}) : '—'; }catch{ return '—'; } })();
  const violCode = it.value?.violation?.code || '—';
  const violDisp = (it.value as any)?.violation_display || violCode;
  const followup = String((it.value as any)?.followup_window || 30);
  const guardian = (it.value as any)?.guardian_full_name || '__________________';
  const summary = it.value?.proposed_summary ? String(it.value?.proposed_summary) : '—';
  const docId = `PLEDG-${new Date().getFullYear()}-${incidentShort}`;
  const templateVer = 'v1.0';
  const reporterName = (it.value as any)?.reporter_name || (it.value as any)?.reporter_full_name || '—';
  const yearNow = new Date().getFullYear();
  const narrative = (it.value as any)?.narrative ? String((it.value as any).narrative) : '—';
  const periodNum = (it.value as any)?.period_number;
  const periodTime = (it.value as any)?.period_time_label || (it.value as any)?.occurred_time || '';
  const periodNumberOrDash = (periodNum && Number(periodNum) > 0) ? String(periodNum) : '—';
  const periodTimeSuffix = periodNum && periodTime ? ` (${periodTime})` : '';
  return new Map<string,string>([
    ['student_full_name', studentFull],
    ['student_sid', String(sid)],
    ['class_name', String(className)],
    ['incident_short_id', incidentShort],
    ['incident_date', String(incidentDate)],
    ['incident_time_hm', String(incidentTimeHM)],
    ['violation_code', String(violCode)],
    ['violation_display_or_code', String(violDisp)],
    ['followup_window', String(followup)],
    ['guardian_full_name', String(guardian)],
    ['proposed_summary_or_dash', String(summary || '—')],
    ['doc_id', String(docId)],
    ['template_version', String(templateVer)],
    ['reporter_name', String(reporterName)],
    ['current_year', String(yearNow)],
    ['incident_narrative_or_dash', String(narrative || '—')],
    ['period_number_or_dash', String(periodNumberOrDash)],
    ['period_time_suffix', String(periodTimeSuffix)],
    ['period_time_label_or_dash', String((it.value as any)?.period_time_label || '—')],
  ]);
}

function fillPlaceholders(template: string): string {
  const map = placeholderMap();
  return template.replace(/\{\{\s*([a-zA-Z0-9_]+)\s*\}\}/g, (_, k) => {
    return map.get(k) ?? '—';
  });
}

const studentPledgeHtml = computed(()=> toHtml(fillPlaceholders(renderStudentPledgeTemplate())));
const guardianPledgeHtml = computed(()=> toHtml(fillPlaceholders(renderGuardianPledgeTemplate())));
const oralHtml = computed(()=> toHtml(fillPlaceholders(renderOralTemplate())));

// إظهار «التنبيه الشفهي» في حالتيْن: الشدة ≤ 1 أو وُجد إجراء مسجل يشير لتنبيه شفهي
const hasOralAction = computed(()=>{
  try{
    const arr = Array.isArray(it.value?.actions_applied)? it.value.actions_applied as any[] : [];
    if (!arr || arr.length===0) return false;
    const txt = (x:any)=> (x?.name||'') + ' ' + (x?.code||'') + ' ' + (x?.description||'');
    return arr.some(a=> /تنبيه\s*شفهي|شفهي|oral\s*warning|verbal\s*warning/i.test(txt(a)) );
  }catch{ return false; }
});
const showOral = computed(()=> Number(it.value?.severity||0) <= 1 || hasOralAction.value);

async function reload(){
  loading.value = true; msg.value='';
  try{
    it.value = await getIncidentFull(id);
  }catch(e:any){
    msg.value = e?.message || 'تعذّر تحميل بيانات الواقعة';
  }finally{
    loading.value = false;
  }
}

onMounted(async ()=> {
  await reload();
  // دعم فتح الصفحة مع طباعة تلقائية لقسم محدد عبر باراميتر الاستعلام
  const section = String((route.query.section || route.query.print || '') as any).trim();
  if (section === 'oral' && showOral.value) {
    // انتظر دورة DOM ثم اطبع القسم المعزول
    nextTick(()=> printSection('oral'));
  }
});

// طباعة مبسطة: نطبع كامل الصفحة أو جزء منها حسب مرساة القسم
function printAll(){
  try{ window.print(); }catch{}
}

function printSection(section: 'oral'|'student_pledge'|'guardian_pledge'|'actions'|'sanctions'){
  // عزل قسم محدد للطباعة بشكل احترافي عبر صنف CSS مؤقت على الحاوية
  printOnly.value = section;
  const cleanup = () => { printOnly.value = null; window.removeEventListener('afterprint', cleanup); };
  window.addEventListener('afterprint', cleanup);
  nextTick(()=> {
    try { window.print(); } catch { cleanup(); }
    // احتياط للمتصفحات التي لا تُطلق afterprint ضمن المعاينة
    setTimeout(()=> { if (printOnly.value) cleanup(); }, 2000);
  });
}
</script>

<style scoped>
.prewrap { white-space: pre-wrap; }
.pledge-text { font-size: 0.96rem; line-height: 1.9; color:#333; }
.pledge-text .sp-1{ height:8px; }
.pledge-text ol{ padding-right: 1.25rem; margin: 0.25rem 0 0.5rem; }
.pledge-text p{ margin: 0.25rem 0; }
.oral-text { font-size: 1rem; line-height: 1.9; color:#222; }
.oral-text ol{ padding-right: 1.25rem; margin: 0.25rem 0 0.5rem; }
.oral-text p{ margin: 0.25rem 0; }
@media print {
  /* أظهر فقط منطقة الطباعة وأخفِ العناصر الأخرى (الهيدر، التنبيهات، ...). */
  .page-stack > :not(.print-area) { display: none !important; }
  .print-area { display: block !important; }
  .print-area .card { page-break-inside: avoid; break-inside: avoid; }
  html, body { background: #fff; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  /* عزل أقسام محددة عند الطباعة عند اختيارها */
  .page-stack.print-only-oral .print-area > .card:not([data-section="oral"]) { display: none !important; }
  .page-stack.print-only-student_pledge .print-area > .card:not([data-section="student_pledge"]) { display: none !important; }
  .page-stack.print-only-guardian_pledge .print-area > .card:not([data-section="guardian_pledge"]) { display: none !important; }
  .page-stack.print-only-actions .print-area > .card:not([data-section="actions"]) { display: none !important; }
  .page-stack.print-only-sanctions .print-area > .card:not([data-section="sanctions"]) { display: none !important; }
}
</style>
