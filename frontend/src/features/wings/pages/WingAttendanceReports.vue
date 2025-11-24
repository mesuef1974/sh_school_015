<template>
  <section class="container py-3" dir="rtl">
    <div class="page-stack">
      <header class="d-flex align-items-center gap-2 flex-wrap">
        <h2 class="m-0">تقارير الحضور والغياب</h2>
        <span class="text-muted">لوحة مشرف الجناح</span>
        <div class="ms-auto d-flex align-items-end gap-2 flex-wrap">
          <select v-model="groupBy" class="form-select form-select-sm" style="width:auto" @change="onGroupChange">
            <option value="day">يومي</option>
            <option value="week">أسبوعي</option>
            <option value="month">شهري</option>
            <option value="term">فصلي</option>
          </select>
          <div v-if="groupBy!=='term'" class="d-flex align-items-center gap-1">
            <label class="form-label mb-0 small">التاريخ</label>
            <input v-if="useSingleDate" type="date" v-model="date" class="form-control form-control-sm" @change="reload" />
            <template v-else>
              <input type="date" v-model="from" class="form-control form-control-sm" @change="reload" />
              <span>–</span>
              <input type="date" v-model="to" class="form-control form-control-sm" @change="reload" />
            </template>
            <div class="form-check form-switch ms-2">
              <input class="form-check-input" type="checkbox" id="switchRange" v-model="useSingleDate" @change="reload" />
              <label class="form-check-label small" for="switchRange">يوم واحد</label>
            </div>
          </div>
          <div v-else class="d-flex align-items-center gap-1">
            <label class="form-label mb-0 small">الفصل</label>
            <select v-model="termId" class="form-select form-select-sm" style="width:auto" @change="reload">
              <option v-for="t in terms" :key="t.id" :value="t.id">{{ t.name }} ({{ t.start_date }} → {{ t.end_date }})</option>
            </select>
          </div>
          <div class="form-check form-switch">
            <input class="form-check-input" type="checkbox" id="switchPending" v-model="includePending" @change="reload" />
            <label class="form-check-label small" for="switchPending">عرض الأعذار قيد المراجعة</label>
          </div>
          <button class="btn btn-sm btn-outline-primary" :disabled="loading" @click="reload">تحديث</button>
          <button class="btn btn-sm btn-outline-secondary" :disabled="loading || rows.length===0" @click="exportCsv">تصدير CSV</button>
        </div>
      </header>

      <!-- KPIs -->
      <div class="row g-2">
        <div class="col-6 col-md-3">
          <div class="card stat p-2">
            <div class="label">إجمالي الطلبة</div>
            <div class="value" dir="ltr">{{ kpi.total_students }}</div>
          </div>
        </div>
        <div class="col-6 col-md-3">
          <div class="card stat p-2">
            <div class="label">الحضور</div>
            <div class="value" dir="ltr">{{ kpi.present }} ({{ fmtPct(kpi.present_pct) }})</div>
          </div>
        </div>
        <div class="col-6 col-md-3">
          <div class="card stat p-2">
            <div class="label">الغياب</div>
            <div class="value" dir="ltr">{{ kpi.absent_total }} ({{ fmtPct(kpi.absent_pct) }})</div>
          </div>
        </div>
        <div class="col-6 col-md-3">
          <div class="card stat p-2">
            <div class="label">مبرر / غير مبرر</div>
            <div class="value" dir="ltr">{{ kpi.absent_excused }} / {{ kpi.absent_unexcused }}</div>
          </div>
        </div>
      </div>

      <!-- Switch result kind -->
      <ul class="nav nav-tabs">
        <li class="nav-item"><button class="nav-link" :class="{active: tab==='class'}" @click="tab='class'">حسب الصف</button></li>
        <li class="nav-item"><button class="nav-link" :class="{active: tab==='wing'}" @click="tab='wing'">حسب الجناح</button></li>
        <li class="nav-item"><button class="nav-link" :class="{active: tab==='school'}" @click="tab='school'">المدرسة</button></li>
      </ul>

      <div class="card p-0">
        <div class="table-responsive">
          <table class="table table-hover align-middle mb-0">
            <thead class="table-light">
              <tr>
                <th>الحاوية الزمنية</th>
                <th v-if="tab==='class'">الصف</th>
                <th v-if="tab!=='school'">الجناح</th>
                <th class="text-end">إجمالي الطلبة</th>
                <th class="text-end">حضور</th>
                <th class="text-end">غياب</th>
                <th class="text-end">مبرر</th>
                <th class="text-end">غير مبرر</th>
                <th class="text-end">معلّق</th>
                <th class="text-end">نسبة الحضور</th>
                <th class="text-end">نسبة الغياب</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!loading && rows.length===0">
                <td colspan="10" class="text-center text-muted py-4">لا توجد بيانات لعرضها</td>
              </tr>
              <tr v-for="(r,idx) in rows" :key="idx">
                <td>{{ r.date_bucket }}</td>
                <td v-if="tab==='class'">{{ r.class_name || ('#'+r.class_id) }}</td>
                <td v-if="tab!=='school'">{{ r.wing_id ?? '—' }}</td>
                <td class="text-end" dir="ltr">{{ r.total_students }}</td>
                <td class="text-end" dir="ltr">{{ r.present }}</td>
                <td class="text-end" dir="ltr">{{ r.absent_total }}</td>
                <td class="text-end" dir="ltr">{{ r.absent_excused }}</td>
                <td class="text-end" dir="ltr">{{ r.absent_unexcused }}</td>
                <td class="text-end" dir="ltr">{{ r.absent_pending || 0 }}</td>
                <td class="text-end" dir="ltr">{{ fmtPct(r.present_pct) }}</td>
                <td class="text-end" dir="ltr">{{ fmtPct(r.absent_pct) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="loading" class="p-3 text-muted">جاري التحميل …</div>
        <div v-if="!loading && error" class="p-3 text-danger border-top">{{ error }}</div>
        <div class="d-flex justify-content-between align-items-center p-2 border-top small text-muted">
          <div>آخر تحديث: {{ lastUpdated || '—' }}</div>
          <div>
            عدد الصفوف: {{ rows.length }}
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';
import { useAuthStore } from '../../../app/stores/auth';
import { getAttendanceReportClasses, getAttendanceReportWings, getAttendanceReportSchool, getAttendanceTerms } from '../../../shared/api/client';

const auth = useAuthStore();
const loading = ref(false);
const error = ref('');
const lastUpdated = ref('');
const tab = ref<'class'|'wing'|'school'>('class');
const groupBy = ref<'day'|'week'|'month'|'term'>('day');
const date = ref<string>('');
const from = ref<string>('');
const to = ref<string>('');
const useSingleDate = ref(true);
const terms = ref<Array<{id:number; name:string; start_date:string; end_date:string}>>([]);
const termId = ref<number|undefined>(undefined);

const rows = ref<any[]>([]);
const includePending = ref(false);
const kpi = ref({ total_students: 0, present: 0, absent_total: 0, absent_excused: 0, absent_unexcused: 0, present_pct: 0, absent_pct: 0 });

function fmtPct(n: number){
  const x = Number(n||0); return isFinite(x)? `${x.toFixed(2)}%` : '0.00%';
}

function onGroupChange(){
  if (groupBy.value === 'term') {
    // ensure terms loaded
    loadTerms();
    useSingleDate.value = true;
  }
  reload();
}

async function loadTerms(){
  try{
    const res = await getAttendanceTerms();
    terms.value = res.items || [];
    if (!termId.value && terms.value.length) termId.value = terms.value[0].id;
  } catch{}
}

function params(){
  const p:any = { group_by: groupBy.value };
  if (groupBy.value === 'term') {
    // backend will respect from/to; pass selected term bounds for precision
    const t = terms.value.find(t=> t.id === termId.value);
    if (t) { p.from = t.start_date; p.to = t.end_date; }
  } else if (useSingleDate.value) {
    if (!date.value) date.value = new Date().toISOString().slice(0,10);
    p.date = date.value;
  } else {
    if (!from.value || !to.value) {
      const today = new Date().toISOString().slice(0,10);
      from.value = from.value || today; to.value = to.value || today;
    }
    p.from = from.value; p.to = to.value;
  }
  if (includePending.value) p.include_pending = 1;
  return p;
}

async function reload(){
  loading.value = true; error.value=''; rows.value = []; kpi.value = { total_students: 0, present: 0, absent_total: 0, absent_excused: 0, absent_unexcused: 0, present_pct: 0, absent_pct: 0 };
  try{
    const p = params();
    if (tab.value === 'class'){
      const res = await getAttendanceReportClasses(p);
      rows.value = res.items || [];
    } else if (tab.value === 'wing'){
      const res = await getAttendanceReportWings(p);
      rows.value = res.items || [];
    } else {
      const res = await getAttendanceReportSchool(p);
      rows.value = res.items || [];
    }
    // compute KPIs over current rows
    let ts=0, pres=0, ab=0, ex=0, unx=0;
    for (const r of rows.value){
      ts += Number(r.total_students||0);
      pres += Number(r.present||0);
      ab += Number(r.absent_total||0);
      ex += Number(r.absent_excused||0);
      unx += Number(r.absent_unexcused||0);
    }
    const present_pct = ts? (pres/ts)*100 : 0;
    const absent_pct = ts? (ab/ts)*100 : 0;
    kpi.value = { total_students: ts, present: pres, absent_total: ab, absent_excused: ex, absent_unexcused: unx, present_pct: Number(present_pct.toFixed(2)), absent_pct: Number(absent_pct.toFixed(2)) };
    lastUpdated.value = new Date().toLocaleString();
  } catch(e:any){
    error.value = e?.message || 'تعذّر تحميل البيانات';
  } finally {
    loading.value = false;
  }
}

function exportCsv(){
  try{
    const headers = tab.value==='class'
      ? ['date_bucket','class_id','class_name','wing_id','total_students','present','absent_total','absent_excused','absent_unexcused','absent_pending','present_pct','absent_pct']
      : tab.value==='wing'
        ? ['date_bucket','wing_id','total_students','present','absent_total','absent_excused','absent_unexcused','absent_pending','present_pct','absent_pct']
        : ['date_bucket','total_students','present','absent_total','absent_excused','absent_unexcused','absent_pending','present_pct','absent_pct'];
    const rowsCsv = rows.value.map((r:any)=> headers.map((h:string)=> r[h] ?? ''));
    const csv = [headers.join(','), ...rowsCsv.map(r=> r.map((v:any)=> String(v).includes(',')? '"'+String(v).replaceAll('"','""')+'"' : String(v)).join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `attendance_reports_${new Date().toISOString().slice(0,10)}.csv`;
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    URL.revokeObjectURL(url);
  } catch {}
}

onMounted(async ()=>{
  // Defaults
  date.value = new Date().toISOString().slice(0,10);
  await loadTerms();
  await reload();
});

watch([tab, groupBy], ()=> reload());
</script>

<style scoped>
.page-stack{ display:grid; gap:12px; }
.stat { border-radius: 10px; }
.stat .label{ font-size: 12px; color:#6c757d; }
.stat .value{ font-size: 20px; font-weight: 600; }
</style>
