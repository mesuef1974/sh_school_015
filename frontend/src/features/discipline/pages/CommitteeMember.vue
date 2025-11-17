<template>
  <section class="d-grid gap-9 committee-page" dir="rtl">
    <!-- شريط عنوان الصفحة (موحّد في المنصة) -->
    <WingPageHeader icon="solar:users-group-two-rounded-bold-duotone" title="لوحة عضو لجنة السلوك" :subtitle="'التصويت والمتابعة ضمن لجان الوقائع'">
      <template #actions>
        <div class="d-flex align-items-center gap-2 flex-wrap">
          <RouterLink class="btn btn-sm btn-outline-secondary" to="/discipline/committee/dashboard">لوحة الرئيس</RouterLink>
          <RouterLink class="btn btn-sm btn-outline-info" to="/discipline/committee/recorder">صفحة المقرر</RouterLink>
        </div>
      </template>
    </WingPageHeader>

    <div v-if="loading" class="alert alert-info py-2">جاري التحميل ...</div>
    <div v-else-if="error" class="alert alert-warning py-2">{{ error }}</div>

    <div v-else>
      <!-- شريط صلاحيات/أدوار -->
      <div v-if="caps" class="alert alert-secondary py-2 d-flex flex-wrap gap-2 align-items-center">
        <span class="fw-semibold">صلاحياتي:</span>
        <span v-if="caps.can_view" class="badge bg-primary-subtle text-primary">عرض مسار اللجنة</span>
        <span v-if="caps.can_schedule" class="badge bg-warning text-dark">تشكيل لجنة</span>
        <span v-if="caps.can_decide" class="badge bg-success">اعتماد قرار</span>
      </div>

      <div v-if="caps && !caps.can_view" class="alert alert-warning">لا تملك صلاحية عرض مسار اللجنة.</div>
      <template v-else>
      <!-- KPIs مختصرة -->
      <div class="row kpis g-7 mb-2">
        <div class="col-md-4 col-6">
          <div class="card kpi">
            <div class="kpi-title">وقائع ضمن لجنتي</div>
            <div class="kpi-value">{{ items.length }}</div>
          </div>
        </div>
        <div class="col-md-4 col-6">
          <div class="card kpi">
            <div class="kpi-title">مكتمل النصاب</div>
            <div class="kpi-value">{{ kpiQuorumMet }}</div>
          </div>
        </div>
        <div class="col-md-4 col-12">
          <div class="card kpi">
            <div class="kpi-title">أغلبية حالية</div>
            <div class="kpi-value small">
              <span class="badge me-1" :class="majClass('approve')">موافقة: {{ kpiMajority.approve }}</span>
              <span class="badge me-1" :class="majClass('reject')">رفض: {{ kpiMajority.reject }}</span>
              <span class="badge me-1" :class="majClass('return')">إعادة: {{ kpiMajority.return }}</span>
            </div>
          </div>
        </div>
      </div>
      <!-- دليل سريع مرتبط بدورة الحياة -->
      <div class="card mt-3">
        <div class="card-header">إرشادات سريعة حسب دورة حياة الواقعة</div>
        <div class="card-body small text-muted">
          <ol class="mb-0 lh-lg">
            <li>بعد <strong>جدولة اللجنة</strong> تظهر الوقائع هنا لكل عضو.</li>
            <li>صوّت على القرار: <span class="badge bg-success">موافقة</span> · <span class="badge bg-danger">رفض</span> · <span class="badge bg-warning text-dark">إعادة</span>.</li>
            <li>يعتمد الرئيس القرار النهائي عبر «قرار اللجنة» في بطاقة الواقعة.</li>
          </ol>
        </div>
      </div>

      <!-- قائمة الوقائع -->
      <div class="card mt-3">
        <div class="card-header">وقائع أنت ضمن لجنتها</div>
        <ul class="list-group list-group-flush">
          <li v-for="it in items" :key="it.id" class="list-group-item">
            <!-- السطر الرئيسي: الطالب + المخالفة + الشدة -->
            <div class="d-flex flex-wrap align-items-center gap-2">
              <div class="flex-grow-1">
                <div class="fw-semibold">{{ it.student_name || '—' }}</div>
                <div class="small text-muted">{{ it.violation_display || it.violation_code || '—' }}</div>
              </div>
              <span class="badge" :class="sevClass(it.severity)" :title="it.severity_label || 'الشدة'">
                {{ it.severity }}
              </span>
              <RouterLink class="btn btn-sm btn-link" :to="{name:'discipline-incident-card', params:{id: it.id}}" title="فتح بطاقة الواقعة">
                بطاقة الواقعة
              </RouterLink>
              <div class="ms-auto d-flex gap-1">
                <button class="btn btn-sm btn-outline-success" :disabled="busyId===it.id" @click="vote(it.id,'approve')" title="موافقة على قرار اللجنة المقترح لهذه الواقعة">موافقة</button>
                <button class="btn btn-sm btn-outline-danger" :disabled="busyId===it.id" @click="vote(it.id,'reject')" title="رفض قرار اللجنة المقترح لهذه الواقعة">رفض</button>
                <button class="btn btn-sm btn-outline-warning" :disabled="busyId===it.id" @click="vote(it.id,'return')" title="إعادة الواقعة لاستكمال بيانات/إجراءات قبل القرار">إعادة</button>
              </div>
            </div>
            <!-- سطر معلومات سياقية -->
            <div class="mt-2 small d-flex flex-wrap align-items-center gap-2">
              <span class="badge bg-light text-dark" title="عدد المرات خلال نافذة السياسة">
                تكرار {{ it.repeat_count_in_window ?? 0 }} خلال {{ it.repeat_window_days ?? 30 }} يومًا
              </span>
              <span v-if="it.committee_required" class="badge bg-primary" title="هذه الواقعة تتطلب لجنة حسب الشدة/التكرار/السياسة">تتطلب لجنة</span>
              <span v-if="it.escalated_due_to_repeat" class="badge bg-orange text-dark" title="تم تصعيدها بسبب التكرار">مصعّدة</span>
              <span v-if="summaries[it.id]" class="text-muted ms-auto">
                مشاركون: {{ summaries[it.id].summary.participated }}/{{ summaries[it.id].summary.total_voters }} ·
                الأغلبية: {{ decisionLabel(summaries[it.id].summary.majority) }}
              </span>
            </div>
            <!-- اختصار جديد: مركز الطباعة -->
            <div class="mt-2 d-flex flex-wrap gap-2">
              <RouterLink class="btn btn-sm btn-outline-dark" :to="{ name: 'discipline-incident-print', params: { id: it.id } }">مركز الطباعة</RouterLink>
            </div>
            <!-- وصف مختصر: تاريخ/زمن ومكان ونص الحادثة -->
            <div class="mt-2 text-muted small incident-brief">
              <span v-if="it.occurred_at">{{ new Date(it.occurred_at).toLocaleDateString('ar-QA') }}، {{ it.occurred_time || '' }}</span>
              <span v-if="it.location"> · المكان: {{ it.location }}</span>
              <span v-if="it.narrative"> · {{ (it.narrative || '').slice(0, 120) }}<span v-if="(it.narrative || '').length > 120">…</span></span>
            </div>
          </li>
          <li v-if="items.length===0" class="list-group-item">
            <div class="d-flex align-items-center">
              <span class="text-muted">لا توجد وقائع مجدولة لك حاليًا.</span>
              <RouterLink class="btn btn-sm btn-link ms-auto" to="/discipline/committee/dashboard">اذهب إلى لوحة الرئيس</RouterLink>
            </div>
          </li>
        </ul>
      </div>
      </template>
    </div>
  </section>
  </template>

<script setup lang="ts">
import { onMounted, reactive, ref, computed } from 'vue';
import { getMyCommittee, getCommitteeVotes, postCommitteeVote, getCommitteeCaps, getIncident, addIncidentAction } from '../../discipline/api';
import WingPageHeader from '../../../components/ui/WingPageHeader.vue';

const loading = ref(false);
const error = ref('');
const items = ref<any[]>([]);
const summaries = reactive<Record<string, any>>({});
const busyId = ref<string>('');
const caps = ref<any>(null);

function sevClass(sev?: number){
  const s = Number(sev||1);
  return s>=4? 'bg-danger': s===3? 'bg-warning text-dark': s===2? 'bg-info text-dark': 'bg-success';
}
function decisionLabel(d?: string|null){
  return d==='approve'?'موافقة': d==='reject'?'رفض': d==='return'?'إعادة':'—';
}

const kpiQuorumMet = computed(()=> Object.values(summaries).filter((s:any)=> s?.summary?.quorum_met).length);
const kpiMajority = computed(()=>{
  const agg = { approve: 0, reject: 0, return: 0 } as Record<'approve'|'reject'|'return', number>;
  for (const s of Object.values(summaries) as any[]){
    const m = s?.summary?.majority as 'approve'|'reject'|'return'|null;
    if (m && agg[m] !== undefined) agg[m]++;
  }
  return agg;
});
function majClass(k: 'approve'|'reject'|'return'){
  if (k==='approve') return 'bg-success';
  if (k==='reject') return 'bg-danger';
  return 'bg-warning text-dark';
}

async function reload(){
  loading.value = true; error.value='';
  try{
    try { const c = await getCommitteeCaps(); caps.value = c?.access_caps || null; } catch {}
    items.value = await getMyCommittee();
    // اجلب ملخص التصويت لكل عنصر (أفضل جهد)
    for (const it of items.value){
      try { summaries[it.id] = await getCommitteeVotes(it.id); } catch {}
    }
  }catch(e:any){
    error.value = e?.message || 'تعذّر تحميل البيانات';
  }finally{
    loading.value = false;
  }
}

async function vote(id: string, decision: 'approve'|'reject'|'return'){
  busyId.value = id;
  try{
    await postCommitteeVote(id, { decision });
    summaries[id] = await getCommitteeVotes(id);
  }catch(e:any){
    alert(e?.message || 'تعذّر تسجيل التصويت');
  }finally{
    busyId.value = '';
  }
}

onMounted(()=> reload());

// ======================= وظائف الطباعة (HTML — خيار A) =======================
// أداة موحّدة لفتح نافذة الطباعة مع مسارات بديلة عند الحجب
function openPrintWindowEnhanced(): Window|null {
  // المحاولة الأساسية — الأكثر موثوقية
  let w: Window|null = null;
  try { w = window.open('about:blank', '_blank', 'noopener,noreferrer'); } catch {}
  if (w) {
    try { w.opener = null; w.focus(); } catch {}
    try {
      w.document.open();
      w.document.write('<!doctype html><title>جاري التحضير للطباعة…</title><body dir="rtl" style="font-family:Segoe UI,Tahoma,Arial,sans-serif; padding:16px; color:#444;">جاري التحضير للطباعة…</body>');
      w.document.close();
    } catch {}
    return w;
  }
  // مسار بديل: إنشاء رابط target=_blank ومحاولة النقر عليه ضمن نفس حدث المستخدم
  try {
    const a = document.createElement('a');
    a.href = 'about:blank';
    a.target = '_blank';
    a.rel = 'noopener';
    a.style.display = 'none';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    // قد يكون قد فُتحت نافذة، لكن لا مرجع لنا. لا يمكننا الكتابة لها برمجيًا.
    // في هذه الحالة سنُسقط إلى المسار الخادمي الخاص بالعناصر التي تملك معاينة خادمية (التعهد).
  } catch {}
  return null;
}
function buildPlatformShell(base: string){
  const logo = `${base}/assets/img/logo.png?v=20251027-02`;
  const headLinks = `
  <style>
    /* طباعة: هوامش A4 وتثبيت الهيدر/الفوتر */
    @media print { @page { size: A4; margin: 2cm; } }
    body { font-family: 'Cairo','Segoe UI',Tahoma,Arial,sans-serif; color:#111; }
    .content-wrap{ padding: 1rem 0 2rem; }
    .doc-meta{font-size:12px;color:#666}
    /* هيدر وفوتر بنفس شكل المنصة */
    .navbar-maronia{ position:fixed; top:0; left:0; right:0; z-index:10; }
    .navbar-maronia nav{ background: linear-gradient(180deg,#8b1e24 0%, #6d141a 45%, #8b1e24 100%); color:#f9d39b; }
    .navbar-maronia .brand-images img{ height:44px; width:auto; display:block }
    .page-footer{ position:fixed; bottom:0; left:0; right:0; }
    .page-footer .container{ background:#7a1f2a; color:#caa86a; }
    .container{ max-width: 1024px; margin-inline:auto; padding-inline: 12px; }
    .py-2{ padding-block: .5rem; }
    .py-3{ padding-block: .75rem; }
    .d-flex{ display:flex; }
    .align-items-center{ align-items:center; }
    .gap-3{ gap:.75rem; }
    .small{ font-size: 12px; }
    .text-center{ text-align:center; }
    .w-100{ width:100%; }
    .flex-fill{ flex:1 1 auto; }
  </style>`;
  const header = `
  <header class="navbar-maronia">
    <nav class="container d-flex align-items-center gap-3 py-2" role="navigation" aria-label="التنقل الرئيسي">
      <div class="brand-images d-flex align-items-center">
        <img src="${logo}" alt="شعار" />
      </div>
      <span class="flex-fill"></span>
    </nav>
  </header>`;
  const footer = `
  <footer class="page-footer py-3">
    <div class="container d-flex justify-content-between small">
      <span class="text-center w-100">©2025 - جميع الحقوق محفوظة - مدرسة الشحانية الاعدادية الثانوية بنين - تطوير( المعلم/ سفيان مسيف s.mesyef0904@education.qa )</span>
    </div>
  </footer>`;
  return { headLinks, header, footer };
}

async function printPledgeStudentById(incidentId: string){
  // افتح النافذة فور النقر لتجنّب الحجب
  let w = openPrintWindowEnhanced();
  if(!w){
    // مسار احتياطي موثوق: افتح معاينة الخادم مباشرة في نفس التبويب بدون حوارات
    const base = import.meta.env.VITE_BACKEND_ORIGIN || `https://127.0.0.1:${import.meta.env.VITE_BACKEND_PORT||8443}`;
    window.location.assign(`${base}/api/v1/discipline/incidents/${incidentId}/pledge/preview/?format=html`);
    return;
  }
  try{
    try { w.opener = null; w.focus(); } catch {}

    const data:any = await getIncident(incidentId);
    const base = import.meta.env.VITE_BACKEND_ORIGIN || `https://127.0.0.1:${import.meta.env.VITE_BACKEND_PORT||8443}`;
    const shell = buildPlatformShell(base);
    const now = new Date(); const y = now.getFullYear(); const m = String(now.getMonth()+1).padStart(2,'0'); const d = String(now.getDate()).padStart(2,'0');
    const shortId = String(data.id || '').slice(0,8);
    const docId = `PLEDG-${y}${m}-${shortId}`;
    const proposed = data.proposed_summary || '—';
    const studentName = data.student_name || `#${data.student}`;
    const viol = data.violation_display || data.violation_code || '—';
    const occurred = fmtDate(data.occurred_at);
    const location = data.location || '—';
    const severity = Number(data.severity||0) || '—';
    const html = `<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8" />
  <title>تعهد خطي — ${studentName}</title>
  ${shell.headLinks}
  </head>
  <body>
    <div class="page-container">
    ${shell.header}
    <main class="page-main container content-wrap">
      <h1>تعهد خطي بشأن التزام السلوك المدرسي</h1>
      <div class="row box" style="margin-bottom:12px;">
        <div><div class="muted">الطالب</div><div>${studentName}</div></div>
        <div><div class="muted">رقم الواقعة</div><div>${shortId}</div></div>
        <div><div class="muted">التاريخ</div><div>${occurred}</div></div>
        <div><div class="muted">المخالفة</div><div>${viol}</div></div>
        <div><div class="muted">المكان</div><div>${location}</div></div>
        <div><div class="muted">الشدة</div><div>${severity}</div></div>
      </div>
      <div class="box">
        <div class="title">نص التعهد</div>
        <p>
          أنا الطالب المذكور أعلاه، أقرّ بأنني اطّلعت على الواقعة رقم ${shortId}
          المتعلقة بالمخالفة المبينة، وأتعهد بما يلي:
        </p>
        <ol>
          <li>الالتزام التام بقواعد السلوك والانضباط المدرسي، وتجنّب تكرار المخالفة.</li>
          <li>التعاون مع الهيئتين التعليمية والإرشادية، وحضور الجلسات أو الأنشطة العلاجية عند الطلب.</li>
          <li>قبول المتابعة الدورية خلال مدة زمنية مناسبة والامتثال للتوجيهات الصادرة.</li>
          <li>العلم بأن تكرار المخالفة قد يترتب عليه إجراءات أشد وفق لائحة السلوك والمواظبة.</li>
        </ol>
        <div class="title" style="margin-top:10px;">تعهد ولي الأمر</div>
        <p>
          أنا ولي أمر الطالب المذكور، أتعهد بمتابعة ابني، والتعاون مع المدرسة،
          وحضور الاجتماعات عند الاستدعاء، وإعلام المدرسة بأي ظروف قد تؤثر على السلوك.
        </p>
        <div class="muted">ملخص الإجراء/التوصية (إن وُجد):</div>
        <div style="font-weight:600; margin-bottom:8px;">${proposed}</div>
        <div class="sig-grid">
          <div class="sig">
            <div class="muted">توقيع الطالب</div>
            <span class="line"></span>
            <div class="muted">الاسم الثلاثي: ____________ · التاريخ: ____/____/______</div>
          </div>
          <div class="sig">
            <div class="muted">توقيع ولي الأمر</div>
            <span class="line"></span>
            <div class="muted">الاسم: ________________ · الهوية: ____________ · التاريخ: ____/____/______</div>
          </div>
          <div class="sig">
            <div class="muted">ختم المدرسة / موظف الاستلام</div>
            <span class="line"></span>
            <div class="muted">الاسم: ________________ · التاريخ: ____/____/______</div>
          </div>
        </div>
        <div class="doc-meta">رقم الوثيقة: ${docId} · قالب الطباعة: v1.0 · تاريخ الإصدار: ${y}-${m}-${d}</div>
        <div style="margin-top:8px; display:flex; align-items:center; gap:12px;">
          <div class="qr" aria-label="QR placeholder"></div>
          <div class="muted">للاطّلاع والتحقق لاحقًا سيُدرج رمز QR ضمن نسخة PDF الموحّدة.</div>
        </div>
      </div>
    </main>
    ${shell.footer}
    </div>
    <script>window.onload = function(){ setTimeout(function(){ try{ window.focus(); }catch(e){}; if (window.print) window.print(); }, 120); }; window.onafterprint = function(){ setTimeout(function(){ try{ window.close(); }catch(e){} }, 200); };<\/script>
  </body>
</html>`;
    w.document.open(); w.document.write(html); w.document.close();
    try { await addIncidentAction(incidentId, { name: 'تعهد خطي (طباعة)', notes: 'رقم الوثيقة: '+docId }); } catch {}
  }catch(e:any){
    try{ w.close(); }catch{}
    alert(e?.message || 'فشل في طباعة التعهد');
  }
}

async function printPledgeGuardianById(incidentId: string){
  let w = openPrintWindowEnhanced();
  // إن حُجبت النوافذ، اطبع في نفس التبويب عبر Blob
  const data:any = await getIncident(incidentId);
  const base = import.meta.env.VITE_BACKEND_ORIGIN || `https://127.0.0.1:${import.meta.env.VITE_BACKEND_PORT||8443}`;
  const shell = buildPlatformShell(base);
  const now = new Date(); const y = now.getFullYear(); const m = String(now.getMonth()+1).padStart(2,'0'); const d = String(now.getDate()).padStart(2,'0');
  const shortId = String(data.id || '').slice(0,8);
  const docId = `PLEDG-${y}${m}-${shortId}`;
  const studentName = data.student_name || `#${data.student}`;
  const viol = data.violation_display || data.violation_code || '—';
  const occurred = fmtDate(data.occurred_at);
  const location = data.location || '—';
  const severity = Number(data.severity||0) || '—';
  const guardianHtml = `<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8" />
  <title>تعهد ولي الأمر — ${studentName}</title>
  ${shell.headLinks}
</head>
<body>
  <div class="page-container">
    ${shell.header}
    <main class="page-main container content-wrap">
      <h1>تعهد ولي الأمر بشأن متابعة السلوك</h1>
      <div class="row box" style="margin-bottom:12px;">
        <div><div class="muted">الطالب</div><div>${studentName}</div></div>
        <div><div class="muted">رقم الواقعة</div><div>${shortId}</div></div>
        <div><div class="muted">التاريخ</div><div>${occurred}</div></div>
        <div><div class="muted">المخالفة</div><div>${viol}</div></div>
        <div><div class="muted">المكان</div><div>${location}</div></div>
        <div><div class="muted">الشدة</div><div>${severity}</div></div>
      </div>
      <div class="box">
        <p>
          أنا ولي أمر الطالب المذكور أعلاه، اطّلعت على تفاصيل الواقعة المشار إليها،
          وأتعهد بالتالي:
        </p>
        <ol>
          <li>متابعة سلوك ابني بانتظام والتعاون مع المدرسة في أي خطة علاجية أو إرشادية.</li>
          <li>الالتزام بحضور الاجتماعات عند الاستدعاء، والاستجابة لأي تواصل من المدرسة.</li>
          <li>إعلام المدرسة بأي ظروف قد تؤثر على السلوك أو المتابعة.</li>
          <li>تفهم أن تكرار المخالفة قد يترتب عليه إجراءات أشد وفق لوائح السلوك.</li>
        </ol>
        <div class="sig-grid">
          <div class="sig">
            <div class="muted">توقيع ولي الأمر</div>
            <span class="line"></span>
            <div class="muted">الاسم: ________________ · الهوية: ____________ · التاريخ: ____/____/______</div>
          </div>
          <div class="sig">
            <div class="muted">بيانات التواصل</div>
            <span class="line"></span>
            <div class="muted">الهاتف: ____________ · البريد: __________________</div>
          </div>
          <div class="sig">
            <div class="muted">ختم المدرسة / موظف الاستلام</div>
            <span class="line"></span>
            <div class="muted">الاسم: ________________ · التاريخ: ____/____/______</div>
          </div>
        </div>
        <div class="doc-meta">رقم الوثيقة: ${docId} · قالب الطباعة: v1.0 · تاريخ الإصدار: ${y}-${m}-${d}</div>
      </div>
    </main>
    ${shell.footer}
  </div>
  <script>window.onload = function(){ setTimeout(function(){ try{ window.focus(); }catch(e){}; if (window.print) window.print(); }, 120); }; window.onafterprint = function(){ setTimeout(function(){ try{ window.close(); }catch(e){} }, 200); };<\/script>
</body>
</html>`;
  if (!w){
    const blob = new Blob([guardianHtml], { type: 'text/html;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    window.location.assign(url);
    return;
  }
  try{
    w.document.open(); w.document.write(guardianHtml); w.document.close();
    try { await addIncidentAction(incidentId, { name: 'تعهد ولي الأمر (طباعة)', notes: 'رقم الوثيقة: '+docId }); } catch {}
  }catch(e:any){ try{ w.close(); }catch{}; alert(e?.message || 'فشل في طباعة تعهد ولي الأمر'); }
}

async function printOralById(incidentId: string){
  // افتح النافذة مبكرًا لتجنّب الحجب
  let w = openPrintWindowEnhanced();
  if(!w){
    // مسار بديل: الطباعة في نفس التبويب عند حجب النوافذ
    try{
      const data:any = await getIncident(incidentId);
      if (Number(data.severity||0) > 1) {
        alert('التنبيه الشفهي مخصص للوقائع البسيطة (مستوى 1)');
        return;
      }
      const base = import.meta.env.VITE_BACKEND_ORIGIN || `https://127.0.0.1:${import.meta.env.VITE_BACKEND_PORT||8443}`;
      const shell = buildPlatformShell(base);
      const now = new Date(); const y = now.getFullYear(); const m = String(now.getMonth()+1).padStart(2,'0'); const d = String(now.getDate()).padStart(2,'0');
      const shortId = String(data.id || '').slice(0,8);
      const docId = `ORAL-${y}${m}-${shortId}`;
      const studentName = data.student_name || `#${data.student}`;
      const viol = data.violation_display || data.violation_code || '—';
      const occurred = fmtDate(data.occurred_at);
      const location = data.location || '—';
      const html = `<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8" />
  <title>تنبيه شفهي — ${studentName}</title>
  ${shell.headLinks}
  </head>
  <body>
    <div class="page-container">${shell.header}
      <main class="page-main container content-wrap">
        <h1>تنبيه شفهي للطالب/ـة</h1>
        <div class="row box" style="margin-bottom:12px;">
          <div><div class="muted">الطالب</div><div>${studentName}</div></div>
          <div><div class="muted">رقم الواقعة</div><div>${shortId}</div></div>
          <div><div class="muted">التاريخ</div><div>${occurred}</div></div>
          <div><div class="muted">المخالفة</div><div>${viol}</div></div>
          <div><div class="muted">المكان</div><div>${location}</div></div>
        </div>
        <div class="box">
          <p>
            تم توجيه <strong>تنبيه شفهي</strong> للطالب/ـة المذكور أعلاه بخصوص الواقعة المشار إليها،
            وذلك للتأكيد على ضرورة الالتزام بقواعد السلوك والانضباط المدرسي وعدم تكرار المخالفة.
          </p>
          <ul>
            <li>توضيح أثر المخالفة على البيئة التعليمية وزملاء الدراسة.</li>
            <li>أخذ تعهّد شفهي بالالتزام مستقبلاً والتعاون مع المعنيين.</li>
          </ul>
          <div class="muted">ملاحظات المبلّغ/المراجع (اختياري): _______________________________</div>
          <div class="sig">
            <div class="muted">توقيع الموظف</div>
            <span class="line"></span>
            <div class="muted">الاسم: ________________ · التاريخ: ____/____/______</div>
          </div>
        </div>
      </main>
      ${shell.footer}
    </div>
    <script>window.onload = function(){ setTimeout(function(){ try{ window.focus(); }catch(e){}; if (window.print) window.print(); }, 120); }; window.onafterprint = function(){ setTimeout(function(){ try{ window.close(); }catch(e){} }, 200); };<\/script>
  </body>
</html>`;
      const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      window.location.assign(url);
      return;
    }catch(e:any){
      alert(e?.message || 'تعذّر فتح أو طباعة التنبيه الشفهي. فعّل النوافذ المنبثقة أو أعد المحاولة.');
      return;
    }
  }
  try{
    try { w.opener = null; w.focus(); } catch {}

    const data:any = await getIncident(incidentId);
    const base = import.meta.env.VITE_BACKEND_ORIGIN || `https://127.0.0.1:${import.meta.env.VITE_BACKEND_PORT||8443}`;
    const shell = buildPlatformShell(base);
    if (Number(data.severity||0) > 1) {
      alert('التنبيه الشفهي مخصص للوقائع البسيطة (مستوى 1)');
      try{ w.close(); }catch{}
      return;
    }
    const now = new Date(); const y = now.getFullYear(); const m = String(now.getMonth()+1).padStart(2,'0'); const d = String(now.getDate()).padStart(2,'0');
    const shortId = String(data.id || '').slice(0,8);
    const docId = `ORAL-${y}${m}-${shortId}`;
    const studentName = data.student_name || `#${data.student}`;
    const viol = data.violation_display || data.violation_code || '—';
    const occurred = fmtDate(data.occurred_at);
    const html = `<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8" />
  <title>تنبيه شفهي — ${studentName}</title>
  ${shell.headLinks}
  </head>
  <body>
    <div class="page-container">
      ${shell.header}
      <main class="page-main container content-wrap">
        <h1>تنبيه شفهي للطالب/ـة</h1>
        <div class="row box" style="margin-bottom:12px;">
          <div><div class="muted">الطالب</div><div>${studentName}</div></div>
          <div><div class="muted">رقم الواقعة</div><div>${shortId}</div></div>
          <div><div class="muted">التاريخ</div><div>${occurred}</div></div>
          <div><div class="muted">المخالفة</div><div>${viol}</div></div>
        </div>
        <div class="box">
          <p>
            تم توجيه <strong>تنبيه شفهي</strong> للطالب/ـة المذكور أعلاه بخصوص الواقعة المشار إليها،
            وذلك للتأكيد على ضرورة الالتزام بقواعد السلوك والانضباط المدرسي وعدم تكرار المخالفة.
          </p>
          <ul>
            <li>توضيح أثر المخالفة على البيئة التعليمية وزملاء الدراسة.</li>
            <li>أخذ تعهّد شفهي بالالتزام مستقبلاً والتعاون مع المعنيين.</li>
          </ul>
          <div class="muted">ملاحظات المبلّغ/المراجع (اختياري): _______________________________</div>
          <div class="sig">
            <div class="muted">توقيع الموظف</div>
            <span class="line"></span>
            <div class="muted">الاسم: ________________ · التاريخ: ____/____/______</div>
          </div>
        </div>
      </main>
      ${shell.footer}
    </div>
    <script>window.onload = function(){ setTimeout(function(){ try{ window.focus(); }catch(e){}; if (window.print) window.print(); }, 120); }; window.onafterprint = function(){ setTimeout(function(){ try{ window.close(); }catch(e){} }, 200); };<\/script>
  </body>
</html>`;
    w.document.open(); w.document.write(html); w.document.close();
    try { await addIncidentAction(incidentId, { name: 'تنبيه شفهي (طباعة)', notes: 'رقم الوثيقة: '+docId }); } catch {}
  }catch(e:any){
    try{ w.close(); }catch{}
    alert(e?.message || 'فشل في طباعة التنبيه الشفهي');
  }
}

async function printActsById(incidentId: string){
  // افتح النافذة مبكرًا لتجنّب الحجب
  let w = openPrintWindowEnhanced();
  if(!w){
    // مسار بديل: الطباعة في نفس التبويب عند حجب النوافذ
    try{
      const data:any = await getIncident(incidentId);
      const base = import.meta.env.VITE_BACKEND_ORIGIN || `https://127.0.0.1:${import.meta.env.VITE_BACKEND_PORT||8443}`;
      const shell = buildPlatformShell(base);
      const now = new Date(); const y = now.getFullYear(); const m = String(now.getMonth()+1).padStart(2,'0'); const d = String(now.getDate()).padStart(2,'0');
      const shortId = String(data.id || '').slice(0,8);
      const docId = `ACTS-${y}${m}-${shortId}`;
      const studentName = data.student_name || `#${data.student}`;
      const viol = data.violation_display || data.violation_code || '—';
      const occurred = fmtDate(data.occurred_at);
      const location = data.location || '—';
      const severity = Number(data.severity||0) || '—';
      const proposed = data.proposed_summary || '—';
      const items: any[] = Array.isArray(data.actions_applied)? data.actions_applied : [];
      const rows = items.map((a:any,idx:number)=> `<tr><td>${idx+1}</td><td>${(a?.name||'').toString()}</td><td>${(a?.notes||'').toString()}</td><td>${a?.at? new Date(a.at).toLocaleString(): ''}</td></tr>`).join('');
      const html = `<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8" />
  <title>إجراءات اللجنة — ${studentName}</title>
  ${shell.headLinks}
  </head>
  <body>
    <div class="page-container">${shell.header}
      <main class="page-main container content_wrap">
        <h1>إجراءات اللجنة المعتمدة/المقترحة</h1>
        <div class="box" style="margin-bottom:8px; color:#555;">
          <div class="row">
            <div><div class="muted">الطالب</div><div><strong>${studentName}</strong></div></div>
            <div><div class="muted">رقم الواقعة</div><div>${shortId}</div></div>
            <div><div class="muted">التاريخ</div><div>${occurred}</div></div>
            <div><div class="muted">المخالفة</div><div>${viol}</div></div>
            <div><div class="muted">المكان</div><div>${location}</div></div>
            <div><div class="muted">الشدة</div><div>${severity}</div></div>
          </div>
          <div class="muted" style="margin-top:6px;">الإجراء/التوصية المختصرة: <span style="font-weight:600; color:#222;">${proposed}</span></div>
        </div>
        <table>
          <thead><tr><th>#</th><th>الإجراء</th><th>ملاحظات</th><th>التاريخ/الوقت</th></tr></thead>
          <tbody>${rows || '<tr><td colspan="4" style="text-align:center; color:#888;">— لا توجد إجراءات —</td></tr>'}</tbody>
        </table>
      </main>
      ${shell.footer}
    </div>
    <script>window.onload = function(){ setTimeout(function(){ try{ window.focus(); }catch(e){}; if (window.print) window.print(); }, 120); }; window.onafterprint = function(){ setTimeout(function(){ try{ window.close(); }catch(e){} }, 200); };<\/script>
  </body>
</html>`;
      const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      window.location.assign(url);
      return;
    }catch(e:any){
      alert(e?.message || 'تعذّر فتح أو طباعة «إجراءات اللجنة». فعّل النوافذ المنبثقة أو أعد المحاولة.');
      return;
    }
  }
  try{
    try { w.opener = null; w.focus(); } catch {}

    const data:any = await getIncident(incidentId);
    const base = import.meta.env.VITE_BACKEND_ORIGIN || `https://127.0.0.1:${import.meta.env.VITE_BACKEND_PORT||8443}`;
    const shell = buildPlatformShell(base);
    const now = new Date(); const y = now.getFullYear(); const m = String(now.getMonth()+1).padStart(2,'0'); const d = String(now.getDate()).padStart(2,'0');
    const shortId = String(data.id || '').slice(0,8);
    const docId = `ACTS-${y}${m}-${shortId}`;
    const studentName = data.student_name || `#${data.student}`;
    const viol = data.violation_display || data.violation_code || '—';
    const occurred = fmtDate(data.occurred_at);
    const location = data.location || '—';
    const severity = Number(data.severity||0) || '—';
    const proposed = data.proposed_summary || '—';
    const items: any[] = Array.isArray(data.actions_applied)? data.actions_applied : [];
    const rows = items.map((a:any,idx:number)=> `<tr><td>${idx+1}</td><td>${(a?.name||'').toString()}</td><td>${(a?.notes||'').toString()}</td><td>${a?.at? new Date(a.at).toLocaleString(): ''}</td></tr>`).join('');
    const html = `<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8" />
  <title>إجراءات اللجنة — ${studentName}</title>
  ${shell.headLinks}
  </head>
  <body>
    <div class="page-container">
      ${shell.header}
      <main class="page-main container content-wrap">
        <h1>إجراءات اللجنة المعتمدة/المقترحة</h1>
        <div class="box" style="margin-bottom:8px; color:#555;">
          <div class="row">
            <div><div class="muted">الطالب</div><div><strong>${studentName}</strong></div></div>
            <div><div class="muted">رقم الواقعة</div><div>${shortId}</div></div>
            <div><div class="muted">التاريخ</div><div>${occurred}</div></div>
            <div><div class="muted">المخالفة</div><div>${viol}</div></div>
            <div><div class="muted">المكان</div><div>${location}</div></div>
            <div><div class="muted">الشدة</div><div>${severity}</div></div>
          </div>
          <div class="muted" style="margin-top:6px;">الإجراء/التوصية المختصرة: <span style="font-weight:600; color:#222;">${proposed}</span></div>
        </div>
        <table>
          <thead><tr><th>#</th><th>الإجراء</th><th>ملاحظات</th><th>التاريخ/الوقت</th></tr></thead>
          <tbody>${rows || '<tr><td colspan="4" style="text-align:center; color:#888;">— لا توجد إجراءات —</td></tr>'}</tbody>
        </table>
      </main>
      ${shell.footer}
    </div>
    <script>window.onload = function(){ setTimeout(function(){ try{ window.focus(); }catch(e){}; if (window.print) window.print(); }, 120); }; window.onafterprint = function(){ setTimeout(function(){ try{ window.close(); }catch(e){} }, 200); };<\/script>
  </body>
</html>`;
    w.document.open(); w.document.write(html); w.document.close();
    try { await addIncidentAction(incidentId, { name: 'إجراءات اللجنة (طباعة)', notes: 'رقم الوثيقة: '+docId }); } catch {}
  }catch(e:any){
    try{ w.close(); }catch{}
    alert(e?.message || 'فشل في طباعة إجراءات اللجنة');
  }
}

async function printSancById(incidentId: string){
  // افتح النافذة مبكرًا لتجنّب الحجب
  let w = openPrintWindowEnhanced();
  if(!w){
    // مسار بديل: الطباعة في نفس التبويب عند حجب النوافذ
    try{
      const data:any = await getIncident(incidentId);
      const base = import.meta.env.VITE_BACKEND_ORIGIN || `https://127.0.0.1:${import.meta.env.VITE_BACKEND_PORT||8443}`;
      const shell = buildPlatformShell(base);
      const now = new Date(); const y = now.getFullYear(); const m = String(now.getMonth()+1).padStart(2,'0'); const d = String(now.getDate()).padStart(2,'0');
      const shortId = String(data.id || '').slice(0,8);
      const docId = `SANC-${y}${m}-${shortId}`;
      const studentName = data.student_name || `#${data.student}`;
      const viol = data.violation_display || data.violation_code || '—';
      const occurred = fmtDate(data.occurred_at);
      const location = data.location || '—';
      const severity = Number(data.severity||0) || '—';
      const proposed = data.proposed_summary || '—';
      const items: any[] = Array.isArray(data.sanctions_applied)? data.sanctions_applied : [];
      const rows = items.map((a:any,idx:number)=> `<tr><td>${idx+1}</td><td>${(a?.name||'').toString()}</td><td>${(a?.notes||'').toString()}</td><td>${a?.at? new Date(a.at).toLocaleString(): ''}</td></tr>`).join('');
      const html = `<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8" />
  <title>عقوبات اللجنة — ${studentName}</title>
  ${shell.headLinks}
  </head>
  <body>
    <div class="page-container">${shell.header}
      <main class="page-main container content-wrap">
        <h1>عقوبات اللجنة المعتمدة/المقترحة</h1>
        <div class="box" style="margin-bottom:8px; color:#555;">
          <div class="row">
            <div><div class="muted">الطالب</div><div><strong>${studentName}</strong></div></div>
            <div><div class="muted">رقم الواقعة</div><div>${shortId}</div></div>
            <div><div class="muted">التاريخ</div><div>${occurred}</div></div>
            <div><div class="muted">المخالفة</div><div>${viol}</div></div>
            <div><div class="muted">المكان</div><div>${location}</div></div>
            <div><div class="muted">الشدة</div><div>${severity}</div></div>
          </div>
          <div class="muted" style="margin-top:6px;">الإجراء/التوصية المختصرة: <span style="font-weight:600; color:#222;">${proposed}</span></div>
        </div>
        <table>
          <thead><tr><th>#</th><th>العقوبة</th><th>ملاحظات</th><th>التاريخ/الوقت</th></tr></thead>
          <tbody>${rows || '<tr><td colspan="4" style="text-align:center; color:#888;">— لا توجد عقوبات —</td></tr>'}</tbody>
        </table>
      </main>
      ${shell.footer}
    </div>
    <script>window.onload = function(){ setTimeout(function(){ try{ window.focus(); }catch(e){}; if (window.print) window.print(); }, 120); }; window.onafterprint = function(){ setTimeout(function(){ try{ window.close(); }catch(e){} }, 200); };<\/script>
  </body>
</html>`;
      const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      window.location.assign(url);
      return;
    }catch(e:any){
      alert(e?.message || 'تعذّر فتح أو طباعة «عقوبات اللجنة». فعّل النوافذ المنبثقة أو أعد المحاولة.');
      return;
    }
  }
  try{
    try { w.opener = null; w.focus(); } catch {}

    const data:any = await getIncident(incidentId);
    const base = import.meta.env.VITE_BACKEND_ORIGIN || `https://127.0.0.1:${import.meta.env.VITE_BACKEND_PORT||8443}`;
    const shell = buildPlatformShell(base);
    const now = new Date(); const y = now.getFullYear(); const m = String(now.getMonth()+1).padStart(2,'0'); const d = String(now.getDate()).padStart(2,'0');
    const shortId = String(data.id || '').slice(0,8);
    const docId = `SANC-${y}${m}-${shortId}`;
    const studentName = data.student_name || `#${data.student}`;
    const viol = data.violation_display || data.violation_code || '—';
    const occurred = fmtDate(data.occurred_at);
    const location = data.location || '—';
    const severity = Number(data.severity||0) || '—';
    const proposed = data.proposed_summary || '—';
    const items: any[] = Array.isArray(data.sanctions_applied)? data.sanctions_applied : [];
    const rows = items.map((a:any,idx:number)=> `<tr><td>${idx+1}</td><td>${(a?.name||'').toString()}</td><td>${(a?.notes||'').toString()}</td><td>${a?.at? new Date(a.at).toLocaleString(): ''}</td></tr>`).join('');
    const html = `<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8" />
  <title>عقوبات اللجنة — ${studentName}</title>
  ${shell.headLinks}
  </head>
  <body>
    <div class="page-container">
      ${shell.header}
      <main class="page-main container content-wrap">
        <h1>عقوبات اللجنة المعتمدة/المقترحة</h1>
        <div class="box" style="margin-bottom:8px; color:#555;">
          <div class="row">
            <div><div class="muted">الطالب</div><div><strong>${studentName}</strong></div></div>
            <div><div class="muted">رقم الواقعة</div><div>${shortId}</div></div>
            <div><div class="muted">التاريخ</div><div>${occurred}</div></div>
            <div><div class="muted">المخالفة</div><div>${viol}</div></div>
            <div><div class="muted">المكان</div><div>${location}</div></div>
            <div><div class="muted">الشدة</div><div>${severity}</div></div>
          </div>
          <div class="muted" style="margin-top:6px;">الإجراء/التوصية المختصرة: <span style="font-weight:600; color:#222;">${proposed}</span></div>
        </div>
        <table>
          <thead><tr><th>#</th><th>العقوبة</th><th>ملاحظات</th><th>التاريخ/الوقت</th></tr></thead>
          <tbody>${rows || '<tr><td colspan="4" style="text-align:center; color:#888;">— لا توجد عقوبات —</td></tr>'}</tbody>
        </table>
      </main>
      ${shell.footer}
    </div>
    <script>window.onload = function(){ setTimeout(function(){ try{ window.focus(); }catch(e){}; if (window.print) window.print(); }, 120); }; window.onafterprint = function(){ setTimeout(function(){ try{ window.close(); }catch(e){} }, 200); };<\/script>
  </body>
</html>`;
    w.document.open(); w.document.write(html); w.document.close();
    try { await addIncidentAction(incidentId, { name: 'عقوبات اللجنة (طباعة)', notes: 'رقم الوثيقة: '+docId }); } catch {}
  }catch(e:any){
    try{ w.close(); }catch{}
    alert(e?.message || 'فشل في طباعة عقوبات اللجنة');
  }
}

// أداة محلية لتنسيق التاريخ بنمط YYYY-MM-DD أو من ISO
function fmtDate(s?: string){
  if(!s) return '—';
  try{
    if (s.length === 10 && /^\d{4}-\d{2}-\d{2}$/.test(s)) return s;
    const d = new Date(s as string);
    const y = d.getFullYear(); const m = String(d.getMonth()+1).padStart(2,'0'); const d2 = String(d.getDate()).padStart(2,'0');
    return `${y}-${m}-${d2}`;
  }catch{ return '—'; }
}
</script>

<style scoped>
.committee-page .card { border-radius: 12px; box-shadow: 0 1px 2px rgba(0,0,0,.04); }
.committee-page .card + .card { margin-top: 1.25rem; }
.committee-page .row { --bs-gutter-x: 3rem; --bs-gutter-y: 2.5rem; }
.list-group-item { padding-top: .9rem; padding-bottom: .9rem; }
.kpi { padding: 12px 14px; }
.kpi-title { font-size: 12px; color: #666; padding: 6px 12px 0; }
.kpi-value { font-size: 24px; font-weight: 700; padding: 0 12px 10px; }
.kpis { --bs-gutter-x: 2.5rem; --bs-gutter-y: 1.5rem; }

@media (max-width: 768px){
  .committee-page .row { --bs-gutter-x: 1.25rem; --bs-gutter-y: 1.25rem; }
}
</style>
