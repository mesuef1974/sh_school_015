<template>
  <section class="d-grid gap-3 page-grid">
    <header class="auto-card p-3 d-flex align-items-center gap-3 glass-header">
      <Icon icon="fa6-solid:clipboard-check" class="header-icon" />
      <div>
        <div class="fw-bold">تسجيل الغياب</div>
        <div class="text-muted small">اختر الصف والتاريخ (اختياري: حصة اليوم)</div>
      </div>
      <span class="ms-auto"></span>
    </header>

    <form @submit.prevent="loadData" class="toolbar-inline mb-3 glass-form p-3">
      <div class="field-inline">
        <label class="form-label mb-0">الصف:</label>
        <select v-model.number="classId" required class="form-select">
          <option :value="null" disabled>اختر الصف</option>
          <option v-for="c in classes" :key="c.id" :value="c.id">{{ c.name || ('صف #' + c.id) }}</option>
        </select>
      </div>
      <div class="field-inline">
        <label class="form-label mb-0">التاريخ:</label>
        <input type="date" v-model="dateStr" class="form-control" @change="onDateChange" />
      </div>
      <div class="field-inline">
        <label class="form-label mb-0">حصة اليوم:</label>
        <select v-model.number="periodNo" class="form-select" @change="onPickPeriod">
          <option :value="null">— لا شيء —</option>
          <option v-for="p in todayPeriods" :key="p.period_number" :value="p.period_number">
            حصة {{ p.period_number }} — {{ p.subject_name || 'مادة' }} — {{ p.classroom_name || ('صف #' + p.classroom_id) }}
          </option>
        </select>
      </div>
      <button type="submit" class="btn btn-maron">تحميل</button>
      <button type="button" class="btn btn-maron-outline" :disabled="!students.length" @click="setAll('present')">تعيين الجميع حاضر</button>
      <button type="button" class="btn btn-outline-secondary" :disabled="!students.length" @click="setAll('absent')">تعيين الجميع غائب</button>
      <button type="button" class="btn btn-maron" :disabled="saving || !students.length" @click="save">حفظ</button>
    </form>

    <div v-if="loading" class="loader-line"></div>
    <div v-else>
      <div v-if="classId || students.length" class="auto-card p-3 mb-3">
        <div class="d-flex align-items-center mb-2">
          <div class="fw-bold">معلومات اليوم</div>
          <span class="ms-auto"></span>
          <span class="small text-muted">{{ dateStr }}</span>
        </div>
        <div class="chips-grid">
          <span class="chip">الحضور: <strong>{{ classKpis.present_pct ?? '--' }}%</strong></span>
          <span class="chip">حاضر {{ classKpis.present ?? 0 }} / {{ classKpis.total ?? 0 }}</span>
          <span class="chip">غياب: {{ classKpis.absent ?? 0 }}</span>
          <span class="chip">متأخر: {{ classKpis.late ?? 0 }}</span>
          <span class="chip">هروب: {{ classKpis.runaway ?? 0 }}</span>
          <span class="chip">إذن خروج: {{ classKpis.excused ?? 0 }}</span>
        </div>
      </div>
      <div v-if="students.length === 0" class="auto-card p-3">لا يوجد طلاب.</div>
      <div v-else class="students-two-col">
        <div class="auto-card p-0">
          <div class="table-responsive">
            <table class="table table-hover table-card align-middle mb-0">
              <thead>
                <tr>
                  <th style="width:60px">#</th>
                  <th>الطالب</th>
                  <th style="width:180px">الحالة</th>
                  <th>ملاحظة</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(s, idx) in studentsLeft" :key="s.id">
                  <td>{{ idx + 1 }}</td>
                  <td>{{ s.full_name }}</td>
                  <td>
                    <select v-model="recordMap[s.id].status" class="form-select">
                      <option value=""></option>
                      <option value="present">حاضر</option>
                      <option value="absent">غائب</option>
                      <option value="late">متأخر</option>
                      <option value="excused">إذن خروج</option>
                      <option value="runaway">هروب</option>
                      <option value="left_early">انصراف مبكر</option>
                    </select>
                  </td>
                  <td>
                    <div v-if="recordMap[s.id].status === 'excused'" class="d-flex flex-wrap gap-3 align-items-center">
                      <label class="form-check form-check-inline m-0">
                        <input class="form-check-input" type="radio" :name="'exit-'+s.id" value="admin" v-model="recordMap[s.id].exit_reasons" />
                        <span class="form-check-label">إدارة</span>
                      </label>
                      <label class="form-check form-check-inline m-0">
                        <input class="form-check-input" type="radio" :name="'exit-'+s.id" value="wing" v-model="recordMap[s.id].exit_reasons" />
                        <span class="form-check-label">مشرف الجناح</span>
                      </label>
                      <label class="form-check form-check-inline m-0">
                        <input class="form-check-input" type="radio" :name="'exit-'+s.id" value="nurse" v-model="recordMap[s.id].exit_reasons" />
                        <span class="form-check-label">الممرض</span>
                      </label>
                      <label class="form-check form-check-inline m-0">
                        <input class="form-check-input" type="radio" :name="'exit-'+s.id" value="restroom" v-model="recordMap[s.id].exit_reasons" />
                        <span class="form-check-label">حمام</span>
                      </label>
                    </div>
                    <div v-else>
                      <input type="text" v-model="recordMap[s.id].note" placeholder="اختياري" class="form-control" />
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div class="auto-card p-0">
          <div class="table-responsive">
            <table class="table table-hover table-card align-middle mb-0">
              <thead>
                <tr>
                  <th style="width:60px">#</th>
                  <th>الطالب</th>
                  <th style="width:180px">الحالة</th>
                  <th>ملاحظة</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(s, idx) in studentsRight" :key="s.id">
                  <td>{{ idx + leftCount + 1 }}</td>
                  <td>{{ s.full_name }}</td>
                  <td>
                    <select v-model="recordMap[s.id].status" class="form-select">
                      <option value=""></option>
                      <option value="present">حاضر</option>
                      <option value="absent">غائب</option>
                      <option value="late">متأخر</option>
                      <option value="excused">إذن خروج</option>
                      <option value="runaway">هروب</option>
                      <option value="left_early">انصراف مبكر</option>
                    </select>
                  </td>
                  <td>
                    <div v-if="recordMap[s.id].status === 'excused'" class="d-flex flex-wrap gap-3 align-items-center">
                      <label class="form-check form-check-inline m-0">
                        <input class="form-check-input" type="radio" :name="'exit-'+s.id" value="admin" v-model="recordMap[s.id].exit_reasons" />
                        <span class="form-check-label">إدارة</span>
                      </label>
                      <label class="form-check form-check-inline m-0">
                        <input class="form-check-input" type="radio" :name="'exit-'+s.id" value="wing" v-model="recordMap[s.id].exit_reasons" />
                        <span class="form-check-label">مشرف الجناح</span>
                      </label>
                      <label class="form-check form-check-inline m-0">
                        <input class="form-check-input" type="radio" :name="'exit-'+s.id" value="nurse" v-model="recordMap[s.id].exit_reasons" />
                        <span class="form-check-label">الممرض</span>
                      </label>
                      <label class="form-check form-check-inline m-0">
                        <input class="form-check-input" type="radio" :name="'exit-'+s.id" value="restroom" v-model="recordMap[s.id].exit_reasons" />
                        <span class="form-check-label">حمام</span>
                      </label>
                    </div>
                    <div v-else>
                      <input type="text" v-model="recordMap[s.id].note" placeholder="اختياري" class="form-control" />
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
      <div class="sticky-actions d-flex align-items-center gap-3 p-2 border-top">
        <span v-if="saveMsg" class="msg">{{ saveMsg }}</span>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, computed } from 'vue';
import { getAttendanceStudents, getAttendanceRecords, postAttendanceBulkSave, getTeacherClasses, getTeacherTimetableToday, getAttendanceSummary } from '../../../shared/api/client';
import { useToast } from 'vue-toastification';

const toast = useToast();
const today = new Date().toISOString().slice(0, 10);
const classId = ref<number | null>(null);
const dateStr = ref<string>(today);
const loading = ref(false);
const saving = ref(false);
const saveMsg = ref('');

// Class/day summary KPIs
const classSummary = ref<{ kpis?: any } | null>(null);
const classKpis = computed(() => classSummary.value?.kpis || { present_pct: null, present: 0, total: 0, absent: 0, late: 0, excused: 0 });

// Today periods for the teacher
const todayPeriods = ref<{ period_number:number; classroom_id:number; classroom_name?:string; subject_id:number; subject_name?:string }[]>([]);
const periodNo = ref<number | null>(null);

interface StudentBrief { id: number; first_name: string; last_name: string; }
interface Rec { student_id: number; status: '' | 'present' | 'absent' | 'late' | 'excused' | 'runaway' | 'left_early'; note?: string | null; exit_reasons?: string }

const classes = ref<{ id: number; name?: string }[]>([]);
const students = ref<StudentBrief[]>([]);
const recordMap = reactive<Record<number, Rec>>({});

const totalStudents = computed(() => students.value.length);
const presentCount = computed(() => Object.values(recordMap).filter(r => r.status === 'present').length);
const absentCount = computed(() => Object.values(recordMap).filter(r => r.status === 'absent').length);
const lateCount = computed(() => Object.values(recordMap).filter(r => r.status === 'late').length);
const runawayCount = computed(() => Object.values(recordMap).filter(r => r.status === 'runaway').length);
const excusedCount = computed(() => Object.values(recordMap).filter(r => r.status === 'excused').length);

// Split students into two nearly equal columns
const leftCount = computed(() => Math.ceil(students.value.length / 2));
const studentsLeft = computed(() => students.value.slice(0, leftCount.value));
const studentsRight = computed(() => students.value.slice(leftCount.value));

function setAll(st: ''|'present'|'absent'|'late'|'excused'|'runaway'|'left_early') {
  for (const s of students.value) {
    if (recordMap[s.id]) recordMap[s.id].status = st;
  }
}

const collator = new Intl.Collator('ar');

async function loadData() {
  await loadClassSummary();
  if (periodNo.value) {
    // If period picked, ensure class matches the selected period
    const p = todayPeriods.value.find(pp => pp.period_number === periodNo.value);
    if (p) {
      classId.value = p.classroom_id;
    }
  }
  if (!classId.value) return;
  loading.value = true;
  saveMsg.value = '';
  try {
    const [sres, rres] = await Promise.all([
      getAttendanceStudents({ class_id: classId.value, date: dateStr.value }),
      getAttendanceRecords({ class_id: classId.value, date: dateStr.value, period_number: periodNo.value ?? null })
    ]);
    // Arabic ascending sort by full_name
    students.value = [...sres.students].sort((a: any, b: any) => {
      return collator.compare(a.full_name || '', b.full_name || '');
    });
    // reset map
    for (const k of Object.keys(recordMap)) delete (recordMap as any)[k];
    for (const st of students.value) {
      (recordMap as any)[st.id] = { student_id: st.id, status: '', note: '', exit_reasons: '' };
    }
    for (const r of rres.records) {
      const eraw: any = (r as any).exit_reasons;
      const ereason = Array.isArray(eraw)
        ? (eraw[0] || '')
        : (typeof eraw === 'string' ? eraw : '');
      const prev = (recordMap as any)[r.student_id];
      if (!prev) {
        (recordMap as any)[r.student_id] = { student_id: r.student_id, status: r.status, note: r.note ?? '', exit_reasons: ereason };
      } else {
        // Prefer showing 'إذن خروج' if any period for the day has it; else keep existing non-empty status
        const priority = (s: string) => (s === 'excused' ? 3 : s === 'late' || s === 'absent' ? 2 : s ? 1 : 0);
        const pickExisting = priority(prev.status) >= priority(r.status);
        if (pickExisting) {
          // Keep previous, but if previous was excused and current carries a reason, merge reason if missing
          if (prev.status === 'excused' && !prev.exit_reasons && ereason) prev.exit_reasons = ereason;
        } else {
          (recordMap as any)[r.student_id] = { student_id: r.student_id, status: r.status, note: r.note ?? '', exit_reasons: ereason };
        }
      }
    }
  } catch (e: any) {
    const msg = e?.response?.data?.detail || 'حدث خطأ أثناء التحميل';
    saveMsg.value = msg;
    try { toast.error(msg, { autoClose: 3500 }); } catch {}
  } finally {
    loading.value = false;
  }
}

async function save() {
  if (!classId.value) return;
  // If there are multiple possible periods today for this class/date, require selecting one to avoid backend ambiguity
  const manyPeriods = Array.isArray(todayPeriods.value) && todayPeriods.value.length > 1;
  if (manyPeriods && !periodNo.value) {
    const msg = 'يرجى اختيار الحصة قبل الحفظ لتجنب التعارض.';
    saveMsg.value = msg;
    try { toast.warning(msg, { autoClose: 3500 }); } catch {}
    return;
  }
  saving.value = true;
  saveMsg.value = '';
  try {
    const base = Object.values(recordMap).filter(r => !!r.status);
    // Validation: require one reason when status is 'excused'
    const missing = base.filter(r => r.status === 'excused' && (!r.exit_reasons || String(r.exit_reasons).trim() === ''));
    if (missing.length) {
      const msg = 'يجب اختيار سبب واحد لإذن الخروج لكل طالب تم تعيين حالته "إذن خروج"';
      saveMsg.value = msg;
      try { toast.error(msg, { autoClose: 3500 }); } catch {}
      return;
    }
    const records = base.map(r => ({
      student_id: r.student_id,
      status: r.status,
      note: r.status === 'excused' ? null : (r.note ?? ''),
      exit_reasons: r.status === 'excused' ? (r.exit_reasons as any) : undefined,
    }));
    const res = await postAttendanceBulkSave({ class_id: classId.value, date: dateStr.value, period_number: periodNo.value ?? undefined as any, records });
    const queued = (res as any)?.queued;
    const msg = queued ? `تمت جدولة الحفظ (${records.length}) — سيتم المزامنة عند توفر الاتصال` : `تم الحفظ (${res.saved})`;
    saveMsg.value = msg;
    try {
      if (queued) toast.info(msg, { autoClose: 3500 }); else toast.success(msg, { autoClose: 2500 });
    } catch {}
    // Reload to reflect persisted records (and computed counters)
    await loadData();
  } catch (e: any) {
    const msg = e?.response?.data?.detail || 'تعذر الحفظ';
    saveMsg.value = msg;
    try { toast.error(msg, { autoClose: 3500 }); } catch {}
  } finally {
    saving.value = false;
  }
}

async function loadClasses() {
  try {
    const res = await getTeacherClasses();
    classes.value = res.classes || [];
    if (!classId.value && classes.value.length) {
      classId.value = classes.value[0].id;
    }
  } catch (e: any) {
    // Non-fatal; user can still enter manually if no classes available (but dropdown requires a value)
    classes.value = [];
  }
}

async function loadTodayPeriods() {
  await loadClassSummary();
  try {
    const res = await getTeacherTimetableToday({ date: dateStr.value });
    todayPeriods.value = res.periods || [];
  } catch {
    todayPeriods.value = [];
  }
}

async function loadClassSummary() {
  try {
    if (!classId.value) { classSummary.value = null; return; }
    const res = await getAttendanceSummary({ class_id: classId.value, date: dateStr.value });
    classSummary.value = res;
  } catch {
    classSummary.value = { kpis: { present_pct: null, present: 0, total: 0, absent: 0, late: 0, excused: 0 } } as any;
  }
}

async function onPickPeriod() {
  if (!periodNo.value) return;
  const p = todayPeriods.value.find(pp => pp.period_number === periodNo.value);
  if (p) {
    classId.value = p.classroom_id;
    await loadClassSummary();
  }
}

function onDateChange() {
  loadTodayPeriods();
  loadClassSummary();
}

onMounted(async () => {
  await loadClasses();
  await loadTodayPeriods();
});
</script>

<style scoped>
.glass-header {
  background: rgba(255,255,255,0.7);
  -webkit-backdrop-filter: blur(8px);
  backdrop-filter: blur(8px);
  border:1px solid rgba(0,0,0,0.06);
  border-radius: 16px;
}
.header-icon { font-size: 26px; color: #8a1538; }

.glass-form {
  background: rgba(255,255,255,0.65);
  -webkit-backdrop-filter: blur(8px);
  backdrop-filter: blur(8px);
  border:1px solid rgba(0,0,0,0.06);
  border-radius: 16px;
}

.chip { background: #f4f6f8; padding: 3px 8px; border-radius: 999px; }
.chip.muted { background: #f7f7fa; color: #666; }
.msg { color: #0a7; }

/* شبكة شرائح مرتبة تلقائيًا لتفادي التراكم */
.chips-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 8px; align-items: center; }

.table-card { border: 0; border-radius: 0; overflow: hidden; }
.table-card thead th { position: sticky; top: 0; background: #fafbfc; z-index: 1; }
.table-card tbody tr:hover { background: #fcfcff; }
.table-card select.form-select { min-width: 150px; }
.table-responsive { overflow-x: auto; }
.table-toolbar { background: rgba(255,255,255,0.65); }
.sticky-actions { position: sticky; bottom: 0; background: rgba(255,255,255,0.85); }

/* Toolbar for filters and actions: wrap on small screens, single line on large without horizontal scroll */
.toolbar-inline { display: flex; align-items: flex-end; gap: 8px; flex-wrap: wrap; overflow: visible; white-space: normal; }
.toolbar-inline .field-inline { display: inline-flex; align-items: center; gap: 6px; min-width: 0; }
.toolbar-inline .form-select, .toolbar-inline .form-control { min-width: 140px; flex: 0 1 auto; }
.toolbar-inline .btn { flex: 0 1 auto; }
@media (min-width: 992px) {
  .toolbar-inline { flex-wrap: nowrap; white-space: nowrap; overflow: hidden; }
  .toolbar-inline > * { min-width: 0; }
  .toolbar-inline .form-select, .toolbar-inline .form-control { min-width: 120px; }
}

/* Two-column students grid (full-bleed) */
.students-two-col { display: grid; grid-template-columns: 1fr; gap: 16px; width: 100vw; margin-inline: calc(50% - 50vw); padding-inline: 12px; box-sizing: border-box; }
@media (min-width: 992px) { /* lg breakpoint */
  .students-two-col { grid-template-columns: minmax(0,1fr) minmax(0,1fr); }
}
.students-two-col > .auto-card { width: 100%; }

.loader-line {
  height: 3px;
  background: linear-gradient(90deg, #8a1538, #b23a48);
  animation: load 1.1s linear infinite;
  border-radius: 2px;
}
@keyframes load { from { background-position: 0 0; } to { background-position: 200% 0; } }
</style>

<style scoped>
/* السماح بالتمرير على مستوى الصفحة بدلاً من الجدول */
.page-grid { grid-template-rows: auto auto auto auto; }
/* إزالة القيود التي تمنع تمدد المكونات وظهور تمرير الصفحة */
.page-grid > * { margin: 0 !important; }
/* الحفاظ على عرض المكونات بالكامل */
.page-grid .auto-card { width: 100%; }
.page-grid .glass-form, .page-grid .glass-header { width: 100%; }
/* عدم تحويل بطاقة الجدول إلى flex لتجنب تمرير داخلي */
.page-grid .auto-card.p-0 { }
</style>