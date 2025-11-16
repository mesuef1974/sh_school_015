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
            <!-- مفاتيح الطباعة المهنية (HTML — خيار A) -->
            <div class="mt-2 d-flex flex-wrap gap-2">
              <button class="btn btn-sm btn-outline-dark" @click="printPledgeById(it.id)">طباعة التعهد</button>
              <button class="btn btn-sm btn-outline-primary" @click="printActsById(it.id)">طباعة إجراءات اللجنة</button>
              <button class="btn btn-sm btn-outline-warning" @click="printSancById(it.id)">طباعة عقوبات اللجنة</button>
              <button class="btn btn-sm btn-outline-secondary" @click="printOralById(it.id)" :disabled="Number(it.severity||0) > 1" title="يُتاح للوقائع البسيطة (مستوى 1)">تنبيه شفهي</button>
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
async function printPledgeById(incidentId: string){
  try{
    const data:any = await getIncident(incidentId);
    const now = new Date(); const y = now.getFullYear(); const m = String(now.getMonth()+1).padStart(2,'0'); const d = String(now.getDate()).padStart(2,'0');
    const shortId = String(data.id || '').slice(0,8);
    const docId = `PLEDG-${y}${m}-${shortId}`;
    const proposed = data.proposed_summary || '—';
    const studentName = data.student_name || `#${data.student}`;
    const viol = data.violation_display || data.violation_code || '—';
    const occurred = fmtDate(data.occurred_at);
    const html = `<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8" />
  <title>تعهد خطي — ${studentName}</title>
  <style>
    :root{ --fg:#111; --muted:#666; --accent:#0d6efd; }
    body{ font-family: 'Segoe UI', Tahoma, Arial, sans-serif; color:var(--fg); margin:0; }
    header, footer{ position: fixed; left: 0; right: 0; }
    header{ top: 0; padding: 12px 24px; border-bottom: 1px solid #ddd; }
    footer{ bottom: 0; padding: 8px 24px; border-top: 1px solid #ddd; color: var(--muted); font-size: 11px; }
    main{ padding: 120px 24px 80px; max-width: 820px; margin: 0 auto; }
    h1{ font-size: 18px; margin: 0 0 12px; }
    .row{ display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 8px 16px; }
    .box{ border: 1px solid #ccc; padding: 12px; border-radius: 6px; }
    .muted{ color: var(--muted); font-size: 12px; }
    .sig-grid{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-top: 16px; }
    .sig{ border: 1px dashed #999; min-height: 72px; padding: 8px; }
    .qr{ width: 96px; height: 96px; border: 1px solid #ccc; display: inline-block; background:
      repeating-linear-gradient(45deg,#eee 0,#eee 8px,#ddd 8px,#ddd 16px); }
    .meta{ margin-top: 10px; font-size: 12px; color: var(--muted); }
    @media print { @page { size: A4; margin: 2cm; } header, footer { position: fixed; } main{ padding: 0; margin-top: 40px; } .no-print{ display: none !important; } }
  </style>
  </head>
  <body>
    <header>
      <div style="display:flex; align-items:center; gap:12px;">
        <div style="font-weight:700;">نظام السلوك المدرسي</div>
        <div class="muted" style="margin-inline-start:auto">رقم الوثيقة: ${docId} · تاريخ الإصدار: ${y}-${m}-${d}</div>
      </div>
    </header>
    <footer>سري — للاستخدام المدرسي · صفحة 1 من 1 · للتحقق امسح رمز QR</footer>
    <main>
      <h1>تعهد خطي بشأن التزام السلوك المدرسي</h1>
      <div class="row box" style="margin-bottom:12px;">
        <div><div class="muted">الطالب</div><div>${studentName}</div></div>
        <div><div class="muted">رقم الواقعة</div><div>${shortId}</div></div>
        <div><div class="muted">التاريخ</div><div>${occurred}</div></div>
        <div><div class="muted">المخالفة</div><div>${viol}</div></div>
      </div>
      <div class="box">
        <p>أنا الطالب/ـة المذكور أعلاه، أقرّ بأنني اطّلعت على الواقعة رقم ${shortId} وأتعهد بالالتزام بقواعد السلوك والانضباط المدرسي، والتعاون مع المدرسة خلال فترة المتابعة.</p>
        <ol>
          <li>الالتزام التام بالقواعد وتجنب تكرار المخالفة.</li>
          <li>التعاون مع الهيئتين التعليمية والإرشادية عند الطلب.</li>
          <li>قبول المتابعة الدورية والامتثال للتوجيهات.</li>
          <li>العلم بأن تكرار المخالفة قد يترتب عليه إجراءات أشد وفق اللوائح.</li>
        </ol>
        <div class="muted">ملخص الإجراء/التوصية (إن وُجد):</div>
        <div style="font-weight:600; margin-bottom:8px;">${proposed}</div>
        <div class="sig-grid">
          <div class="sig"><div class="muted">توقيع الطالب/ـة</div></div>
          <div class="sig"><div class="muted">توقيع ولي الأمر</div></div>
          <div class="sig"><div class="muted">ختم المدرسة / موظف الاستلام</div></div>
        </div>
        <div class="meta">رقم الوثيقة: ${docId}</div>
        <div style="margin-top:8px; display:flex; align-items:center; gap:12px;">
          <div class="qr" aria-label="QR placeholder"></div>
          <div class="muted">سيتم توليد رمز QR في الإصدار القادم (خيار B). حالياً يُستخدم رقم الوثيقة للتحقق الداخلي.</div>
        </div>
      </div>
    </main>
    <script>window.onload = function(){ setTimeout(function(){ window.print(); }, 50); };<\/script>
  </body>
</html>`;
    const w = window.open('', '_blank', 'noopener,noreferrer'); if(!w) throw new Error('تعذّر فتح نافذة الطباعة.');
    w.document.open(); w.document.write(html); w.document.close();
    try { await addIncidentAction(incidentId, { name: 'تعهد خطي (طباعة)', notes: 'رقم الوثيقة: '+docId }); } catch {}
  }catch(e:any){ alert(e?.message || 'فشل في طباعة التعهد'); }
}

async function printOralById(incidentId: string){
  try{
    const data:any = await getIncident(incidentId);
    if (Number(data.severity||0) > 1) { alert('التنبيه الشفهي مخصص للوقائع البسيطة (مستوى 1)'); return; }
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
  <style>
    :root{ --fg:#111; --muted:#666; }
    body{ font-family: 'Segoe UI', Tahoma, Arial, sans-serif; color:var(--fg); margin:0; }
    header, footer{ position: fixed; left: 0; right: 0; }
    header{ top: 0; padding: 12px 24px; border-bottom: 1px solid #ddd; }
    footer{ bottom: 0; padding: 8px 24px; border-top: 1px solid #ddd; color: var(--muted); font-size: 11px; }
    main{ padding: 100px 24px 80px; max-width: 820px; margin: 0 auto; }
    h1{ font-size: 18px; margin: 0 0 12px; }
    .row{ display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 8px 16px; }
    .box{ border: 1px solid #ccc; padding: 12px; border-radius: 6px; }
    .muted{ color: var(--muted); font-size: 12px; }
    .sig{ border: 1px dashed #999; min-height: 64px; padding: 8px; margin-top: 12px; }
    @media print { @page { size: A4; margin: 2cm; } header, footer { position: fixed; } main{ padding: 0; margin-top: 40px; } }
  </style>
  </head>
  <body>
    <header>
      <div style="display:flex; align-items:center; gap:12px;">
        <div style="font-weight:700;">نظام السلوك المدرسي</div>
        <div class="muted" style="margin-inline-start:auto">رقم الوثيقة: ${docId} · تاريخ الإصدار: ${y}-${m}-${d}</div>
      </div>
    </header>
    <footer>سري — للاستخدام المدرسي · صفحة 1 من 1</footer>
    <main>
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
    <script>window.onload = function(){ setTimeout(function(){ window.print(); }, 50); };<\/script>
  </body>
</html>`;
    const w = window.open('', '_blank', 'noopener,noreferrer'); if(!w) throw new Error('تعذّر فتح نافذة الطباعة.');
    w.document.open(); w.document.write(html); w.document.close();
    try { await addIncidentAction(incidentId, { name: 'تنبيه شفهي (طباعة)', notes: 'رقم الوثيقة: '+docId }); } catch {}
  }catch(e:any){ alert(e?.message || 'فشل في طباعة التنبيه الشفهي'); }
}

async function printActsById(incidentId: string){
  try{
    const data:any = await getIncident(incidentId);
    const now = new Date(); const y = now.getFullYear(); const m = String(now.getMonth()+1).padStart(2,'0'); const d = String(now.getDate()).padStart(2,'0');
    const shortId = String(data.id || '').slice(0,8);
    const docId = `ACTS-${y}${m}-${shortId}`;
    const studentName = data.student_name || `#${data.student}`;
    const items: any[] = Array.isArray(data.actions_applied)? data.actions_applied : [];
    const rows = items.map((a:any,idx:number)=> `<tr><td>${idx+1}</td><td>${(a?.name||'').toString()}</td><td>${(a?.notes||'').toString()}</td><td>${a?.at? new Date(a.at).toLocaleString(): ''}</td></tr>`).join('');
    const html = `<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8" />
  <title>إجراءات اللجنة — ${studentName}</title>
  <style>
    body{ font-family: 'Segoe UI', Tahoma, Arial, sans-serif; margin:0; }
    header, footer{ position: fixed; left:0; right:0; }
    header{ top:0; padding:12px 24px; border-bottom:1px solid #ddd; }
    footer{ bottom:0; padding:8px 24px; border-top:1px solid #ddd; color:#666; font-size:11px; }
    main{ padding: 90px 24px 70px; max-width: 900px; margin:0 auto; }
    table{ width:100%; border-collapse: collapse; }
    th,td{ border:1px solid #ccc; padding:6px 8px; font-size: 13px; }
    th{ background:#f8f9fa; }
    h1{ font-size: 18px; margin: 0 0 10px; }
    @media print{ @page{ size:A4; margin:2cm; } header,footer{ position: fixed; } }
  </style>
  </head>
  <body>
    <header>
      <div style="display:flex; align-items:center; gap:12px;">
        <div style="font-weight:700;">نظام السلوك المدرسي</div>
        <div style="margin-inline-start:auto; color:#666;">رقم الوثيقة: ${docId} · تاريخ الإصدار: ${y}-${m}-${d}</div>
      </div>
    </header>
    <footer>سري — للاستخدام المدرسي</footer>
    <main>
      <h1>إجراءات اللجنة المعتمدة/المقترحة</h1>
      <div style="margin-bottom:8px; color:#555;">الطالب: <strong>${studentName}</strong> · الواقعة: ${shortId}</div>
      <table>
        <thead><tr><th>#</th><th>الإجراء</th><th>ملاحظات</th><th>التاريخ/الوقت</th></tr></thead>
        <tbody>${rows || '<tr><td colspan="4" style="text-align:center; color:#888;">— لا توجد إجراءات —</td></tr>'}</tbody>
      </table>
    </main>
    <script>window.onload = function(){ setTimeout(function(){ window.print(); }, 50); };<\/script>
  </body>
</html>`;
    const w = window.open('', '_blank', 'noopener,noreferrer'); if(!w) throw new Error('تعذّر فتح نافذة الطباعة.');
    w.document.open(); w.document.write(html); w.document.close();
    try { await addIncidentAction(incidentId, { name: 'إجراءات اللجنة (طباعة)', notes: 'رقم الوثيقة: '+docId }); } catch {}
  }catch(e:any){ alert(e?.message || 'فشل في طباعة إجراءات اللجنة'); }
}

async function printSancById(incidentId: string){
  try{
    const data:any = await getIncident(incidentId);
    const now = new Date(); const y = now.getFullYear(); const m = String(now.getMonth()+1).padStart(2,'0'); const d = String(now.getDate()).padStart(2,'0');
    const shortId = String(data.id || '').slice(0,8);
    const docId = `SANC-${y}${m}-${shortId}`;
    const studentName = data.student_name || `#${data.student}`;
    const items: any[] = Array.isArray(data.sanctions_applied)? data.sanctions_applied : [];
    const rows = items.map((a:any,idx:number)=> `<tr><td>${idx+1}</td><td>${(a?.name||'').toString()}</td><td>${(a?.notes||'').toString()}</td><td>${a?.at? new Date(a.at).toLocaleString(): ''}</td></tr>`).join('');
    const html = `<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8" />
  <title>عقوبات اللجنة — ${studentName}</title>
  <style>
    body{ font-family: 'Segoe UI', Tahoma, Arial, sans-serif; margin:0; }
    header, footer{ position: fixed; left:0; right:0; }
    header{ top:0; padding:12px 24px; border-bottom:1px solid #ddd; }
    footer{ bottom:0; padding:8px 24px; border-top:1px solid #ddd; color:#666; font-size:11px; }
    main{ padding: 90px 24px 70px; max-width: 900px; margin:0 auto; }
    table{ width:100%; border-collapse: collapse; }
    th,td{ border:1px solid #ccc; padding:6px 8px; font-size: 13px; }
    th{ background:#f8f9fa; }
    h1{ font-size: 18px; margin: 0 0 10px; }
    @media print{ @page{ size:A4; margin:2cm; } header,footer{ position: fixed; } }
  </style>
  </head>
  <body>
    <header>
      <div style="display:flex; align-items:center; gap:12px;">
        <div style="font-weight:700;">نظام السلوك المدرسي</div>
        <div style="margin-inline-start:auto; color:#666;">رقم الوثيقة: ${docId} · تاريخ الإصدار: ${y}-${m}-${d}</div>
      </div>
    </header>
    <footer>سري — للاستخدام المدرسي</footer>
    <main>
      <h1>عقوبات اللجنة المعتمدة/المقترحة</h1>
      <div style="margin-bottom:8px; color:#555;">الطالب: <strong>${studentName}</strong> · الواقعة: ${shortId}</div>
      <table>
        <thead><tr><th>#</th><th>العقوبة</th><th>ملاحظات</th><th>التاريخ/الوقت</th></tr></thead>
        <tbody>${rows || '<tr><td colspan="4" style="text-align:center; color:#888;">— لا توجد عقوبات —</td></tr>'}</tbody>
      </table>
    </main>
    <script>window.onload = function(){ setTimeout(function(){ window.print(); }, 50); };<\/script>
  </body>
</html>`;
    const w = window.open('', '_blank', 'noopener,noreferrer'); if(!w) throw new Error('تعذّر فتح نافذة الطباعة.');
    w.document.open(); w.document.write(html); w.document.close();
    try { await addIncidentAction(incidentId, { name: 'عقوبات اللجنة (طباعة)', notes: 'رقم الوثيقة: '+docId }); } catch {}
  }catch(e:any){ alert(e?.message || 'فشل في طباعة عقوبات اللجنة'); }
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
