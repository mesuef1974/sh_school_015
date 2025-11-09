<template>
  <section class="container py-3" dir="rtl">
    <div class="page-stack">
      <WingPageHeader :icon="tileMeta.icon" :title="titleBar" :color="sevColor" :subtitle="subtitleBar">
        <template #actions>
          <div class="d-flex flex-wrap gap-2">
            <button v-if="it && it.status==='open'" class="btn btn-primary" :disabled="busy" @click="onSubmit">إرسال للمراجعة</button>
            <button v-if="it && it.status==='under_review'" class="btn btn-outline-success" :disabled="busy" @click="onReview">اعتماد المراجعة</button>
            <button v-if="it && it.status!=='closed'" class="btn btn-outline-warning" :disabled="busy" @click="onEscalate">تصعيد</button>
            <button v-if="it && it.status==='under_review'" class="btn btn-outline-info" :disabled="busy" @click="onNotify">إشعار ولي الأمر</button>
            <button v-if="it && it.status!=='closed'" class="btn btn-outline-secondary" :disabled="busy" @click="onClose">إغلاق</button>
            <button class="btn btn-outline-dark" :disabled="loading" @click="reload">تحديث</button>
          </div>
        </template>
      </WingPageHeader>

      <div class="row g-3">
        <div class="col-lg-8 col-12">
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
          </div>

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