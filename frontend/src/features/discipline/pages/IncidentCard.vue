<template>
  <section class="container py-3" dir="rtl">
    <div class="page-stack">
      <!-- شريط العنوان -->
      <WingPageHeader :icon="tileMeta.icon" :title="titleBar" :color="sevColor" :subtitle="subtitleBar">
        <template #actions>
          <div class="d-flex flex-wrap gap-2">
            <button v-if="it && it.status==='open'" class="btn btn-primary" :disabled="busy" @click="onSubmit">إرسال للمراجعة</button>
            <button v-if="it && it.status==='under_review'" class="btn btn-outline-success" :disabled="busy" @click="onReview">اعتماد المراجعة</button>
            <button v-if="it && it.status!=='closed'" class="btn btn-outline-warning" :disabled="busy" @click="onEscalate">تصعيد</button>
            <button v-if="it && it.status==='under_review'" class="btn btn-outline-info" :disabled="busy" @click="onNotify">إشعار ولي الأمر</button>
            <button v-if="it && it.status!=='closed'" class="btn btn-outline-secondary" :disabled="busy" @click="onClose">إغلاق</button>
            <!-- مركز الطباعة الموحد -->
            <RouterLink v-if="it" class="btn btn-outline-dark" :to="{ name: 'discipline-incident-print', params: { id: it.id } }">مركز الطباعة</RouterLink>
            <!-- اختصار مباشر لطباعة التنبيه الشفهي عند الشدة 1 -->
            <RouterLink
              v-if="it && Number(it.severity||0) <= 1"
              class="btn btn-outline-dark"
              :to="{ name: 'discipline-incident-print', params: { id: it.id }, query: { section: 'oral' } }"
              title="فتح صفحة الطباعة على التنبيه الشفهي"
            >تنبيه شفهي</RouterLink>
            <button class="btn btn-outline-dark" :disabled="loading" @click="reload">تحديث</button>
          </div>
        </template>
      </WingPageHeader>

      <div class="row g-3">
        <div class="col-lg-8 col-12">
          <!-- بطاقة تفاصيل أساسية -->
          <div class="card p-3">
            <div class="row g-2">
              <div class="col-md-6 col-12">
                <div class="text-muted small">الطالب</div>
                <div class="fw-bold">{{ it?.student_name || ('#'+it?.student) }}</div>
              </div>
              <div class="col-md-6 col-12">
                <div class="text-muted small">المخالفة</div>
                <div class="fw-bold">{{ it?.violation_display || it?.violation?.code }}</div>
              </div>
              <div class="col-md-4 col-6">
                <div class="text-muted small">التاريخ</div>
                <div>{{ fmtDate(it?.occurred_at) }}</div>
              </div>
              <div class="col-md-4 col-6">
                <div class="text-muted small">الموقع</div>
                <div>{{ it?.location || '—' }}</div>
              </div>
              <div class="col-md-4 col-6">
                <div class="text-muted small">الشدة</div>
                <span class="badge" :style="{backgroundColor: sevColor, color: '#fff'}">{{ it?.severity ?? '—' }}</span>
              </div>
              <div class="col-12">
                <div class="text-muted small">الوصف</div>
                <div class="prewrap">{{ it?.narrative || '—' }}</div>
              </div>
            </div>
          </div>

          <!-- حالة وسلا وبيانات اللجنة -->
          <div class="card p-3 mt-3">
            <div class="d-flex flex-wrap gap-3 align-items-center">
              <div>
                <div class="text-muted small">استحقاق مراجعة المشرف</div>
                <div>{{ it?.review_sla_due_at ? fmtDateTime(it!.review_sla_due_at) : '—' }}</div>
                <span v-if="it?.is_overdue_review" class="badge bg-danger mt-1">متجاوز</span>
              </div>
              <div>
                <div class="text-muted small">استحقاق إشعار ولي الأمر</div>
                <div>{{ it?.notify_sla_due_at ? fmtDateTime(it!.notify_sla_due_at) : '—' }}</div>
                <span v-if="it?.is_overdue_notify" class="badge bg-danger mt-1">متجاوز</span>
              </div>
              <div>
                <div class="text-muted small">الحالة</div>
                <span class="badge" :class="badgeFor(it?.status)">{{ statusAr(it?.status) }}</span>
              </div>
              <div>
                <div class="text-muted small">لجنة؟</div>
                <span class="badge" :class="it?.committee_required ? 'bg-danger' : 'bg-success'">{{ it?.committee_required? 'نعم':'لا' }}</span>
              </div>
            </div>
            <!-- معلومات جدولة اللجنة (إن وُجدت) -->
            <div v-if="it?.committee_scheduled_at || it?.committee_scheduled_by_name" class="mt-3 small">
              <div class="text-muted">تمت جدولة اللجنة:</div>
              <div>
                <span v-if="it?.committee_scheduled_at">بتاريخ {{ fmtDateTime(it!.committee_scheduled_at) }}</span>
                <span v-if="it?.committee_scheduled_by_name"> · بواسطة {{ it!.committee_scheduled_by_name }}</span>
              </div>
              <div v-if="it?.proposed_summary" class="mt-2">
                <span class="text-muted">الإجراء المقترح من المقرِّرة:</span>
                <div class="fw-semibold">{{ it!.proposed_summary }}</div>
              </div>
              <div class="mt-2 d-flex flex-wrap gap-2">
                <RouterLink class="btn btn-sm btn-outline-secondary" to="/discipline/committee/dashboard">لوحة الرئيس</RouterLink>
                <RouterLink class="btn btn-sm btn-outline-info" to="/discipline/committee/recorder">صفحة المقرّر</RouterLink>
                <RouterLink class="btn btn-sm btn-outline-primary" to="/discipline/committee/member">صفحة العضو</RouterLink>
              </div>
            </div>
          </div>

          <!-- الإجراءات والعقوبات -->
          <div class="card p-3 mt-3">
            <h6 class="mb-2">الإجراءات والعقوبات</h6>
            <div class="small text-muted">إجراءات: {{ it?.actions_count ?? 0 }} — عقوبات: {{ it?.sanctions_count ?? 0 }}</div>
            <ul class="list-group mt-2">
              <li v-for="(a,idx) in (it?.actions_applied||[])" :key="'a'+idx" class="list-group-item">
                <strong>{{ a.name }}</strong>
                <small class="text-muted ms-2">{{ a.at ? fmtDateTime(a.at) : '' }}</small>
                <div class="text-muted">{{ a.notes }}</div>
              </li>
              <li v-for="(s,idx) in (it?.sanctions_applied||[])" :key="'s'+idx" class="list-group-item list-group-item-warning">
                <strong>{{ s.name }}</strong>
                <small class="text-muted ms-2">{{ s.at ? fmtDateTime(s.at) : '' }}</small>
                <div class="text-muted">{{ s.notes }}</div>
              </li>
              <li v-if="!it || ((it.actions_applied||[]).length===0 && (it.sanctions_applied||[]).length===0)" class="list-group-item text-muted">— لا توجد عناصر —</li>
            </ul>

            <div v-if="it && it.status!=='closed'" class="row g-2 mt-3">
              <div class="col-md-5 col-12">
                <input v-model.trim="actionName" type="text" class="form-control" placeholder="إضافة إجراء (الاسم)" />
              </div>
              <div class="col-md-5 col-12">
                <input v-model.trim="actionNotes" type="text" class="form-control" placeholder="ملاحظات" />
              </div>
              <div class="col-md-2 col-12 d-grid">
                <button class="btn btn-outline-primary" :disabled="busy || !actionName" @click="onAddAction">إضافة إجراء</button>
              </div>

              <div class="col-md-5 col-12 mt-2">
                <input v-model.trim="sanctionName" type="text" class="form-control" placeholder="إضافة عقوبة (الاسم)" />
              </div>
              <div class="col-md-5 col-12 mt-2">
                <input v-model.trim="sanctionNotes" type="text" class="form-control" placeholder="ملاحظات" />
              </div>
              <div class="col-md-2 col-12 d-grid mt-2">
                <button class="btn btn-outline-warning" :disabled="busy || !sanctionName" @click="onAddSanction">إضافة عقوبة</button>
              </div>
            </div>
          </div>
        </div>

        <div class="col-lg-4 col-12">
          <div class="card p-3">
            <div class="text-muted small">معلومات إضافية</div>
            <div>المبلغ: {{ it?.reporter_name || '—' }}</div>
            <div class="small mt-2" :class="msgClass" aria-live="polite">{{ msg }}</div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import WingPageHeader from '../../../components/ui/WingPageHeader.vue';
import { tiles } from '../../../home/icon-tiles.config';
import { getIncident, submitIncident, reviewIncident, addIncidentAction, addIncidentSanction, escalateIncident, notifyGuardian, closeIncident } from '../api';
import { openPrintWindowEnhanced, writeAndPrint, blobPrintSameTab } from '../../../shared/print/util';

const route = useRoute();
const id = computed(()=> String(route.params.id || ''));

const tileMeta = computed(()=> ({ title: 'بطاقة الواقعة', subtitle: 'تفاصيل وإجراءات', icon: 'solar:document-bold-duotone', color: '#2e86c1' } as any));

const loading = ref(false);
const busy = ref(false);
const it = ref<any|null>(null);
const msg = ref('');
const msgClass = computed(()=> msg.value.includes('فشل')? 'text-danger':'text-success');
const actionName = ref('');
const actionNotes = ref('');
const sanctionName = ref('');
const sanctionNotes = ref('');

const sevColor = computed(()=> it.value?.level_color || '#2e7d32');
const titleBar = computed(()=> it.value ? `${it.value.violation_display || it.value.violation_code} — ${it.value.student_name || ('#'+it.value.student)}` : 'بطاقة الواقعة');
const subtitleBar = computed(()=> it.value ? `الحالة: ${statusAr(it.value.status)} • الشدة: ${it.value.severity}` : '');

async function reload(){
  loading.value = true; msg.value='';
  try{ it.value = await getIncident(id.value); }catch(e:any){ msg.value = e?.message || 'تعذّر تحميل البيانات'; }
  finally{ loading.value = false; }
}

async function onSubmit(){ await run(async()=> await submitIncident(id.value)); }
async function onReview(){ await run(async()=> await reviewIncident(id.value)); }
async function onEscalate(){ await run(async()=> await escalateIncident(id.value)); }
async function onNotify(){ await run(async()=> await notifyGuardian(id.value, { channel: 'internal' })); }
async function onClose(){ await run(async()=> await closeIncident(id.value)); }
async function onAddAction(){ await run(async()=> await addIncidentAction(id.value, { name: actionName.value, notes: actionNotes.value })); actionName.value=''; actionNotes.value=''; }
async function onAddSanction(){ await run(async()=> await addIncidentSanction(id.value, { name: sanctionName.value, notes: sanctionNotes.value })); sanctionName.value=''; sanctionNotes.value=''; }

function buildPlatformShell(base: string){
  const logo = `${base}/assets/img/logo.png?v=20251027-02`;
  const headLinks = `
  <style>
    @media print { @page { size: A4; margin: 2cm; } }
    body { font-family: 'Cairo','Segoe UI',Tahoma,Arial,sans-serif; color:#111; }
    .content-wrap{ padding: 1rem 0 2rem; }
    .doc-meta{font-size:12px;color:#666}
    .navbar-maronia{ position:fixed; top:0; left:0; right:0; z-index:10; }
    .navbar-maronia nav{ background: linear-gradient(180deg,#8b1e24 0%, #6d141a 45%, #8b1e24 100%); color:#f9d39b; }
    .navbar-maronia .brand-images img{ height:44px; width:auto; display:block }
    .page-footer{ position:fixed; bottom:0; left:0; right:0; }
    .page-footer .container{ background:#7a1f2a; color:#caa86a; }
    .page-main{ margin-top:64px; margin-bottom:56px; }
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
  <header class=\"navbar-maronia\">\n    <nav class=\"container d-flex align-items-center gap-3 py-2\" role=\"navigation\" aria-label=\"التنقل الرئيسي\">\n      <div class=\"brand-images d-flex align-items-center\">\n        <img src=\"${logo}\" alt=\"شعار\" />\n      </div>\n      <span class=\"flex-fill\"></span>\n    </nav>\n  </header>`;
  const footer = `
  <footer class=\"page-footer py-3\">\n    <div class=\"container d-flex justify-content-between small\">\n      <span class=\"text-center w-100\">©2025 - جميع الحقوق محفوظة - مدرسة الشحانية الاعدادية الثانوية بنين - تطوير( المعلم/ سفيان مسيف s.mesyef0904@education.qa )</span>\n    </div>\n  </footer>`;
  return { headLinks, header, footer };
}

// خيار A: طباعة تعهد خطي HTML من الواجهة (نسختان: الطالب وولي الأمر)
async function printPledgeStudent(){
  if(!it.value) return;
  try{
    const data = it.value as any;
    const now = new Date();
    const y = now.getFullYear();
    const m = String(now.getMonth()+1).padStart(2,'0');
    const d = String(now.getDate()).padStart(2,'0');
    const shortId = String(data.id || '').slice(0,8);
    const docId = `PLEDG-${y}${m}-${shortId}`;
    const proposed = data.proposed_summary || '—';
    const studentName = data.student_name || `#${data.student}`;
    const viol = data.violation_display || data.violation_code || '—';
    const occurred = fmtDate(data.occurred_at);
    const base = import.meta.env.VITE_BACKEND_ORIGIN || `https://127.0.0.1:${import.meta.env.VITE_BACKEND_PORT||8443}`;
    const shell = buildPlatformShell(base);
    const html = `<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8" />
  <title>تعهد خطي — ${studentName}</title>
  ${shell.headLinks}
  </head>
  <body>
    <div class="page-container">${shell.header}
    <main class="page-main container content-wrap">
      <h1>تعهد خطي بشأن التزام السلوك المدرسي</h1>
      <div class="row box" style="margin-bottom:12px;">
        <div><div class="muted">الطالب</div><div>${studentName}</div></div>
        <div><div class="muted">رقم الواقعة</div><div>${shortId}</div></div>
        <div><div class="muted">التاريخ</div><div>${occurred}</div></div>
        <div><div class="muted">المخالفة</div><div>${viol}</div></div>
      </div>
      <div class="box">
        <p>أنا الطالب المذكور أعلاه، أقرّ بأنني اطّلعت على الواقعة رقم ${shortId} وأتعهد بالالتزام بقواعد السلوك والانضباط المدرسي، والتعاون مع المدرسة خلال فترة المتابعة.</p>
        <ol>
          <li>الالتزام التام بالقواعد وتجنب تكرار المخالفة.</li>
          <li>التعاون مع الهيئتين التعليمية والإرشادية عند الطلب.</li>
          <li>قبول المتابعة الدورية والامتثال للتوجيهات.</li>
          <li>العلم بأن تكرار المخالفة قد يترتب عليه إجراءات أشد وفق اللوائح.</li>
        </ol>
        <div class="muted">ملخص الإجراء/التوصية (إن وُجد):</div>
        <div style="font-weight:600; margin-bottom:8px;">${proposed}</div>
        <div class="sig-grid">
          <div class="sig"><div class="muted">توقيع الطالب</div><span class="line"></span><div class="muted">الاسم الثلاثي: ____________ · التاريخ: ____/____/______</div></div>
          <div class="sig"><div class="muted">توقيع ولي الأمر</div><span class="line"></span><div class="muted">الاسم: ________________ · الهوية: ____________ · التاريخ: ____/____/______</div></div>
          <div class="sig"><div class="muted">ختم المدرسة / موظف الاستلام</div><span class="line"></span><div class="muted">الاسم: ________________ · التاريخ: ____/____/______</div></div>
        </div>
        <div class="doc-meta">رقم الوثيقة: ${docId} · قالب الطباعة: v1.0 · تاريخ الإصدار: ${y}-${m}-${d}</div>
        <div style="margin-top:8px; display:flex; align-items:center; gap:12px;">
          <div class="qr" aria-label="QR placeholder"></div>
          <div class="muted">سيتم توليد رمز QR في الإصدار القادم (خيار B). حالياً يُستخدم رقم الوثيقة للتحقق الداخلي.</div>
        </div>
      </div>
    </main>${shell.footer}</div>
    <script>window.onload = function(){ setTimeout(function(){ try{ window.focus(); }catch(e){}; if(window.print) window.print(); }, 120); }; window.onafterprint = function(){ setTimeout(function(){ try{ window.close(); }catch(e){} }, 200); };<\/script>
  </body>
</html>`;
    let w = openPrintWindowEnhanced();
    if(!w){
      // مسار احتياطي تلقائي: افتح معاينة الخادم في نفس التبويب بدون حوار
      const base2 = import.meta.env.VITE_BACKEND_ORIGIN || `https://127.0.0.1:${import.meta.env.VITE_BACKEND_PORT||8443}`;
      window.location.assign(`${base2}/api/v1/discipline/incidents/${data.id}/pledge/preview/?format=html`);
      return;
    }
    writeAndPrint(w, html);
    // سجّل أثر الطباعة كإجراء
    await run(async()=> await addIncidentAction(id.value, { name: 'تعهد خطي (طباعة)', notes: 'طُبع التعهد وسُلّم للموقّعين. رقم الوثيقة: '+docId }));
  }catch(e:any){
    msg.value = e?.message || 'فشل في إنشاء التعهد للطباعة';
  }
}

async function printPledgeGuardian(){
  if(!it.value) return;
  try{
    const data = it.value as any;
    const now = new Date();
    const y = now.getFullYear();
    const m = String(now.getMonth()+1).padStart(2,'0');
    const d = String(now.getDate()).padStart(2,'0');
    const shortId = String(data.id || '').slice(0,8);
    const docId = `PLEDG-${y}${m}-${shortId}`;
    const studentName = data.student_name || `#${data.student}`;
    const viol = data.violation_display || data.violation_code || '—';
    const occurred = fmtDate(data.occurred_at);
    const base = import.meta.env.VITE_BACKEND_ORIGIN || `https://127.0.0.1:${import.meta.env.VITE_BACKEND_PORT||8443}`;
    const shell = buildPlatformShell(base);
    const html = `<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8" />
  <title>تعهد ولي الأمر — ${studentName}</title>
  ${shell.headLinks}
  </head>
  <body>
    <div class="page-container">${shell.header}
    <main class="page-main container content-wrap">
      <h1>تعهد ولي الأمر بشأن متابعة السلوك</h1>
      <div class="row box" style="margin-bottom:12px;">
        <div><div class="muted">الطالب</div><div>${studentName}</div></div>
        <div><div class="muted">رقم الواقعة</div><div>${shortId}</div></div>
        <div><div class="muted">التاريخ</div><div>${occurred}</div></div>
        <div><div class="muted">المخالفة</div><div>${viol}</div></div>
      </div>
      <div class="box">
        <p>أنا ولي أمر الطالب المذكور أعلاه، اطّلعت على تفاصيل الواقعة المشار إليها، وأتعهد بالتالي:</p>
        <ol>
          <li>متابعة سلوك ابني والتعاون مع المدرسة.</li>
          <li>حضور الاجتماعات عند الاستدعاء والاستجابة للتواصل.</li>
          <li>إبلاغ المدرسة بأي ظروف قد تؤثر على السلوك.</li>
          <li>تفهم تبعات تكرار المخالفة وفق اللوائح.</li>
        </ol>
        <div class="sig-grid">
          <div class="sig"><div class="muted">توقيع ولي الأمر</div><span class="line"></span><div class="muted">الاسم: ________________ · الهوية: ____________ · التاريخ: ____/____/______</div></div>
          <div class="sig"><div class="muted">بيانات التواصل</div><span class="line"></span><div class="muted">الهاتف: ____________ · البريد: __________________</div></div>
          <div class="sig"><div class="muted">ختم المدرسة / موظف الاستلام</div><span class="line"></span><div class="muted">الاسم: ________________ · التاريخ: ____/____/______</div></div>
        </div>
        <div class="doc-meta">رقم الوثيقة: ${docId} · قالب الطباعة: v1.0 · تاريخ الإصدار: ${y}-${m}-${d}</div>
      </div>
    </main>${shell.footer}</div>
    <script>window.onload = function(){ setTimeout(function(){ try{ window.focus(); }catch(e){}; if(window.print) window.print(); }, 120); }; window.onafterprint = function(){ setTimeout(function(){ try{ window.close(); }catch(e){} }, 200); };<\/script>
  </body>
</html>`;
    let w = openPrintWindowEnhanced();
    if(!w){ blobPrintSameTab(html); return; }
    writeAndPrint(w, html);
    await run(async()=> await addIncidentAction(id.value, { name: 'تعهد ولي الأمر (طباعة)', notes: 'رقم الوثيقة: '+docId }));
  }catch(e:any){ msg.value = e?.message || 'فشل في إنشاء تعهد ولي الأمر للطباعة'; }
}

// خيار A: طباعة «تنبيه شفهي» (نافذة مبكرة + بديل نفس التبويب)
async function printOralWarning(){
  if(!it.value) return;
  try{
    const data = it.value as any;
    const now = new Date();
    const y = now.getFullYear();
    const m = String(now.getMonth()+1).padStart(2,'0');
    const d = String(now.getDate()).padStart(2,'0');
    const shortId = String(data.id || '').slice(0,8);
    const docId = `ORAL-${y}${m}-${shortId}`;
    const studentName = data.student_name || `#${data.student}`;
    const viol = data.violation_display || data.violation_code || '—';
    const occurred = fmtDate(data.occurred_at);
    const base = import.meta.env.VITE_BACKEND_ORIGIN || `https://127.0.0.1:${import.meta.env.VITE_BACKEND_PORT||8443}`;
    const shell = buildPlatformShell(base);
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
        </div>
        <div class="box">
          <p>تم توجيه <strong>تنبيه شفهي</strong> للطالب/ـة المذكور أعلاه بخصوص الواقعة المشار إليها، مع التأكيد على الالتزام بقواعد السلوك والانضباط وعدم تكرار المخالفة.</p>
          <ul>
            <li>فهم أثر المخالفة على البيئة التعليمية.</li>
            <li>التعهّد بالالتزام مستقبلاً والتعاون مع المعنيين.</li>
          </ul>
          <div class="muted">ملاحظات المبلّغ/المراجع (اختياري): _______________________________</div>
          <div class="sig"><div class="muted">توقيع الموظف</div></div>
        </div>
      </main>
      ${shell.footer}
    </div>
    <script>window.onload = function(){ setTimeout(function(){ try{ window.focus(); }catch(e){}; if(window.print) window.print(); }, 120); }; window.onafterprint = function(){ setTimeout(function(){ try{ window.close(); }catch(e){} }, 200); };<\/script>
  </body>
</html>`;
    let w = openPrintWindowEnhanced();
    if(!w){
      // مسار بديل: الطباعة في نفس التبويب
      blobPrintSameTab(html);
      return;
    }
    writeAndPrint(w, html);
    await run(async()=> await addIncidentAction(id.value, { name: 'تنبيه شفهي (طباعة)', notes: 'رقم الوثيقة: '+docId }));
  }catch(e:any){ msg.value = e?.message || 'فشل في إنشاء تنبيه شفهي للطباعة'; }
}

// خيار A: طباعة ملخّص «إجراءات اللجنة» (نافذة مبكرة + بديل نفس التبويب)
async function printCommitteeActions(){
  if(!it.value) return;
  try{
    const data = it.value as any;
    const now = new Date();
    const y = now.getFullYear();
    const m = String(now.getMonth()+1).padStart(2,'0');
    const d = String(now.getDate()).padStart(2,'0');
    const shortId = String(data.id || '').slice(0,8);
    const docId = `ACTS-${y}${m}-${shortId}`;
    const studentName = data.student_name || `#${data.student}`;
    const items: any[] = Array.isArray(data.actions_applied)? data.actions_applied : [];
    const rows = items.map((a,idx)=> `<tr><td>${idx+1}</td><td>${(a?.name||'').toString()}</td><td>${(a?.notes||'').toString()}</td><td>${a?.at? new Date(a.at).toLocaleString(): ''}</td></tr>`).join('');
    const base = import.meta.env.VITE_BACKEND_ORIGIN || `https://127.0.0.1:${import.meta.env.VITE_BACKEND_PORT||8443}`;
    const shell = buildPlatformShell(base);
    const html = `<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8" />
  <title>إجراءات اللجنة — ${studentName}</title>
  ${shell.headLinks}
  </head>
  <body>
    <div class="page-container">${shell.header}
      <main class="page-main container content-wrap">
        <h1>إجراءات اللجنة المعتمدة/المقترحة</h1>
        <div class="box" style="margin-bottom:8px; color:#555;">الطالب: <strong>${studentName}</strong> · الواقعة: ${shortId}</div>
        <table>
          <thead><tr><th>#</th><th>الإجراء</th><th>ملاحظات</th><th>التاريخ/الوقت</th></tr></thead>
          <tbody>${rows || '<tr><td colspan="4" style="text-align:center; color:#888;">— لا توجد إجراءات —</td></tr>'}</tbody>
        </table>
      </main>
      ${shell.footer}
    </div>
    <script>window.onload = function(){ setTimeout(function(){ try{ window.focus(); }catch(e){}; if(window.print) window.print(); }, 120); }; window.onafterprint = function(){ setTimeout(function(){ try{ window.close(); }catch(e){} }, 200); };<\/script>
  </body>
</html>`;
    let w = openPrintWindowEnhanced();
    if(!w){ blobPrintSameTab(html); return; }
    writeAndPrint(w, html);
    await run(async()=> await addIncidentAction(id.value, { name: 'إجراءات اللجنة (طباعة)', notes: 'رقم الوثيقة: '+docId }));
  }catch(e:any){ msg.value = e?.message || 'فشل في إنشاء طباعة إجراءات اللجنة'; }
}

// خيار A: طباعة ملخّص «عقوبات اللجنة» (نافذة مبكرة + بديل نفس التبويب)
async function printCommitteeSanctions(){
  if(!it.value) return;
  try{
    const data = it.value as any;
    const now = new Date();
    const y = now.getFullYear();
    const m = String(now.getMonth()+1).padStart(2,'0');
    const d = String(now.getDate()).padStart(2,'0');
    const shortId = String(data.id || '').slice(0,8);
    const docId = `SANC-${y}${m}-${shortId}`;
    const studentName = data.student_name || `#${data.student}`;
    const items: any[] = Array.isArray(data.sanctions_applied)? data.sanctions_applied : [];
    const rows = items.map((a,idx)=> `<tr><td>${idx+1}</td><td>${(a?.name||'').toString()}</td><td>${(a?.notes||'').toString()}</td><td>${a?.at? new Date(a.at).toLocaleString(): ''}</td></tr>`).join('');
    const base = import.meta.env.VITE_BACKEND_ORIGIN || `https://127.0.0.1:${import.meta.env.VITE_BACKEND_PORT||8443}`;
    const shell = buildPlatformShell(base);
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
        <div class="box" style="margin-bottom:8px; color:#555;">الطالب: <strong>${studentName}</strong> · الواقعة: ${shortId}</div>
        <table>
          <thead><tr><th>#</th><th>العقوبة</th><th>ملاحظات</th><th>التاريخ/الوقت</th></tr></thead>
          <tbody>${rows || '<tr><td colspan="4" style="text-align:center; color:#888;">— لا توجد عقوبات —</td></tr>'}</tbody>
        </table>
      </main>
      ${shell.footer}
    </div>
    <script>window.onload = function(){ setTimeout(function(){ try{ window.focus(); }catch(e){}; if(window.print) window.print(); }, 120); }; window.onafterprint = function(){ setTimeout(function(){ try{ window.close(); }catch(e){} }, 200); };<\/script>
  </body>
</html>`;
    let w = openPrintWindowEnhanced();
    if(!w){ blobPrintSameTab(html); return; }
    writeAndPrint(w, html);
    await run(async()=> await addIncidentAction(id.value, { name: 'عقوبات اللجنة (طباعة)', notes: 'رقم الوثيقة: '+docId }));
  }catch(e:any){ msg.value = e?.message || 'فشل في إنشاء طباعة عقوبات اللجنة'; }
}

async function run(fn: ()=>Promise<any>){
  try{ busy.value = true; await fn(); await reload(); msg.value='تم التنفيذ'; }
  catch(e:any){ msg.value = e?.response?.data?.detail || e?.message || 'فشل التنفيذ'; }
  finally{ busy.value = false; }
}

function fmtDate(s?: string){ if(!s) return '—'; try{ const d=new Date(s); const y=d.getFullYear(); const m=String(d.getMonth()+1).padStart(2,'0'); const dd=String(d.getDate()).padStart(2,'0'); return `${y}-${m}-${dd}`; }catch{ return s as string; } }
function fmtDateTime(s?: string){ if(!s) return '—'; try{ const d=new Date(s); return d.toLocaleString(); }catch{ return s as string; } }
function badgeFor(st?: string){ return st==='closed'?'bg-secondary':(st==='under_review'?'bg-warning text-dark':'bg-info'); }
function statusAr(st?: string){ if(!st) return '—'; return st==='closed'?'مغلقة':(st==='under_review'?'قيد المراجعة':'مسودة'); }

onMounted(reload);
</script>
<style scoped>
.page-stack{ display:grid; gap:16px; }
.prewrap{ white-space: pre-wrap; }
</style>
