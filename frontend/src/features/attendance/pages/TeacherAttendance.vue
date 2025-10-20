<template>
  <section class="d-grid gap-3 page-grid">
    <header
      v-motion
      :initial="{ opacity: 0, y: -30 }"
      :enter="{ opacity: 1, y: 0, transition: { duration: 400 } }"
      class="auto-card p-3 d-flex align-items-center gap-3 glass-header"
    >
      <Icon icon="solar:clipboard-check-bold-duotone" class="header-icon" />
      <div>
        <div class="fw-bold">تسجيل الغياب</div>
        <div class="text-muted small">اختر الصف والتاريخ (اختياري: حصة اليوم)</div>
      </div>
      <span class="ms-auto"></span>
    </header>

    <div
      v-motion
      :initial="{ opacity: 0, x: -50 }"
      :enter="{ opacity: 1, x: 0, transition: { duration: 400, delay: 100 } }"
      class="auto-card p-3 mb-3"
    >
      <form @submit.prevent="loadData" class="attendance-form">
        <!-- Row 1: Filters -->
        <div class="form-row">
          <div class="form-field">
            <label class="form-label">
              <Icon icon="solar:users-group-two-rounded-bold-duotone" width="18" />
              الصف
            </label>
            <select v-model.number="classId" required class="form-select">
              <option :value="null" disabled>اختر الصف</option>
              <option v-for="c in classes" :key="c.id" :value="c.id">{{ c.name || ('صف #' + c.id) }}</option>
            </select>
          </div>

          <div class="form-field">
            <label class="form-label">
              <Icon icon="solar:calendar-bold-duotone" width="18" />
              التاريخ
            </label>
            <input type="date" v-model="dateStr" class="form-control" @change="onDateChange" />
          </div>

          <div class="form-field form-field-wide">
            <label class="form-label">
              <Icon icon="solar:clock-circle-bold-duotone" width="18" />
              حصة اليوم
            </label>
            <select v-model.number="periodNo" class="form-select" @change="onPickPeriod">
              <option :value="null">— لا شيء —</option>
              <option v-for="p in todayPeriods" :key="p.period_number" :value="p.period_number">
                حصة {{ p.period_number }} — {{ p.subject_name || 'مادة' }} — {{ p.classroom_name || ('صف #' + p.classroom_id) }}
              </option>
            </select>
          </div>

          <DsButton type="submit" variant="primary" icon="solar:refresh-bold-duotone" class="btn-load">
            تحميل
          </DsButton>
        </div>

        <!-- Row 2: Actions -->
        <div class="form-actions">
          <DsButton type="button" variant="success" icon="solar:check-circle-bold-duotone" :disabled="!students.length" @click="setAll('present')">
            <span class="btn-text">تعيين الجميع حاضر</span>
            <span class="btn-text-short">حاضر</span>
          </DsButton>
          <DsButton type="button" variant="danger" icon="solar:close-circle-bold-duotone" :disabled="!students.length" @click="setAll('absent')">
            <span class="btn-text">تعيين الجميع غائب</span>
            <span class="btn-text-short">غائب</span>
          </DsButton>
          <DsButton type="button" variant="primary" icon="solar:diskette-bold-duotone" :disabled="saving || !students.length" :loading="saving" @click="save">
            <span class="btn-text">حفظ الحضور</span>
            <span class="btn-text-short">حفظ</span>
          </DsButton>
        </div>
      </form>
    </div>

    <div v-if="loading" class="loader-line"></div>
    <div v-else>
      <div v-if="classId || students.length" class="auto-card p-3 mb-3">
        <div class="stats-header">
          <div class="d-flex align-items-center gap-2">
            <Icon icon="solar:chart-bold-duotone" width="20" style="color: var(--maron-primary);" />
            <span class="fw-bold">معلومات اليوم</span>
          </div>
          <div class="date-badge">
            <Icon icon="solar:calendar-bold-duotone" width="16" />
            <span>{{ dateStr }}</span>
          </div>
        </div>
        <div class="chips-grid">
          <DsBadge variant="info" icon="solar:chart-bold-duotone">
            الحضور: <strong>{{ classKpis.present_pct ?? '--' }}%</strong>
          </DsBadge>
          <DsBadge variant="success" icon="solar:check-circle-bold-duotone">
            حاضر {{ classKpis.present ?? 0 }} / {{ classKpis.total ?? 0 }}
          </DsBadge>
          <DsBadge variant="danger" icon="solar:close-circle-bold-duotone">
            غياب: {{ classKpis.absent ?? 0 }}
          </DsBadge>
          <DsBadge variant="warning" icon="solar:clock-circle-bold-duotone">
            متأخر: {{ classKpis.late ?? 0 }}
          </DsBadge>
          <DsBadge variant="danger" icon="solar:running-bold-duotone">
            هروب: {{ classKpis.runaway ?? 0 }}
          </DsBadge>
          <DsBadge variant="info" icon="solar:exit-bold-duotone">
            إذن خروج: {{ classKpis.excused ?? 0 }}
          </DsBadge>
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
                  <td><span class="student-name" :class="nameClass(recordMap[s.id].status)">{{ s.full_name }}</span></td>
                  <td>
                    <select v-model="recordMap[s.id].status" class="form-select" :class="statusClass(recordMap[s.id].status)">
                      <option value=""></option>
                      <option value="present" :class="statusClass('present')">حاضر</option>
                      <option value="absent" :class="statusClass('absent')">غائب</option>
                      <option value="late" :class="statusClass('late')">متأخر</option>
                      <option value="excused" :class="statusClass('excused')">إذن خروج</option>
                      <option value="runaway" :class="statusClass('runaway')">هروب</option>
                      <option value="left_early" :class="statusClass('left_early')">انصراف مبكر</option>
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
                        <span class="form-check-label">دورة المياه</span>
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
                  <td><span class="student-name" :class="nameClass(recordMap[s.id].status)">{{ s.full_name }}</span></td>
                  <td>
                    <select v-model="recordMap[s.id].status" class="form-select" :class="statusClass(recordMap[s.id].status)">
                      <option value=""></option>
                      <option value="present" :class="statusClass('present')">حاضر</option>
                      <option value="absent" :class="statusClass('absent')">غائب</option>
                      <option value="late" :class="statusClass('late')">متأخر</option>
                      <option value="excused" :class="statusClass('excused')">إذن خروج</option>
                      <option value="runaway" :class="statusClass('runaway')">هروب</option>
                      <option value="left_early" :class="statusClass('left_early')">انصراف مبكر</option>
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
                        <span class="form-check-label">دورة المياه</span>
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
import DsButton from '../../../components/ui/DsButton.vue';
import DsBadge from '../../../components/ui/DsBadge.vue';

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

function statusClass(s: string) {
  // Align colors with history page badges (background colors)
  return {
    'text-bg-success': s === 'present',
    'text-bg-danger': s === 'absent' || s === 'runaway',
    'text-bg-warning': s === 'late',
    'text-bg-secondary': s === 'excused',
    'text-bg-info': s === 'left_early'
  } as any;
}

// Text-only color for student name (no background)
function nameClass(s: string) {
  return {
    'text-success': s === 'present',
    'text-danger': s === 'absent' || s === 'runaway',
    'text-warning': s === 'late',
    'text-secondary': s === 'excused',
    'text-info': s === 'left_early'
  } as any;
}

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
/* Student name uses text color only (no background chip) */
.student-name { font-weight: 600; }
.table-responsive { overflow-x: auto; }
.table-toolbar { background: rgba(255,255,255,0.65); }
.sticky-actions { position: sticky; bottom: 0; background: rgba(255,255,255,0.85); }

/* Toolbar for filters and actions: wrap on small screens, single line on large without horizontal scroll */
/* Attendance Form Styles */
.attendance-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1rem;
  align-items: end;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  font-size: 0.875rem;
  color: #495057;
  margin-bottom: 0;
}

.form-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  padding-top: 0.5rem;
  border-top: 1px solid #e9ecef;
}

.form-actions button {
  flex: 1 1 auto;
  min-width: 140px;
}

.btn-text-short {
  display: none;
}

/* Mobile & Up - All in one row */
@media (min-width: 576px) {
  .form-row {
    grid-template-columns: 160px 150px 1fr auto;
  }

  .form-field-wide {
    grid-column: auto;
  }

  .btn-load {
    align-self: end;
  }

  .form-actions button {
    flex: 0 1 auto;
  }
}

/* Tablet & Up */
@media (min-width: 768px) {
  .form-row {
    grid-template-columns: 180px 160px 1fr auto;
  }
}

/* Desktop */
@media (min-width: 992px) {
  .form-row {
    grid-template-columns: 200px 180px 1fr auto;
  }
}

/* Large Desktop */
@media (min-width: 1200px) {
  .form-row {
    grid-template-columns: 220px 200px 1fr auto;
  }
}

/* Mobile - Show short text */
@media (max-width: 576px) {
  .btn-text {
    display: none;
  }

  .btn-text-short {
    display: inline;
  }

  .form-actions button {
    min-width: 100px;
  }
}

/* Stats Header */
.stats-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid #e9ecef;
  flex-wrap: wrap;
}

.date-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  border-radius: 8px;
  font-size: 0.875rem;
  font-weight: 600;
  color: #495057;
  border: 1px solid #dee2e6;
  white-space: nowrap;
}

@media (max-width: 576px) {
  .stats-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .date-badge {
    align-self: stretch;
    justify-content: center;
  }
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