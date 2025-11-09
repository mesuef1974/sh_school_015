<template>
  <section class="container py-3" dir="rtl">
    <div class="page-stack">
      <header class="d-flex align-items-center justify-content-between">
        <div>
          <h2 class="h5 mb-1">وقائع الانضباط (واجهة مبسطة)</h2>
          <div class="text-muted small">صفحة مبسطة تم إنشاؤها من الصفر وتستدعي البيانات من قاعدة البيانات عبر واجهة الـ API</div>
        </div>
        <div class="d-flex align-items-end gap-2">
          <select v-model="status" class="form-select form-select-sm" style="width:auto" @change="reload">
            <option value="">كل الحالات</option>
            <option value="open">مسودة</option>
            <option value="under_review">قيد المراجعة</option>
            <option value="closed">مغلقة</option>
          </select>
          <button class="btn btn-sm btn-outline-primary" :disabled="loading" @click="reload">تحديث</button>
        </div>
      </header>

      <div class="card p-0 mt-3">
        <div class="table-responsive">
          <table class="table table-hover align-middle mb-0">
            <thead class="table-light">
              <tr>
                <th>التاريخ</th>
                <th>المخالفة</th>
                <th>الطالب</th>
                <th>الشدة</th>
                <th>الحالة</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!loading && items.length === 0 && !error">
                <td colspan="5" class="text-center text-muted py-4">لا توجد بيانات لعرضها</td>
              </tr>
              <tr v-for="it in items" :key="it.id">
                <td>{{ fmtDate(it.occurred_at) }}</td>
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
          <div>حجم الصفحة: {{ pageSize }}</div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { listIncidents, getIncidentsMine } from '../api';
import { useAuthStore } from '../../../app/stores/auth';

const auth = useAuthStore();
const items = ref<any[]>([]);
const loading = ref(false);
const error = ref('');
const lastUpdated = ref<string>('');
const status = ref('');
const pageSize = 25;

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
    const privileged = !!(auth.profile?.is_superuser || auth.profile?.is_staff || (auth.profile?.permissions||[]).includes('discipline.access'));
    // المعلم يرى سجلاته فقط افتراضيًا؛ المميز يرى الكل افتراضيًا
    const data = privileged ? await listIncidents(params, { signal: ac.signal })
                            : await getIncidentsMine(params, { signal: ac.signal });
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

reload();
</script>

<style scoped>
.page-stack{ display:grid; gap:16px; }
</style>