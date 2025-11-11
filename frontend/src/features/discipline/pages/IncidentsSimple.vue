<template>
  <section class="container py-3" dir="rtl">
    <div class="page-stack">
      <header class="d-flex align-items-center justify-content-between flex-wrap gap-2">
        <div>
          <h2 class="h5 mb-1">وقائع الانضباط (واجهة مبسطة)</h2>
          <div class="text-muted small">صفحة مبسطة تم إنشاؤها من الصفر وتستدعي البيانات من قاعدة البيانات عبر واجهة الـ API</div>
        </div>
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
      </header>

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
                <th>الشدة</th>
                <th>الحالة</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!loading && items.length === 0 && !error">
                <td colspan="7" class="text-center text-muted py-4">لا توجد بيانات لعرضها</td>
              </tr>
              <tr v-for="it in items" :key="it.id">
                <td>{{ fmtDate(it.occurred_at) }}</td>
                <td>{{ it.occurred_time || fmtTime(it.occurred_at) }}</td>
                <td>{{ it.class_name || '—' }}</td>
                <td>{{ it.violation_display || it.violation?.code || '—' }}</td>
                <td>{{ it.student_name || ('#'+it.student) }}</td>
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
import { ref, computed } from 'vue';
import { listIncidents, getIncidentsMine } from '../api';
import { useAuthStore } from '../../../app/stores/auth';

const auth = useAuthStore();
const items = ref<any[]>([]);
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

function exportCsv(){
  try{
    const headers = ['id','occurred_at','violation','student','severity','status'];
    const rows = items.value.map((it:any)=>[
      it.id,
      it.occurred_at || '',
      (it.violation_display || it.violation?.code || ''),
      (it.student_name || it.student || ''),
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
