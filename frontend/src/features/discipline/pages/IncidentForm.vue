<template>
  <section class="container py-3" dir="rtl">
    <div class="page-stack">
      <WingPageHeader :icon="tileMeta.icon" :title="tileMeta.title" :color="tileMeta.color" :subtitle="tileMeta.subtitle" />

      <div class="card p-3">
        <div class="row g-3">
        <div class="col-md-4 col-12">
          <label class="form-label">المخالفة</label>
          <select v-model.number="form.violation" class="form-select" :disabled="loading">
            <option :value="0">— اختر —</option>
            <option v-for="v in violations" :key="v.id" :value="v.id">{{ v.code }} — {{ v.category }}</option>
          </select>
          <div v-if="selectedViolation" class="form-text">
            <div><strong>إجراءات افتراضية:</strong> {{ (selectedViolation.default_actions||[]).join('، ') || '—' }}</div>
            <div><strong>عقوبات افتراضية:</strong> {{ (selectedViolation.default_sanctions||[]).join('، ') || '—' }}</div>
          </div>
        </div>

        <div class="col-md-4 col-12">
          <label class="form-label">التاريخ</label>
          <input v-model="date" type="date" class="form-control" :disabled="loading" @change="onDateChange" />
        </div>
        <div class="col-md-4 col-12">
          <label class="form-label">الحصة</label>
          <select v-model.number="selectedPeriod" class="form-select" :disabled="loading || periods.length===0" @change="onPeriodChange">
            <option :value="0">— خارج الحصص —</option>
            <option v-for="p in periods" :key="p.period_number" :value="p.period_number">
              الحصة {{ p.period_number }} — {{ p.classroom_name || ('#'+p.classroom_id) }} — {{ p.subject_name || '' }} ({{ p.start_time || '' }}
              {{ p.end_time ? ('→ '+p.end_time) : '' }})
            </option>
          </select>
          <div class="form-text" v-if="periods.length===0">لا توجد حصص لهذا اليوم.</div>
        </div>

        <div class="col-md-4 col-12">
          <label class="form-label">الصف</label>
          <select v-model.number="form.class_id" class="form-select" :disabled="loading || classes.length===0" @change="onClassChange">
            <option :value="0">— اختر —</option>
            <option v-for="c in classes" :key="c.id" :value="c.id">{{ c.name || ('#'+c.id) }}</option>
          </select>
          <div class="form-text" v-if="classes.length===0">لا توجد لديك صفوف مسندة.</div>
        </div>

        <div class="col-md-4 col-12">
          <label class="form-label">الطالب</label>
          <select v-model.number="form.student" class="form-select" :disabled="loading || rosterLoading || roster.length===0">
            <option :value="0">— اختر —</option>
            <option v-for="s in roster" :key="s.id" :value="s.id">{{ s.full_name || ('#'+s.id) }}</option>
          </select>
          <div class="form-text" v-if="rosterLoading">جاري تحميل طلاب الصف …</div>
          <div class="form-text text-danger" v-else-if="rosterError">{{ rosterError }}</div>
          <div class="form-text" v-else-if="form.class_id && roster.length===0">لا يوجد طلاب لهذا الصف/التاريخ.</div>
        </div>

        <div class="col-md-4 col-12">
          <label class="form-label">وقت الحادثة</label>
          <input v-model="form.occurred_at" type="datetime-local" class="form-control" :disabled="loading" />
        </div>
        <div class="col-md-6 col-12">
          <label class="form-label">المكان</label>
          <input v-model.trim="form.location" type="text" class="form-control" placeholder="مثال: الصف 6" :disabled="loading" />
        </div>
        <div class="col-12">
          <label class="form-label">الوصف</label>
          <textarea v-model.trim="form.narrative" rows="4" class="form-control" placeholder="سرد مختصر" :disabled="loading"></textarea>
        </div>
      </div>
      <div class="d-flex align-items-center gap-2 mt-3">
        <button class="btn btn-primary" :disabled="loading || !canSubmit" @click="onSubmit">حفظ</button>
        <span class="small" :class="msgClass" aria-live="polite">{{ msg }}</span>
      </div>
    </div>
    </div>
  </section>
</template>
<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import WingPageHeader from '../../../components/ui/WingPageHeader.vue';
import { tiles } from '../../../home/icon-tiles.config';
import { createIncident, listViolations } from '../api';
import { useAuthStore } from '../../../app/stores/auth';
import { useRouter } from 'vue-router';
import { getTeacherClasses, getTeacherTimetableToday, getClassStudents } from '../../../shared/api/client';

const tileMeta = computed(()=> tiles.find(t=> t.to === '/discipline/incidents/new') || ({ title: 'تسجيل واقعة', subtitle: 'إدخال واقعة سلوكية جديدة', icon: 'solar:add-square-bold-duotone', color: '#27ae60' } as any));

const auth = useAuthStore();
const router = useRouter();

const violations = ref<any[]>([]);
const loading = ref(false);
const msg = ref('');
const msgClass = computed(()=> msg.value.includes('فشل')? 'text-danger':'text-success');

// Teacher context
const classes = ref<{id:number; name?:string}[]>([]);
const periods = ref<{period_number:number; classroom_id:number; classroom_name?:string; subject_name?:string; start_time?:string; end_time?:string}[]>([]);
const roster = ref<{id:number; full_name?:string|null}[]>([]);
const rosterLoading = ref(false);
const rosterError = ref('');

// Date and period selectors
const todayIso = () => new Date().toISOString().slice(0,10);
const date = ref<string>(todayIso());
const selectedPeriod = ref<number>(0);

const nowIsoLocal = () => {
  const d = new Date();
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0,16);
};

const form = ref({
  violation: 0,
  class_id: 0 as number,
  student: 0 as number,
  reporter: undefined as any,
  occurred_at: nowIsoLocal(),
  location: '',
  narrative: '',
});

const selectedViolation = computed(()=> violations.value.find(v=> v.id===form.value.violation));

const canSubmit = computed(()=> form.value.violation>0 && !!form.value.student && !!form.value.occurred_at);

async function loadViolations(){
  const data = await listViolations();
  const results = data?.results ?? data ?? [];
  violations.value = results;
}

async function loadTeacherClasses(){
  try{
    const res = await getTeacherClasses();
    classes.value = res.classes || [];
  }catch{ classes.value = []; }
}

async function loadTimetable(){
  try{
    const res = await getTeacherTimetableToday({ date: date.value });
    periods.value = res.periods || [];
  }catch{ periods.value = []; }
}

async function loadRoster(){
  rosterLoading.value = true; rosterError.value=''; roster.value = [];
  if (!form.value.class_id){ rosterLoading.value=false; return; }
  try{
    const res = await getClassStudents({ class_id: form.value.class_id, date: date.value });
    roster.value = res.students || [];
    if (!Array.isArray(roster.value)) roster.value = [] as any;
  }catch(e:any){
    roster.value = [];
    const detail = e?.response?.data?.detail || e?.message || '';
    // Friendly Arabic messages for common cases
    if (typeof detail === 'string' && /not allowed/i.test(detail)) {
      rosterError.value = 'لا تملك صلاحية للوصول إلى هذا الصف.';
    } else if (typeof detail === 'string') {
      rosterError.value = detail;
    } else {
      rosterError.value = 'تعذّر تحميل طلاب الصف.';
    }
  } finally {
    rosterLoading.value = false;
  }
}

function onDateChange(){
  // Refresh timetable and roster when date changes
  loadTimetable();
  if (form.value.class_id) loadRoster();
}

function onPeriodChange(){
  const p = periods.value.find(x=> x.period_number === selectedPeriod.value);
  if (p){
    // Prefill class and location from selected period
    form.value.class_id = p.classroom_id;
    if (!form.value.location){ form.value.location = p.classroom_name || ''; }
    // If the period has times, prefill occurred_at to the midpoint of the lesson time on the selected date
    try{
      if (p.start_time && p.end_time && date.value){
        const [sh, sm] = String(p.start_time).split(':').map(x=> parseInt(x,10));
        const [eh, em] = String(p.end_time).split(':').map(x=> parseInt(x,10));
        // Build Date objects in local time
        const start = new Date(date.value + 'T00:00');
        start.setHours(isFinite(sh)?sh:0, isFinite(sm)?sm:0, 0, 0);
        const end = new Date(date.value + 'T00:00');
        end.setHours(isFinite(eh)?eh:0, isFinite(em)?em:0, 0, 0);
        const midMs = start.getTime() + Math.floor((end.getTime() - start.getTime())/2);
        const mid = new Date(midMs);
        // Normalize to input type="datetime-local" expected format (local without timezone)
        const d = new Date(mid);
        d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
        form.value.occurred_at = d.toISOString().slice(0,16);
      }
    }catch{ /* ignore prefill errors */ }
    loadRoster();
  }
}

function onClassChange(){
  // When class changes manually, refresh roster and set location if empty
  const c = classes.value.find(x=> x.id===form.value.class_id);
  if (c && !form.value.location){ form.value.location = c.name || ''; }
  loadRoster();
}

async function onSubmit(){
  if (!canSubmit.value) return;
  try{
    loading.value = true; msg.value = '';
    const payload = {
      violation: form.value.violation,
      student: form.value.student,
      occurred_at: new Date(form.value.occurred_at).toISOString(),
      location: form.value.location || (classes.value.find(c=>c.id===form.value.class_id)?.name || ''),
      narrative: form.value.narrative,
    };
    // Optionally include class/period to help backend validate and fix subject
    if (form.value.class_id){
      (payload as any).class_id = form.value.class_id;
    }
    if (selectedPeriod.value && selectedPeriod.value > 0){
      (payload as any).period_number = selectedPeriod.value;
    }
    await createIncident(payload);
    msg.value = 'تم الحفظ بنجاح';
    router.push({ name: 'discipline-incidents' });
  }catch(e:any){
    const detail = e?.response?.data?.detail || e?.message || '';
    msg.value = detail ? `فشل الحفظ: ${detail}` : 'فشل الحفظ';
  }finally{
    loading.value = false;
  }
}

onMounted(async()=>{
  await Promise.all([loadViolations(), loadTeacherClasses(), loadTimetable()]);
});

watch(date, onDateChange);
</script>
<style scoped>
.page-stack{ display:grid; gap:16px; }
.form-text{ font-size: 0.85rem; }
</style>
