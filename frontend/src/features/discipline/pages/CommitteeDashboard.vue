<template>
  <section class="d-grid gap-3" dir="rtl">
    <header class="d-flex align-items-center gap-2">
      <h3 class="m-0">لوحة رئيس لجنة السلوك</h3>
      <div class="ms-auto d-flex align-items-center gap-2">
        <label class="form-label m-0">المدى</label>
        <select class="form-select form-select-sm w-auto" v-model.number="days" @change="reload">
          <option :value="7">آخر 7 أيام</option>
          <option :value="30">آخر 30 يومًا</option>
        </select>
        <button class="btn btn-sm btn-outline-primary" :disabled="loading" @click="reload">تحديث</button>
      </div>
    </header>

    <div v-if="loading" class="alert alert-info py-2">جاري التحميل ...</div>
    <div v-else-if="error" class="alert alert-warning py-2">{{ error }}</div>

    <div v-else>
      <!-- KPIs -->
      <div class="row g-3">
        <div class="col-md-3 col-6">
          <div class="card kpi kpi--all">
            <div class="kpi-title">تتطلّب لجنة</div>
            <div class="kpi-value">{{ data.kpis?.need_committee ?? 0 }}</div>
          </div>
        </div>
        <div class="col-md-3 col-6">
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
      <div class="row g-3">
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
        <div class="card-header">اللجنة السلوكية الدائمة</div>
        <div class="card-body">
          <div v-if="!data.standing" class="text-muted">لا يوجد تشكيل دائم محفوظ.</div>
          <div v-else class="row g-3">
            <div class="col-md-4">
              <div class="mini-box">
                <div class="mini-title">الرئيس</div>
                <div class="mini-value">{{ bestName(data.standing?.chair) }}</div>
              </div>
            </div>
            <div class="col-md-4">
              <div class="mini-box">
                <div class="mini-title">الأعضاء</div>
                <div class="mini-value">
                  <span v-if="!data.standing?.members || data.standing.members.length===0" class="text-muted">—</span>
                  <span v-else>{{ data.standing.members.map((m:any)=>bestName(m)).join('، ') }}</span>
                </div>
              </div>
            </div>
            <div class="col-md-4">
              <div class="mini-box">
                <div class="mini-title">المقرر</div>
                <div class="mini-value">{{ bestName(data.standing?.recorder) }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Queues -->
      <div class="row g-3">
        <div class="col-md-6">
          <div class="card h-100">
            <div class="card-header">تحتاج تشكيل لجنة</div>
            <ul class="list-group list-group-flush">
              <li v-for="it in (data.queues?.need_scheduling||[])" :key="it.id" class="list-group-item">
                <div class="d-flex align-items-center">
                  <div class="me-2 small text-muted">{{ it.violation_code || '—' }}</div>
                  <div class="flex-grow-1">{{ it.student_name || '—' }}</div>
                  <span class="badge" :class="sevClass(it.severity)">{{ it.severity }}</span>
                </div>
              </li>
              <li v-if="!data.queues || data.queues.need_scheduling.length===0" class="list-group-item text-muted">لا توجد عناصر</li>
            </ul>
          </div>
        </div>
        <div class="col-md-6">
          <div class="card h-100">
            <div class="card-header">مجدولة وتنتظر القرار</div>
            <ul class="list-group list-group-flush">
              <li v-for="it in (data.queues?.scheduled_pending_decision||[])" :key="it.id" class="list-group-item">
                <div class="d-flex align-items-center">
                  <div class="me-2 small text-muted">{{ it.violation_code || '—' }}</div>
                  <div class="flex-grow-1">{{ it.student_name || '—' }}</div>
                  <span class="badge" :class="sevClass(it.severity)">{{ it.severity }}</span>
                </div>
              </li>
              <li v-if="!data.queues || data.queues.scheduled_pending_decision.length===0" class="list-group-item text-muted">لا توجد عناصر</li>
            </ul>
          </div>
        </div>
      </div>

      <!-- Recent decisions -->
      <div class="card">
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
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { getCommitteeDashboard } from '../../discipline/api';

const loading = ref(false);
const error = ref('');
const data = ref<any>({});
const days = ref<7|30>(30);

function bestName(u?: any|null){
  if (!u) return '—';
  return (u.staff_full_name || u.full_name || u.username || '—');
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
function decisionLabel(d?: string){
  return d==='approve'?'موافقة': d==='reject'?'رفض': d==='return'?'إعادة':'—';
}

async function reload(){
  loading.value = true; error.value='';
  try{
    const res = await getCommitteeDashboard({ days: days.value });
    data.value = res || {};
  }catch(e:any){
    error.value = e?.message || 'تعذّر تحميل لوحة اللجنة';
  }finally{
    loading.value = false;
  }
}

onMounted(()=> reload());
</script>

<style scoped>
.kpi { padding: 8px 12px; }
.kpi-title { font-size: 13px; color: #666; padding: 6px 12px 0; }
.kpi-value { font-size: 28px; font-weight: 700; padding: 0 12px 10px; }
.kpi--all .kpi-value { color: #6d4c41; }
.kpi--warn .kpi-value { color: #c0392b; }
.kpi--info .kpi-value { color: #1565c0; }
.kpi--ok .kpi-value { color: #2e7d32; }
.mini-box { background: #fafafa; border: 1px solid #eee; border-radius: 8px; padding: 10px 12px; }
.mini-title { font-size: 12px; color: #666; }
.mini-value { font-weight: 600; }
</style>
