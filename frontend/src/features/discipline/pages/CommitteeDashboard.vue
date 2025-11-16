<template>
  <section class="d-grid gap-9 committee-dashboard" dir="rtl">
    <!-- شريط عنوان الصفحة الموحّد في المنصة -->
    <WingPageHeader icon="solar:shield-check-bold-duotone" title="لوحة رئيس لجنة السلوك" :subtitle="'إدارة اللجان والقرارات'">
      <template #actions>
        <div class="d-flex align-items-center gap-2 flex-wrap">
          <label class="form-label m-0">المدى</label>
          <select class="form-select form-select-sm w-auto" v-model.number="days" @change="reload">
            <option :value="7">آخر 7 أيام</option>
            <option :value="30">آخر 30 يومًا</option>
          </select>
          <button class="btn btn-sm btn-outline-primary" :disabled="loading" @click="reload">تحديث</button>
          <RouterLink class="btn btn-sm btn-outline-secondary" to="/discipline/committee/member">صفحة الأعضاء</RouterLink>
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
        <span v-if="caps.is_staff" class="badge bg-info text-dark">Staff</span>
        <span v-if="caps.is_superuser" class="badge bg-dark">Superuser</span>
        <span class="vr"></span>
        <span v-if="caps.is_standing_chair" class="badge bg-primary">رئيس اللجنة الدائمة</span>
        <span v-if="caps.is_standing_member && !caps.is_standing_chair" class="badge bg-secondary">عضو اللجنة الدائمة</span>
        <span v-if="caps.is_standing_recorder" class="badge bg-info text-dark">مقرر اللجنة الدائمة</span>
      </div>
      <!-- KPIs -->
      <div class="row g-7">
        <div class="col-md-3 col-6">
          <div class="card kpi kpi--all">
            <div class="kpi-title">تتطلّب لجنة</div>
            <div class="kpi-value">{{ data.kpis?.need_committee ?? 0 }}</div>
          </div>
        </div>
        <div class="col-md-3 col-6" v-if="caps?.can_schedule">
          <div class="card kpi kpi--warn">
            <div class="kpi-title">بحاجة لتشكيل</div>
            <div class="kpi-value">{{ data.kpis?.need_scheduling ?? 0 }}</div>
          </div>
        </div>
        <div class="col-md-3 col-6">
          <div class="card kpi kpi--info">
            <div class="kpi-title">مُجَدولة وتنتظر قرار</div>
            <div class="kpi-value">{{ data.kpis?.scheduled_pending ?? 0 }}</div>
          </div>
        </div>
        <div class="col-md-3 col-6">
          <div class="card kpi kpi--ok">
            <div class="kpi-title">قرارات ({{ days }} يوم)</div>
            <div class="kpi-value">
              {{ (data.kpis?.decisions_recent?.approve||0) + (data.kpis?.decisions_recent?.reject||0) + (data.kpis?.decisions_recent?.return||0) }}
            </div>
            <div class="small text-muted px-3 pb-2">
              موافق: {{ data.kpis?.decisions_recent?.approve||0 }} · مرفوض: {{ data.kpis?.decisions_recent?.reject||0 }} · إعادة: {{ data.kpis?.decisions_recent?.return||0 }}
            </div>
          </div>
        </div>
      </div>

      <!-- Overdue + Top violations -->
      <div class="row g-7">
        <div class="col-md-6">
          <div class="card">
            <div class="card-header">تنبيهات التأخر (SLA)</div>
            <div class="card-body">
              <ul class="mb-0">
                <li>متأخرة عن الاستلام: <strong>{{ data.overdue?.review ?? 0 }}</strong></li>
                <li>متأخرة عن الإشعار: <strong>{{ data.overdue?.notify ?? 0 }}</strong></li>
              </ul>
            </div>
          </div>
        </div>
        <div class="col-md-6">
          <div class="card">
            <div class="card-header">أكثر المخالفات تكرارًا</div>
            <ul class="list-group list-group-flush">
              <li v-for="v in (data.top_violations_30d||[])" :key="v.code+String(v.category)" class="list-group-item d-flex justify-content-between align-items-center">
                <span>{{ v.code || '—' }} — {{ v.category || 'غير محدد' }}</span>
                <span class="badge bg-secondary">{{ v.count }}</span>
              </li>
              <li v-if="!data.top_violations_30d || data.top_violations_30d.length===0" class="list-group-item text-muted">لا توجد بيانات</li>
            </ul>
          </div>
        </div>
      </div>

      <!-- Standing committee -->
      <div class="card">
        <div class="card-header d-flex align-items-center gap-2">
          <span>اللجنة السلوكية الدائمة</span>
          <span class="ms-auto small text-muted">تُستخدم كقائمة افتراضية لتشكيل أي لجنة واقعة</span>
        </div>
        <div class="card-body">
          <div v-if="!data.standing" class="text-muted">لا يوجد تشكيل دائم محفوظ.</div>
          <div v-else class="row g-7">
            <div class="col-md-4">
              <div class="mini-box role-box">
                <div class="mini-title">الرئيس</div>
                <div class="mini-value d-flex align-items-center gap-2">
                  <span class="avatar" :title="bestName(data.standing?.chair)">{{ initialsOf(data.standing?.chair) }}</span>
                  <span class="fw-semibold">{{ bestName(data.standing?.chair) }}</span>
                  <span class="badge role-badge bg-primary-subtle text-primary">رئيس</span>
                </div>
              </div>
            </div>
            <div class="col-md-4">
              <div class="mini-box role-box">
                <div class="mini-title">الأعضاء</div>
                <div class="mini-value d-flex flex-wrap gap-2">
                  <span v-if="!data.standing?.members || data.standing.members.length===0" class="text-muted">—</span>
                  <template v-else>
                    <span v-for="m in data.standing.members" :key="'m'+m.id" class="chip" :title="bestName(m)">
                      <span class="avatar avatar--sm">{{ initialsOf(m) }}</span>
                      <span class="chip-text">{{ bestName(m) }}</span>
                    </span>
                  </template>
                </div>
              </div>
            </div>
            <div class="col-md-4">
              <div class="mini-box role-box">
                <div class="mini-title">المقرر</div>
                <div class="mini-value d-flex align-items-center gap-2">
                  <span class="avatar" :title="bestName(data.standing?.recorder)">{{ initialsOf(data.standing?.recorder) }}</span>
                  <span class="fw-semibold">{{ bestName(data.standing?.recorder) }}</span>
                  <span class="badge role-badge bg-info-subtle text-info">مقرر</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Queues -->
      <div class="row g-7">
        <div class="col-md-6">
          <div class="card h-100">
            <div class="card-header">تحتاج تشكيل لجنة</div>
            <ul class="list-group list-group-flush">
              <li v-for="it in (data.queues?.need_scheduling||[])" :key="it.id" class="list-group-item">
                <div class="d-flex align-items-center gap-2">
                  <div class="me-2 small text-muted" :title="'رمز المخالفة'">{{ it.violation_code || '—' }}</div>
                  <RouterLink class="flex-grow-1 text-decoration-none" :to="{ name: 'discipline-incident-card', params: { id: it.id } }" :title="'فتح بطاقة الواقعة'">
                    {{ it.student_name || '—' }}
                  </RouterLink>
                  <span class="badge" :class="sevClass(it.severity)" :title="'الشدة'">{{ it.severity }}</span>
                  <button
                    class="btn btn-sm btn-outline-primary ms-2"
                    :disabled="scheduleBusy===it.id"
                    :title="'تشكيل فوري باستخدام اللجنة الدائمة'"
                    @click="scheduleNow(it.id)"
                  >
                    {{ scheduleBusy===it.id ? 'جارٍ التشكيل…' : 'تشكيل الآن' }}
                  </button>
                </div>
              </li>
              <li v-if="!data.queues || data.queues.need_scheduling.length===0" class="list-group-item text-muted">لا توجد عناصر</li>
            </ul>
          </div>
        </div>
        <div class="col-md-6" v-if="caps?.can_decide">
          <div class="card h-100">
            <div class="card-header">مجدولة وتنتظر القرار</div>
            <ul class="list-group list-group-flush">
              <li v-for="it in (data.queues?.scheduled_pending_decision||[])" :key="it.id" class="list-group-item">
                <div class="d-flex align-items-center">
                  <div class="me-2 small text-muted" :title="'رمز المخالفة'">{{ it.violation_code || '—' }}</div>
                  <RouterLink class="flex-grow-1 text-decoration-none" :to="{ name: 'discipline-incident-card', params: { id: it.id } }" :title="'فتح بطاقة الواقعة'">
                    {{ it.student_name || '—' }}
                  </RouterLink>
                  <span class="badge" :class="sevClass(it.severity)" :title="'الشدة'">{{ it.severity }}</span>
                </div>
                <div v-if="it.proposed_summary" class="small text-muted mt-1">
                  {{ it.proposed_summary }}
                </div>
              </li>
              <li v-if="!data.queues || data.queues.scheduled_pending_decision.length===0" class="list-group-item text-muted">لا توجد عناصر</li>
            </ul>
          </div>
        </div>
      </div>

      <!-- بطاقات مختصرة لروابط صفحات العضو والمقرر -->
      <div class="row g-7">
        <div class="col-md-6">
          <div class="card h-100">
            <div class="card-header d-flex align-items-center">
              <span>بطاقة «عضو اللجنة»</span>
              <RouterLink class="btn btn-sm btn-outline-secondary ms-auto" to="/discipline/committee/member">الانتقال للصفحة</RouterLink>
            </div>
            <div class="card-body small text-muted">
              استعرض وقائع اللجان التي أنت ضمنها وصوّت بسرعة (موافقة/رفض/إعادة) مع ملخص فوري للنصاب والأغلبية.
            </div>
          </div>
        </div>
        <div class="col-md-6">
          <div class="card h-100">
            <div class="card-header d-flex align-items-center">
              <span>بطاقة «مقرّر اللجنة»</span>
              <RouterLink class="btn btn-sm btn-outline-info ms-auto" to="/discipline/committee/recorder">الانتقال للصفحة</RouterLink>
            </div>
            <div class="card-body small text-muted">
              تابع الأصوات والسجّل الملخّص للقرارات لتسهيل تدوين المحضر واعتماد الرئيس للقرار النهائي.
            </div>
          </div>
        </div>
      </div>

      <!-- Recent decisions -->
      <div class="card mt-3">
        <div class="card-header">أحدث قرارات اللجنة</div>
        <ul class="list-group list-group-flush">
          <li v-for="r in (data.recent_decisions||[])" :key="r.incident_id+String(r.at)" class="list-group-item d-flex align-items-center">
            <span class="badge me-2" :class="decisionClass(r.decision)">{{ decisionLabel(r.decision) }}</span>
            <span class="me-3">{{ r.actor || '—' }}</span>
            <span class="text-muted small">{{ fmtDate(r.at) }}</span>
          </li>
          <li v-if="!data.recent_decisions || data.recent_decisions.length===0" class="list-group-item text-muted">لا توجد قرارات حديثة</li>
        </ul>
      </div>

      <!-- Help: كيف يتم اتخاذ الإجراء في الواقعة؟ -->
      <div class="card mt-3">
        <div class="card-header d-flex align-items-center gap-2">
          <span>كيف يتم اتخاذ الإجراء في الواقعة؟</span>
          <span class="ms-auto small text-muted">مختصر دورة حياة البلاغ</span>
        </div>
        <div class="card-body">
          <ol class="mb-2 small lh-lg">
            <li><strong>إنشاء الواقعة</strong> (incident_create) من صفحة الوقائع.</li>
            <li><strong>إرسال للمراجعة</strong> (incident_submit) ثم <strong>استلام/مراجعة</strong> (incident_review).</li>
            <li>يمكن <strong>إشعار ولي الأمر</strong> (incident_notify_guardian) وتسجيل القناة/الملاحظة.</li>
            <li>عند الحاجة، <strong>تصعيد/تفعيل اللجنة</strong> ثم <strong>إحالة تلقائية إلى اللجنة السلوكية الدائمة</strong> (لا يوجد تشكيل يدوي).</li>
            <li><strong>قرار اللجنة</strong> (approve | reject | return) مع ملاحظات، ويمكن الإغلاق الفوري عند الموافقة.</li>
            <li>أخيرًا، <strong>إغلاق الواقعة</strong> (incident_close) بعد تنفيذ الإجراء المناسب.</li>
          </ol>
          <div class="small text-muted">للتفاصيل الكاملة راجع الوثيقة: <code>docs/INCIDENT_LIFECYCLE.md</code></div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { getCommitteeDashboard, scheduleCommittee } from '../../discipline/api';
import WingPageHeader from '../../../components/ui/WingPageHeader.vue';

const loading = ref(false);
const error = ref('');
const data = ref<any>({});
const days = ref<7|30>(30);
const caps = ref<any>(null);
const scheduleBusy = ref<string>('');

function bestName(u?: any|null){
  if (!u) return '—';
  return (u.staff_full_name || u.full_name || u.username || '—');
}

function initialsOf(u?: any|null){
  const name = bestName(u);
  if (!name || name === '—') return '؟';
  try {
    const parts = String(name).trim().split(/\s+/);
    if (parts.length === 1) return parts[0].slice(0,2).toUpperCase();
    const first = parts[0].slice(0,1);
    const last = parts[parts.length-1].slice(0,1);
    return (first + last).toUpperCase();
  } catch {
    return String(name).slice(0,2).toUpperCase();
  }
}

function fmtDate(s?: string){
  if (!s) return '';
  try { const d=new Date(s); const y=d.getFullYear(); const m=String(d.getMonth()+1).padStart(2,'0'); const dd=String(d.getDate()).padStart(2,'0'); return `${y}-${m}-${dd}`; } catch { return s; }
}

function sevClass(sev?: number){
  const s = Number(sev||1);
  return s>=4? 'bg-danger': s===3? 'bg-warning text-dark': s===2? 'bg-info text-dark': 'bg-success';
}
function decisionClass(d?: string){
  if (d==='approve') return 'bg-success';
  if (d==='reject') return 'bg-danger';
  if (d==='return') return 'bg-warning text-dark';
  return 'bg-secondary';
}

async function scheduleNow(id: string){
  if (!id) return;
  if (!window.confirm('سيتم تشكيل اللجنة باستخدام «اللجنة السلوكية الدائمة». هل تريد المتابعة؟')) return;
  scheduleBusy.value = id;
  try {
    await scheduleCommittee(id, { use_standing: true });
    // Refresh dashboard queues after successful scheduling
    await reload();
  } catch (e: any) {
    const msg = e?.response?.data?.detail || e?.message || 'تعذّر التشكيل';
    alert(msg);
  } finally {
    scheduleBusy.value = '';
  }
}
function decisionLabel(d?: string){
  return d==='approve'?'موافقة': d==='reject'?'رفض': d==='return'?'إعادة':'—';
}

async function reload(){
  loading.value = true; error.value='';
  try{
    const res = await getCommitteeDashboard({ days: days.value });
    data.value = res || {};
    caps.value = res?.access_caps || null;
  }catch(e:any){
    error.value = e?.message || 'تعذّر تحميل لوحة اللجنة';
  }finally{
    loading.value = false;
  }
}

onMounted(()=> reload());
</script>

<style scoped>
.committee-dashboard .card { border-radius: 12px; box-shadow: 0 1px 2px rgba(0,0,0,.04); }
/* فصل أكبر بين البطاقات المتجاورة رأسياً */
.committee-dashboard .card + .card { margin-top: 1.25rem; }
/* Gutters أوسع لمنع التلاصق أفقياً وعمودياً */
.committee-dashboard .row { --bs-gutter-x: 3rem; --bs-gutter-y: 2.75rem; }
.kpi { padding: 12px 14px; }
.kpi-title { font-size: 13px; color: #666; padding: 6px 12px 0; }
.kpi-value { font-size: 28px; font-weight: 700; padding: 0 12px 10px; }
.kpi--all .kpi-value { color: #6d4c41; }
.kpi--warn .kpi-value { color: #c0392b; }
.kpi--info .kpi-value { color: #1565c0; }
.kpi--ok .kpi-value { color: #2e7d32; }
.mini-box { background: #fafafa; border: 1px solid #eee; border-radius: 12px; padding: 12px 14px; }
.role-box { min-height: 88px; }
.mini-title { font-size: 12px; color: #666; }
.mini-value { font-weight: 600; }

/* Avatar + chips for members */
.avatar { display: inline-flex; align-items: center; justify-content: center; width: 32px; height: 32px; border-radius: 50%; background: #e9ecef; color: #495057; font-weight: 700; }
.avatar--sm { width: 24px; height: 24px; font-size: 11px; }
.chip { display: inline-flex; align-items: center; gap: 6px; border: 1px solid #e0e0e0; background: #fff; border-radius: 999px; padding: 4px 8px 4px 6px; }
.chip-text { max-width: 160px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.role-badge { font-size: 11px; }

/* تباعد إضافي على الشاشات الصغيرة لضمان عدم تلاصق البطاقات */
@media (max-width: 768px){
  .committee-dashboard .card { margin-bottom: 1rem; }
  .committee-dashboard .row { --bs-gutter-x: 1.25rem; --bs-gutter-y: 1.25rem; }
}
</style>
