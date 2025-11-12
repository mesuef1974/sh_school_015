<template>
  <section class="container py-3" dir="rtl">
    <div class="page-stack">
      <WingPageHeader icon="solar:shield-check-bold-duotone" title="وقائع الانضباط (واجهة مبسطة)" :subtitle="'صفحة مبسطة تم إنشاؤها من الصفر وتستدعي البيانات من قاعدة البيانات عبر واجهة الـ API'">
        <template #actions>
          <div class="d-flex align-items-end gap-2 flex-wrap">
            <div v-if="isPrivileged" class="d-flex align-items-center gap-1">
              <label class="form-label mb-0 small">النطاق</label>
              <select v-model="scope" class="form-select form-select-sm" style="width:auto" @change="onScopeChange">
                <option value="mine">سجلاتي</option>
                <option value="all">الكل</option>
              </select>
            </div>
            <div>
              <input v-model.trim="q" @keyup.enter="reload" type="search" class="form-control form-control-sm" placeholder="بحث بالوصف/المكان/المخالفة" style="min-width:240px" />
            </div>
            <select v-model="status" class="form-select form-select-sm" style="width:auto" @change="reload">
              <option value="">كل الحالات</option>
              <option value="open">مسودة</option>
              <option value="under_review">قيد المراجعة</option>
              <option value="closed">مغلقة</option>
            </select>
            <button class="btn btn-sm btn-outline-primary" :disabled="loading" @click="reload">تحديث</button>
            <button class="btn btn-sm btn-outline-secondary" :disabled="loading || items.length===0" @click="exportCsv">تصدير CSV</button>
          </div>
        </template>
      </WingPageHeader>

      <div class="card p-0 mt-3">
        <div class="table-responsive">
          <table class="table table-hover align-middle mb-0">
            <thead class="table-light">
              <tr>
                <th>التاريخ</th>
                <th>التوقيت</th>
                <th>الفصل</th>
                <th>المخالفة</th>
                <th>الطالب</th>
                <th class="text-center">وقائع الطالب</th>
                <th>مسجل الواقعة</th>
                <th>درجة المخالقة</th>
                <th>الحالة</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!loading && items.length === 0 && !error">
                <td colspan="9" class="text-center text-muted py-4">لا توجد بيانات لعرضها</td>
              </tr>
              <tr v-for="it in displayedItems" :key="it.id">
                <td>{{ fmtDate(it.occurred_at) }}</td>
                <td>{{ it.occurred_time || fmtTime(it.occurred_at) }}</td>
                <td>{{ it.class_name || '—' }}</td>
                <td>{{ it.violation_display || it.violation?.code || '—' }}</td>
                <td>{{ it.student_name || ('#'+it.student) }}</td>
                <td class="text-center">
                  <button
                    v-if="it.student"
                    class="btn btn-sm btn-light border"
                    :title="'عرض جميع وقائع الطالب'"
                    @click="openStudentIncidents(it.student, it.student_name)"
                  >
                    <template v-if="counts[String(it.student)] !== undefined">
                      <span class="badge bg-primary">{{ counts[String(it.student)] }}</span>
                    </template>
                    <template v-else>
                      <span class="badge bg-secondary">…</span>
                    </template>
                  </button>
                  <span v-else>—</span>
                </td>
                <td>{{ it.reporter_name || '—' }}</td>
                <td><span class="badge bg-secondary">{{ it.severity ?? '—' }}</span></td>
                <td>
                  <span class="badge" :class="badgeFor(it.status)">{{ statusAr(it.status) }}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="loading" class="p-3 text-muted">جاري التحميل …</div>
        <div v-if="!loading && error" class="p-3 text-danger border-top">{{ error }}
          <button class="btn btn-sm btn-outline-secondary ms-2" @click="reload">محاولة مجددًا</button>
        </div>
        <div class="d-flex justify-content-between align-items-center p-2 border-top small text-muted">
          <div>آخر تحديث: {{ lastUpdated || '—' }}</div>
          <div>
            عدد السجلات: {{ items.length }}
            <span class="ms-2">حجم الصفحة: {{ pageSize }}</span>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { listIncidents, getIncidentsMine, countIncidentsByStudent } from '../api';
import { useAuthStore } from '../../../app/stores/auth';
import WingPageHeader from '../../../components/ui/WingPageHeader.vue';
import { router } from '../../../app/router';

const auth = useAuthStore();
const items = ref<any[]>([]);
const counts = ref<Record<string, number>>({});
const loading = ref(false);
const error = ref('');
const lastUpdated = ref<string>('');
const status = ref('');
const q = ref('');
const pageSize = 25;

const isPrivileged = computed(() => !!(auth.profile?.is_superuser || auth.profile?.is_staff || (auth.profile?.permissions||[]).includes('discipline.access')));
const SCOPE_STORAGE_KEY = 'discipline_incidents_simple_scope';
function loadSavedScope(): 'mine'|'all' {
  try { const v = localStorage.getItem(SCOPE_STORAGE_KEY); if (v==='mine' || v==='all') return v as any; } catch {}
  return isPrivileged.value ? 'all' : 'mine';
}
const scope = ref<'mine'|'all'>(loadSavedScope());
function onScopeChange(){ try { localStorage.setItem(SCOPE_STORAGE_KEY, scope.value) } catch {} reload(); }

function fmtDate(s?: string){ if(!s) return '—'; try{ const d=new Date(s); const y=d.getFullYear(); const m=String(d.getMonth()+1).padStart(2,'0'); const dd=String(d.getDate()).padStart(2,'0'); return `${y}-${m}-${dd}`; }catch{ return s as string; } }
function badgeFor(st: string){ return st==='closed'?'bg-secondary':(st==='under_review'?'bg-warning text-dark':'bg-info'); }
function statusAr(st: string){ return st==='closed'?'مغلقة':(st==='under_review'?'قيد المراجعة':'مسودة'); }
function fmtTime(s?: string){ if(!s) return '—'; try{ const d=new Date(s); const hh=String(d.getHours()).padStart(2,'0'); const mm=String(d.getMinutes()).padStart(2,'0'); return `${hh}:${mm}`; }catch{ return ''; } }

// Arabic plural label for "violations"
function arCountLabel(n: number){
  const x = Number(n||0);
  if (x === 0) return 'مخالفات';
  if (x === 1) return 'مخالفة';
  if (x === 2) return 'مخالفتان';
  if (x >= 3 && x <= 10) return 'مخالفات';
  return 'مخالفة'; // generic for >10
}

// Show only the latest incident per student (items are already sorted DESC by backend)
const displayedItems = computed(() => {
  const seen = new Set<string>();
  const out: any[] = [];
  for (const it of items.value) {
    const sid = (it && (String(it.student||''))) || '';
    if (!sid) { out.push(it); continue; }
    if (seen.has(sid)) continue; // already captured a newer one
    seen.add(sid);
    out.push(it);
  }
  return out;
});

async function reload(){
  loading.value = true; error.value=''; items.value=[];
  const ac = new AbortController();
  const timeout = setTimeout(()=> ac.abort(), 10000);
  try{
    const params:any = { page_size: pageSize };
    if (status.value) params.status = status.value;
    if (q.value) params.search = q.value;
    let data: any;
    if (!isPrivileged.value) {
      data = await getIncidentsMine(params, { signal: ac.signal });
    } else {
      data = scope.value === 'mine' ? await getIncidentsMine(params, { signal: ac.signal })
                                    : await listIncidents(params, { signal: ac.signal });
    }
    items.value = Array.isArray(data) ? data : (data?.results ?? []);
    // Fetch counts per student for currently visible items
    await fetchStudentCounts();
    lastUpdated.value = new Date().toLocaleString();
  } catch(e:any){
    if (e?.code === 'ERR_CANCELED') {
      error.value = 'انتهت مهلة الاتصال (10 ثوانٍ). حاول مجددًا.';
    } else if (e?.status === 401) {
      error.value = 'انتهت الجلسة. يرجى تسجيل الدخول مجددًا.';
    } else if (e?.status === 403) {
      error.value = 'لا تملك صلاحية كافية لعرض هذه البيانات.';
    } else {
      error.value = e?.message || 'تعذّر تحميل البيانات';
    }
  } finally {
    clearTimeout(timeout);
    loading.value = false;
  }
}

async function fetchStudentCounts(){
  try{
    const ids = Array.from(new Set(items.value.map((it:any)=> it?.student).filter((v:any)=> typeof v==='number' || (typeof v==='string' && /^\d+$/.test(v))))).map(String);
    if (ids.length === 0) { counts.value = {}; return; }
    const res = await countIncidentsByStudent({ student: ids });
    const map: Record<string, number> = { };
    for (const id of ids) {
      const v = (res && (res as any)[id]);
      map[id] = typeof v === 'number' ? v : 0;
    }
    // If backend returned empty mapping (possible caching/perm), fallback to local tally from current items
    const empty = Object.keys(res || {}).length === 0;
    if (empty) {
      for (const it of items.value) {
        const sid = String(it?.student || '');
        if (!sid) continue;
        map[sid] = (map[sid] || 0) + 1;
      }
    }
    counts.value = map;
  } catch {
    // On error, fallback to local tally so the user still sees a number
    const map: Record<string, number> = {};
    for (const it of items.value) {
      const sid = String(it?.student || '');
      if (!sid) continue;
      map[sid] = (map[sid] || 0) + 1;
    }
    counts.value = map;
  }
}

function openStudentIncidents(studentId: string|number, studentName?: string){
  const idStr = String(studentId);
  const route = router.resolve({ name: 'discipline-student-incidents', params: { studentId: idStr }, query: studentName? { name: studentName } : {} });
  window.open(route.href, '_blank');
}

function exportCsv(){
  try{
    const headers = ['id','occurred_at','violation','student','reporter','degree','status'];
    const rows = items.value.map((it:any)=>[
      it.id,
      it.occurred_at || '',
      (it.violation_display || it.violation?.code || ''),
      (it.student_name || it.student || ''),
      (it.reporter_name || ''),
      (it.severity ?? ''),
      (it.status || '')
    ]);
    const csv = [headers.join(','), ...rows.map(r=> r.map(v => String(v).includes(',')? '"'+String(v).replaceAll('"','""')+'"' : String(v)).join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `discipline_incidents_${new Date().toISOString().slice(0,10)}.csv`;
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    URL.revokeObjectURL(url);
  } catch {}
}

reload();
</script>

<style scoped>
.page-stack{ display:grid; gap:16px; }
</style>
