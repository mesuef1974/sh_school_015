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
            <!-- طباعة تنبيه شفهي (لمسجّل الواقعة؛ نظهره عامة عند الشدة 1 طالما غير مغلقة) -->
            <button v-if="it && it.status!=='closed' && Number(it.severity||0) <= 1" class="btn btn-outline-dark" :disabled="busy || loading" @click="printOralWarning">طباعة تنبيه شفهي</button>
            <button v-if="it && it.status!=='closed'" class="btn btn-outline-dark" :disabled="busy || loading" @click="printPledge">طباعة التعهد</button>
            <!-- طباعة إجراءات/عقوبات اللجنة عند وجود عناصر -->
            <button
              v-if="it && it.status!=='closed' && it.committee_required && (Array.isArray(it.actions_applied) ? it.actions_applied.length>0 : false)"
              class="btn btn-outline-primary"
              :disabled="busy || loading"
              @click="printCommitteeActions"
            >طباعة إجراءات اللجنة</button>
            <button
              v-if="it && it.status!=='closed' && it.committee_required && (Array.isArray(it.sanctions_applied) ? it.sanctions_applied.length>0 : false)"
              class="btn btn-outline-warning"
              :disabled="busy || loading"
              @click="printCommitteeSanctions"
            >طباعة عقوبات اللجنة</button>
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

// خيار A: طباعة تعهد خطي HTML من الواجهة
async function printPledge(){
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
    @media print {
      @page { size: A4; margin: 2cm; }
      header, footer { position: fixed; }
      main{ padding: 0; margin-top: 40px; }
      .no-print{ display: none !important; }
    }
  </style>
  </head>
  <body>
    <header>
      <div style="display:flex; align-items:center; gap:12px;">
        <div style="font-weight:700;">نظام السلوك المدرسي</div>
        <div class="muted" style="margin-inline-start:auto">رقم الوثيقة: ${docId} · تاريخ الإصدار: ${y}-${m}-${d}</div>
      </div>
    </header>
    <footer>
      سري — للاستخدام المدرسي · صفحة 1 من 1 · للتحقق امسح رمز QR
    </footer>
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
    const w = window.open('', '_blank', 'noopener,noreferrer');
    if(!w){ throw new Error('تعذّر فتح نافذة الطباعة — الرجاء السماح بالنوافذ المنبثقة.'); }
    w.document.open();
    w.document.write(html);
    w.document.close();
    // سجّل أثر الطباعة كإجراء
    await run(async()=> await addIncidentAction(id.value, { name: 'تعهد خطي (طباعة)', notes: 'طُبع التعهد وسُلّم للموقّعين. رقم الوثيقة: '+docId }));
  }catch(e:any){
    msg.value = e?.message || 'فشل في إنشاء التعهد للطباعة';
  }
}

// خيار A: طباعة «تنبيه شفهي» من الواجهة
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
    <footer>
      سري — للاستخدام المدرسي · صفحة 1 من 1
    </footer>
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
    const w = window.open('', '_blank', 'noopener,noreferrer');
    if(!w){ throw new Error('تعذّر فتح نافذة الطباعة — الرجاء السماح بالنوافذ المنبثقة.'); }
    w.document.open(); w.document.write(html); w.document.close();
    await run(async()=> await addIncidentAction(id.value, { name: 'تنبيه شفهي (طباعة)', notes: 'رقم الوثيقة: '+docId }));
  }catch(e:any){ msg.value = e?.message || 'فشل في إنشاء تنبيه شفهي للطباعة'; }
}

// خيار A: طباعة ملخّص «إجراءات اللجنة»
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
    const w = window.open('', '_blank', 'noopener,noreferrer');
    if(!w){ throw new Error('تعذّر فتح نافذة الطباعة — الرجاء السماح بالنوافذ المنبثقة.'); }
    w.document.open(); w.document.write(html); w.document.close();
    await run(async()=> await addIncidentAction(id.value, { name: 'إجراءات اللجنة (طباعة)', notes: 'رقم الوثيقة: '+docId }));
  }catch(e:any){ msg.value = e?.message || 'فشل في إنشاء طباعة إجراءات اللجنة'; }
}

// خيار A: طباعة ملخّص «عقوبات اللجنة»
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
    const w = window.open('', '_blank', 'noopener,noreferrer');
    if(!w){ throw new Error('تعذّر فتح نافذة الطباعة — الرجاء السماح بالنوافذ المنبثقة.'); }
    w.document.open(); w.document.write(html); w.document.close();
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
