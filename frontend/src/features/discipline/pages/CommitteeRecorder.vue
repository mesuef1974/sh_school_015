<template>
  <section class="d-grid gap-9 committee-page" dir="rtl">
    <!-- شريط عنوان الصفحة -->
    <WingPageHeader icon="solar:document-text-bold-duotone" title="صفحة مقرر لجنة السلوك" :subtitle="'متابعة محاضر اللجنة وطباعة النماذج'">
      <template #actions>
        <div class="d-flex align-items-center gap-2 flex-wrap">
          <RouterLink class="btn btn-sm btn-outline-secondary" to="/discipline/committee/dashboard">لوحة الرئيس</RouterLink>
          <RouterLink class="btn btn-sm btn-outline-info" to="/discipline/committee/member">لوحة العضو</RouterLink>
        </div>
      </template>
    </WingPageHeader>

    <div v-if="loading" class="alert alert-info py-2">جاري التحميل ...</div>
    <div v-else-if="error" class="alert alert-warning py-2">{{ error }}</div>

    <div v-else>
      <div v-if="caps" class="alert alert-secondary py-2 d-flex flex-wrap gap-2 align-items-center">
        <span class="fw-semibold">صلاحياتي:</span>
        <span v-if="caps.can_view" class="badge bg-primary-subtle text-primary">عرض مسار اللجنة</span>
        <span v-if="caps.is_standing_recorder" class="badge bg-info text-dark">مقرر اللجنة الدائمة</span>
      </div>

      <div class="card mt-3">
        <div class="card-header">وقائع تحتاج متابعة/طباعة بواسطة المقرّر</div>
        <ul class="list-group list-group-flush">
          <li v-for="it in items" :key="it.id" class="list-group-item">
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
            </div>
            <div class="mt-2 small d-flex flex-wrap align-items-center gap-2 text-muted">
              <span v-if="it.occurred_at">{{ new Date(it.occurred_at).toLocaleDateString('ar-QA') }} {{ it.occurred_time || '' }}</span>
              <span v-if="it.location"> · المكان: {{ it.location }}</span>
            </div>
            <div class="mt-2 d-flex flex-wrap gap-2">
              <RouterLink class="btn btn-sm btn-outline-dark" :to="{ name: 'discipline-incident-print', params: { id: it.id } }">مركز الطباعة</RouterLink>
            </div>
          </li>
          <li v-if="items.length===0" class="list-group-item">
            <div class="d-flex align-items-center">
              <span class="text-muted">لا توجد وقائع تحتاج متابعة من المقرّر حاليًا.</span>
              <RouterLink class="btn btn-sm btn-link ms-auto" to="/discipline/committee/dashboard">اذهب إلى لوحة الرئيس</RouterLink>
            </div>
          </li>
        </ul>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import WingPageHeader from '../../../components/ui/WingPageHeader.vue';
import { getMyCommittee, getCommitteeCaps, getIncident, addIncidentAction } from '../../discipline/api';

const loading = ref(false);
const error = ref('');
const items = ref<any[]>([]);
const caps = ref<any>(null);

function sevClass(sev?: number){
  const s = Number(sev||1);
  return s>=4? 'bg-danger': s===3? 'bg-warning text-dark': s===2? 'bg-info text-dark': 'bg-success';
}

async function reload(){
  loading.value = true; error.value='';
  try{
    try { const c = await getCommitteeCaps(); caps.value = c?.access_caps || null; } catch {}
    // لغياب Endpoint مخصص للمقرّر، نستخدم «وقائع لعضو اللجنة» كقائمة عمل للمقرّر أيضًا
    items.value = await getMyCommittee();
  }catch(e:any){
    error.value = e?.message || 'تعذّر تحميل البيانات';
  }finally{
    loading.value = false;
  }
}

onMounted(()=> reload());

// ======================= وظائف الطباعة (HTML — خيار A) =======================
// أداة موحّدة لفتح نافذة الطباعة مع مسارات بديلة عند الحجب
function openPrintWindowEnhanced(): Window|null {
  let w: Window|null = null;
  try { w = window.open('about:blank', '_blank', 'noopener,noreferrer'); } catch {}
  if (w) {
    try { (w as any).opener = null; w.focus(); } catch {}
    try {
      w.document.open();
      w.document.write('<!doctype html><title>جاري التحضير للطباعة…</title><body dir="rtl" style="font-family:Segoe UI,Tahoma,Arial,sans-serif; padding:16px; color:#444;">جاري التحضير للطباعة…</body>');
      w.document.close();
    } catch {}
    return w;
  }
  // بديل باستخدام رابط غير مرئي — قد يفتح تبويبًا دون مرجع
  try {
    const a = document.createElement('a');
    a.href = 'about:blank';
    a.target = '_blank';
    a.rel = 'noopener';
    a.style.display = 'none';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  } catch {}
  return null;
}
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
    /* Utilities used by documents */
    .row{ display:grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 8px 16px; }
    .box{ border:1px solid #ccc; padding:12px; border-radius:6px; }
    .muted{ color:#666; font-size:12px; }
    .sig-grid{ display:grid; grid-template-columns: repeat(3,1fr); gap:12px; margin-top:16px; }
    .sig{ border:1px dashed #999; min-height:72px; padding:8px; }
    .sig .line{ display:block; margin-top:6px; border-top:1px solid #bbb; height:0; }
    .qr{ width:96px; height:96px; border:1px solid #ccc; display:inline-block; background: repeating-linear-gradient(45deg,#eee 0,#eee 8px,#ddd 8px,#ddd 16px); }
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
  let w = openPrintWindowEnhanced();
  if(!w){
    // فتح المعاينة الخادمية مباشرة في نفس التبويب بدون أسئلة أو تنبيهات
    const base = import.meta.env.VITE_BACKEND_ORIGIN || `https://127.0.0.1:${import.meta.env.VITE_BACKEND_PORT||8443}`;
    window.location.assign(`${base}/api/v1/discipline/incidents/${incidentId}/pledge/preview/?format=html`);
    return;
  }
  try{
    try { (w as any).opener = null; w.focus(); } catch {}

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
<html lang=\"ar\" dir=\"rtl\">
<head>
  <meta charset=\"utf-8\" />
  <title>تعهد ولي الأمر — ${studentName}</title>
  ${shell.headLinks}
</head>
<body>
  <div class=\"page-container\">${shell.header}
    <main class=\"page-main container content-wrap\">
      <h1>تعهد ولي الأمر بشأن متابعة السلوك</h1>
      <div class=\"row box\" style=\"margin-bottom:12px;\">
        <div><div class=\"muted\">الطالب</div><div>${studentName}</div></div>
        <div><div class=\"muted\">رقم الواقعة</div><div>${shortId}</div></div>
        <div><div class=\"muted\">التاريخ</div><div>${occurred}</div></div>
        <div><div class=\"muted\">المخالفة</div><div>${viol}</div></div>
        <div><div class=\"muted\">المكان</div><div>${location}</div></div>
        <div><div class=\"muted\">الشدة</div><div>${severity}</div></div>
      </div>
      <div class=\"box\">
        <p>أنا ولي أمر الطالب المذكور أعلاه، اطّلعت على تفاصيل الواقعة المشار إليها، وأتعهد بالتالي:</p>
        <ol>
          <li>متابعة السلوك والتعاون مع المدرسة في أي خطة علاجية أو إرشادية.</li>
          <li>حضور الاجتماعات عند الاستدعاء والاستجابة للتواصل.</li>
          <li>إبلاغ المدرسة بأي ظروف قد تؤثر على السلوك.</li>
          <li>تفهم تبعات تكرار المخالفة وفق اللوائح.</li>
        </ol>
        <div class=\"sig-grid\">
          <div class=\"sig\"><div class=\"muted\">توقيع ولي الأمر</div><span class=\"line\"></span><div class=\"muted\">الاسم: ________________ · الهوية: ____________ · التاريخ: ____/____/______</div></div>
          <div class=\"sig\"><div class=\"muted\">بيانات التواصل</div><span class=\"line\"></span><div class=\"muted\">الهاتف: ____________ · البريد: __________________</div></div>
          <div class=\"sig\"><div class=\"muted\">ختم المدرسة / موظف الاستلام</div><span class=\"line\"></span><div class=\"muted\">الاسم: ________________ · التاريخ: ____/____/______</div></div>
        </div>
        <div class=\"doc-meta\">رقم الوثيقة: ${docId} · قالب الطباعة: v1.0 · تاريخ الإصدار: ${y}-${m}-${d}</div>
      </div>
    </main>
    ${shell.footer}
  </div>
  <script>window.onload = function(){ setTimeout(function(){ try{ window.focus(); }catch(e){}; if (window.print) window.print(); }, 120); }; window.onafterprint = function(){ setTimeout(function(){ try{ window.close(); }catch(e){} }, 200); };<\/script>
</body>
</html>`;
  if(!w){ const blob = new Blob([guardianHtml], { type: 'text/html;charset=utf-8' }); const url = URL.createObjectURL(blob); window.location.assign(url); return; }
  try{ w.document.open(); w.document.write(guardianHtml); w.document.close(); try{ await addIncidentAction(incidentId, { name: 'تعهد ولي الأمر (طباعة)', notes: 'رقم الوثيقة: '+docId }); }catch{} }
  catch(e:any){ try{ w.close(); }catch{}; alert(e?.message || 'فشل في طباعة تعهد ولي الأمر'); }
}

async function printOralById(incidentId: string){
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
    <div class="page-container">
      ${shell.header}
      <main class="page-main container content-wrap">
        <h1>تنبيه شفهي للطالب</h1>
        <div class="row box" style="margin-bottom:12px;">
          <div><div class="muted">الطالب</div><div>${studentName}</div></div>
          <div><div class="muted">رقم الواقعة</div><div>${shortId}</div></div>
          <div><div class="muted">التاريخ</div><div>${occurred}</div></div>
          <div><div class="muted">المخالفة</div><div>${viol}</div></div>
          <div><div class="muted">المكان</div><div>${location}</div></div>
        </div>
        <div class="box">
          <p>
            تم توجيه <strong>تنبيه شفهي</strong> للطالب المذكور أعلاه بخصوص الواقعة المشار إليها،
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
    try { (w as any).opener = null; w.focus(); } catch {}

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
<html lang=\"ar\" dir=\"rtl\">
<head>
  <meta charset=\"utf-8\" />
  <title>إجراءات اللجنة — ${studentName}</title>
  ${shell.headLinks}
  </head>
  <body>
    <div class=\"page-container\">${shell.header}
      <main class=\"page-main container content-wrap\">
        <h1>إجراءات اللجنة المعتمدة/المقترحة</h1>
        <div class=\"box\" style=\"margin-bottom:8px; color:#555;\">
          <div class=\"row\">
            <div><div class=\"muted\">الطالب</div><div><strong>${studentName}</strong></div></div>
            <div><div class=\"muted\">رقم الواقعة</div><div>${shortId}</div></div>
            <div><div class=\"muted\">التاريخ</div><div>${occurred}</div></div>
            <div><div class=\"muted\">المخالفة</div><div>${viol}</div></div>
            <div><div class=\"muted\">المكان</div><div>${location}</div></div>
            <div><div class=\"muted\">الشدة</div><div>${severity}</div></div>
          </div>
          <div class=\"muted\" style=\"margin-top:6px;\">الإجراء/التوصية المختصرة: <span style=\"font-weight:600; color:#222;\">${proposed}</span></div>
        </div>
        <table>
          <thead><tr><th>#</th><th>الإجراء</th><th>ملاحظات</th><th>التاريخ/الوقت</th></tr></thead>
          <tbody>${rows || '<tr><td colspan=\"4\" style=\"text-align:center; color:#888;\">— لا توجد إجراءات —</td></tr>'}</tbody>
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
    try { (w as any).opener = null; w.focus(); } catch {}

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
      const items: any[] = Array.isArray(data.sanctions_applied)? data.sanctions_applied : [];
      const rows = items.map((a:any,idx:number)=> `<tr><td>${idx+1}</td><td>${(a?.name||'').toString()}</td><td>${(a?.notes||'').toString()}</td><td>${a?.at? new Date(a.at).toLocaleString(): ''}</td></tr>`).join('');
      const html = `<!DOCTYPE html>
<html lang=\"ar\" dir=\"rtl\">
<head>
  <meta charset=\"utf-8\" />
  <title>عقوبات اللجنة — ${studentName}</title>
  ${shell.headLinks}
  </head>
  <body>
    <div class=\"page-container\">${shell.header}
      <main class=\"page-main container content-wrap\">
        <h1>عقوبات اللجنة المعتمدة/المقترحة</h1>
        <div class=\"box\" style=\"margin-bottom:8px; color:#555;\">الطالب: <strong>${studentName}</strong> · الواقعة: ${shortId}</div>
        <table>
          <thead><tr><th>#</th><th>العقوبة</th><th>ملاحظات</th><th>التاريخ/الوقت</th></tr></thead>
          <tbody>${rows || '<tr><td colspan=\"4\" style=\"text-align:center; color:#888;\">— لا توجد عقوبات —</td></tr>'}</tbody>
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
    try { (w as any).opener = null; w.focus(); } catch {}

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

// أداة محلية لتنسيق التاريخ
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
.list-group-item { padding-top: .9rem; padding-bottom: .9rem; }
</style>
