<template>
  <section class="container py-3" dir="rtl">
    <div class="page-stack">
      <WingPageHeader :icon="tileMeta.icon" :title="tileMeta.title" :color="tileMeta.color" :subtitle="tileMeta.subtitle">
        <template #actions>
          <div class="d-flex align-items-center gap-2">
            <button class="btn btn-outline-primary" :disabled="loading" @click="reload">تحديث</button>
            <button class="btn btn-primary" @click="$router.push({name:'discipline-incident-new'})">تسجيل واقعة</button>
          </div>
        </template>
      </WingPageHeader>

      <div class="card p-3">
        <div class="row g-3 align-items-end">
        <div class="col-md-3 col-12">
          <label class="form-label">الحالة</label>
          <select v-model="status" class="form-select" @change="reload">
            <option value="">الكل</option>
            <option value="open">مسودة (open)</option>
            <option value="under_review">قيد المراجعة</option>
            <option value="closed">مغلقة</option>
          </select>
        </div>
        <div class="col-md-6 col-12">
          <label class="form-label">بحث</label>
          <input v-model.trim="q" @input="onSearchInput" type="search" class="form-control" placeholder="بحث بالوصف/المكان/المخالفة" />
        </div>
        <div class="col-md-3 col-12">
          <label class="form-label">الحالة العامة</label>
          <div class="small" :class="error? 'text-danger':'text-muted'">
            <span v-if="loading">جاري التحميل …</span>
            <span v-else-if="error">{{ error }}</span>
            <span v-else>آخر تحديث: {{ lastUpdated || '—' }}</span>
          </div>
        </div>
      </div>
    </div>

    <div class="card p-0 mt-3">
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead class="table-light">
            <tr>
              <th>التاريخ</th>
              <th>الكود/المخالفة</th>
              <th>الطالب</th>
              <th>الشدة</th>
              <th>لجنة؟</th>
              <th>الموقع</th>
              <th>وصف مختصر</th>
              <th>الحالة</th>
              <th>إجراءات/عقوبات</th>
              <th>المُبلّغ</th>
              <th style="width:160px">عمليات</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!loading && items.length===0">
              <td :colspan="11" class="text-center text-muted py-4">لا توجد سجلات مطابقة للمعايير الحالية</td>
            </tr>
            <tr v-for="it in items" :key="it.id">
              <td>{{ fmtDate(it.occurred_at) }}</td>
              <td><strong>{{ it.violation_display || it.violation?.code || '—' }}</strong></td>
              <td>{{ it.student_name || ('#'+it.student) }}</td>
              <td><span class="badge bg-secondary">{{ it.severity ?? '—' }}</span></td>
              <td>
                <span class="badge" :class="it.committee_required ? 'bg-danger' : 'bg-success'">{{ it.committee_required? 'نعم':'لا' }}</span>
              </td>
              <td>{{ it.location || '—' }}</td>
              <td :title="it.narrative || ''">{{ truncate(it.narrative, 60) }}</td>
              <td>
                <span class="badge" :class="badgeFor(it.status)">{{ statusAr(it.status) }}</span>
              </td>
              <td>
                <span class="badge bg-outline-primary text-primary me-1">إج {{ it.actions_count ?? 0 }}</span>
                <span class="badge bg-outline-warning text-warning">عق {{ it.sanctions_count ?? 0 }}</span>
              </td>
              <td>{{ it.reporter_name || '—' }}</td>
              <td>
                <button class="btn btn-sm btn-outline-success" v-if="it.status==='open'" :disabled="busyId===it.id" @click="send(it.id)">إرسال للمراجعة</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="loading" class="p-3 text-muted">جاري التحميل …</div>
      <div v-if="!loading && error" class="p-3 text-danger border-top">{{ error }}
        <button class="btn btn-sm btn-outline-secondary ms-2" @click="reload">محاولة مجددًا</button>
      </div>
    </div>
    </div>
  </section>
</template>
<script setup lang="ts">
import { ref, computed } from 'vue';
import WingPageHeader from '../../../components/ui/WingPageHeader.vue';
import { tiles } from '../../../home/icon-tiles.config';
import { listIncidents, submitIncident } from '../api';
import { useAuthStore } from '../../../app/stores/auth';

const tileMeta = computed(()=> tiles.find(t=> t.to === '/discipline/incidents') || ({ title: 'وقائع المعلم', subtitle: 'سجلاتي والإرسال للمراجعة', icon: 'solar:document-text-bold-duotone', color: '#2e86c1' } as any));

const auth = useAuthStore();
const items = ref<any[]>([]);
const loading = ref(false);
const status = ref('');
const q = ref('');
const error = ref('');
const lastUpdated = ref<string>('');
const busyId = ref<string| null>(null);
let timer:any = null;

async function reload(){
  loading.value = true; items.value = []; error.value='';
  try{
    const params:any = {};
    if (status.value) params.status = status.value; // server-side status filter
    if (q.value) params.search = q.value;
    const data = await listIncidents(params);
    items.value = data?.results ?? data ?? [];
    lastUpdated.value = new Date().toLocaleString();
  } catch(e:any){
    error.value = e?.message || 'تعذّر تحميل البيانات';
  } finally {
    loading.value = false;
  }
}

function onSearchInput(){ clearTimeout(timer); timer = setTimeout(reload, 300); }

async function send(id: string){
  try{
    busyId.value = id;
    await submitIncident(id);
    await reload();
  }finally{
    busyId.value = null;
  }
}

function fmtDate(s?: string){ if(!s) return '—'; try{ const d=new Date(s); const y=d.getFullYear(); const m=String(d.getMonth()+1).padStart(2,'0'); const dd=String(d.getDate()).padStart(2,'0'); return `${y}-${m}-${dd}`; }catch{ return s as string; } }
function badgeFor(st: string){ return st==='closed'?'bg-secondary':(st==='under_review'?'bg-warning text-dark':'bg-info'); }
function statusAr(st: string){ return st==='closed'?'مغلقة':(st==='under_review'?'قيد المراجعة':'مسودة'); }

reload();
</script>
<style scoped>
.page-stack{ display:grid; gap:16px; }
</style>