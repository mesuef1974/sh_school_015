<template>
  <section class="container py-3" dir="rtl">
    <div class="page-stack">
      <WingPageHeader icon="solar:user-circle-bold-duotone" :title="pageTitle" :subtitle="subtitle">
        <template #actions>
          <div class="d-flex align-items-end gap-2 flex-wrap">
            <input v-model.trim="q" @keyup.enter="reload" type="search" class="form-control form-control-sm" placeholder="بحث في وصف/مكان الواقعة" style="min-width:240px" />
            <select v-model="status" class="form-select form-select-sm" style="width:auto" @change="reload">
              <option value="">كل الحالات</option>
              <option value="open">مسودة</option>
              <option value="under_review">قيد المراجعة</option>
              <option value="closed">مغلقة</option>
            </select>
            <button class="btn btn-sm btn-outline-primary" :disabled="loading" @click="reload">تحديث</button>
          </div>
        </template>
      </WingPageHeader>

      <div class="card p-0 mt-3">
        <div class="table-responsive">
          <table class="table table-hover align-middle mb-0">
            <thead class="table-light">
              <tr>
                <th style="width:110px">التاريخ</th>
                <th style="width:90px">الوقت</th>
                <th>الفصل</th>
                <th>المخالفة</th>
                <th style="width:90px">الدرجة</th>
                <th style="width:110px">الحالة</th>
                <th>المكان</th>
                <th>الوصف</th>
                <th>مسجل الواقعة</th>
                <th style="width:80px">لجنة؟</th>
                <th style="width:80px">تصعيد؟</th>
                <th style="width:90px">الإجراءات</th>
                <th style="width:90px">العقوبات</th>
                <th style="width:160px">تم الإرسال</th>
                <th style="width:160px">تمت المراجعة</th>
                <th style="width:160px">تم الإغلاق</th>
                <th style="width:170px">استحقاق المراجعة</th>
                <th style="width:170px">استحقاق الإبلاغ</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!loading && items.length === 0 && !error">
                <td colspan="18" class="text-center text-muted py-4">لا توجد وقائع لهذا الطالب.</td>
              </tr>
              <tr v-for="it in items" :key="it.id">
                <td>{{ fmtDate(it.occurred_at) }}</td>
                <td>{{ it.occurred_time || fmtTime(it.occurred_at) }}</td>
                <td>{{ it.class_name || '—' }}</td>
                <td>
                  <div class="d-flex align-items-center gap-1">
                    <span class="badge rounded-pill" :style="{ backgroundColor: it.level_color || '#6c757d' }">{{ it.violation_code || '—' }}</span>
                    <span class="text-muted">{{ it.violation_category || it.violation_display || '—' }}</span>
                  </div>
                </td>
                <td>
                  <span class="badge" :class="sevBadge(it.severity)">درجة {{ it.severity ?? '—' }}</span>
                </td>
                <td><span class="badge" :class="badgeFor(it.status)">{{ statusAr(it.status) }}</span></td>
                <td>{{ it.location || '—' }}</td>
                <td class="text-muted">{{ it.narrative || '—' }}</td>
                <td>{{ it.reporter_name || '—' }}</td>
                <td>
                  <span class="badge" :class="boolBadge(it.committee_required)">{{ boolAr(it.committee_required) }}</span>
                </td>
                <td>
                  <span class="badge" :class="boolBadge(it.escalated_due_to_repeat)">{{ boolAr(it.escalated_due_to_repeat) }}</span>
                </td>
                <td>
                  <span class="badge bg-secondary">{{ safeNum(it.actions_count) }}</span>
                </td>
                <td>
                  <span class="badge bg-secondary">{{ safeNum(it.sanctions_count) }}</span>
                </td>
                <td>{{ fmtDateTime(it.submitted_at) }}</td>
                <td>
                  <div class="d-flex align-items-center gap-1">
                    <span>{{ fmtDateTime(it.reviewed_at) }}</span>
                    <span v-if="it.is_overdue_review" class="badge bg-danger">متأخرة</span>
                  </div>
                </td>
                <td>{{ fmtDateTime(it.closed_at) }}</td>
                <td>
                  <div class="d-flex align-items-center gap-1">
                    <span>{{ fmtDateTime(it.review_sla_due_at) }}</span>
                    <span v-if="it.is_overdue_review" class="badge bg-danger">متجاوزة</span>
                  </div>
                </td>
                <td>
                  <div class="d-flex align-items-center gap-1">
                    <span>{{ fmtDateTime(it.notify_sla_due_at) }}</span>
                    <span v-if="it.is_overdue_notify" class="badge bg-danger">متجاوزة</span>
                  </div>
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
          <div>عدد الوقائع: {{ items.length }}</div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { useRoute } from 'vue-router';
import WingPageHeader from '../../../components/ui/WingPageHeader.vue';
import { listIncidents, getIncidentsMine } from '../api';
import { useAuthStore } from '../../../app/stores/auth';

const auth = useAuthStore();
const route = useRoute();

const studentId = computed(()=> String(route.params.studentId||''));
const studentName = computed(()=> String((route.query?.name as string) || ''));

const pageTitle = computed(()=> `وقائع الطالب ${studentName.value ? '— ' + studentName.value : ''}`);
const subtitle = computed(()=> `عرض جميع الوقائع المسجلة للطالب رقم #${studentId.value}`);

const items = ref<any[]>([]);
const loading = ref(false);
const error = ref('');
const lastUpdated = ref<string>('');
const status = ref('');
const q = ref('');

const isPrivileged = computed(() => !!(auth.profile?.is_superuser || auth.profile?.is_staff || (auth.profile?.permissions||[]).includes('discipline.access')));

function fmtDate(s?: string){ if(!s) return '—'; try{ const d=new Date(s); const y=d.getFullYear(); const m=String(d.getMonth()+1).padStart(2,'0'); const dd=String(d.getDate()).padStart(2,'0'); return `${y}-${m}-${dd}`; }catch{ return s as string; } }
function fmtTime(s?: string){ if(!s) return '—'; try{ const d=new Date(s); const hh=String(d.getHours()).padStart(2,'0'); const mm=String(d.getMinutes()).padStart(2,'0'); return `${hh}:${mm}`; }catch{ return ''; } }
function badgeFor(st: string){ return st==='closed'?'bg-secondary':(st==='under_review'?'bg-warning text-dark':'bg-info'); }
function sevBadge(sev?: number){ const s=Number(sev||1); return s>=4?'bg-danger':(s===3?'bg-warning text-dark':(s===2?'bg-primary':'bg-secondary')); }
function statusAr(st: string){ return st==='closed'?'مغلقة':(st==='under_review'?'قيد المراجعة':'مسودة'); }
function fmtDateTime(s?: string){ if(!s) return '—'; try{ const d=new Date(s); const y=d.getFullYear(); const m=String(d.getMonth()+1).padStart(2,'0'); const dd=String(d.getDate()).padStart(2,'0'); const hh=String(d.getHours()).padStart(2,'0'); const mm=String(d.getMinutes()).padStart(2,'0'); return `${y}-${m}-${dd} ${hh}:${mm}`; }catch{ return s as string; } }
function boolAr(v: any){ return v ? 'نعم' : 'لا'; }
function boolBadge(v: any){ return v ? 'bg-success' : 'bg-secondary'; }
function safeNum(v: any){ const n = Number(v); return Number.isFinite(n) ? n : 0; }

async function reload(){
  loading.value = true; error.value=''; items.value=[];
  const ac = new AbortController();
  const timeout = setTimeout(()=> ac.abort(), 10000);
  try{
    const params:any = { page_size: 200, student: studentId.value };
    if (status.value) params.status = status.value;
    if (q.value) params.search = q.value;
    let data: any;
    if (!isPrivileged.value) {
      data = await getIncidentsMine(params, { signal: ac.signal });
    } else {
      data = await listIncidents(params, { signal: ac.signal });
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

watch(()=> studentId.value, reload, { immediate: true });
</script>

<style scoped>
.page-stack{ display:grid; gap:16px; }
</style>
