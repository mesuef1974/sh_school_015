<template>
  <section>
    <div class="d-flex align-items-center gap-2 mb-3 page-header">
      <i class="bi bi-clipboard-check"></i>
      <h1 class="h5 m-0">تسجيل الغياب</h1>
      <span class="ms-auto"></span>
      <span class="chip">تحسين بصري</span>
    </div>

    <TeacherMenu />

    <form @submit.prevent="loadData" class="row g-2 align-items-end mb-3">
      <div class="col-12 col-md-3">
        <label class="form-label">الصف</label>
        <select v-model.number="classId" required class="form-select">
          <option :value="null" disabled>اختر الصف</option>
          <option v-for="c in classes" :key="c.id" :value="c.id">{{ c.name || ('صف #' + c.id) }}</option>
        </select>
      </div>
      <div class="col-12 col-md-3">
        <label class="form-label">التاريخ</label>
        <input type="date" v-model="dateStr" class="form-control" @change="loadTodayPeriods" />
      </div>
      <div class="col-12 col-md-3">
        <label class="form-label">حصة اليوم</label>
        <select v-model.number="periodNo" class="form-select" @change="onPickPeriod">
          <option :value="null">— لا شيء —</option>
          <option v-for="p in todayPeriods" :key="p.period_number" :value="p.period_number">
            حصة {{ p.period_number }} — {{ p.subject_name || 'مادة' }} — {{ p.classroom_name || ('صف #' + p.classroom_id) }}
          </option>
        </select>
      </div>
      <div class="col-12 col-md-3 d-flex gap-2">
        <button type="submit" class="btn btn-maron">تحميل</button>
        <button type="button" class="btn btn-maron-outline" :disabled="!students.length" @click="setAll('present')">تعيين الجميع حاضر</button>
        <button type="button" class="btn btn-outline-secondary" :disabled="!students.length" @click="setAll('absent')">تعيين الجميع غائب</button>
      </div>
    </form>

    <div v-if="loading" class="loader-line"></div>
    <div v-else>
      <div class="summary" v-if="students.length">
        <strong>ملخص اليوم:</strong>
        <span>الإجمالي: {{ totalStudents }}</span>
        <span>حاضر: {{ presentCount }}</span>
        <span>غائب: {{ absentCount }}</span>
        <span>متأخر: {{ lateCount }}</span>
        <span>معذور: {{ excusedCount }}</span>
      </div>
      <div v-if="students.length === 0" class="auto-card p-3">لا يوجد طلاب.</div>
      <table v-else class="table table-hover table-card align-middle">
        <thead>
          <tr>
            <th style="width:60px">#</th>
            <th>الطالب</th>
            <th style="width:180px">الحالة</th>
            <th>ملاحظة</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(s, idx) in students" :key="s.id">
            <td>{{ idx + 1 }}</td>
            <td>{{ s.full_name }}</td>
            <td>
              <select v-model="recordMap[s.id].status" class="form-select">
                <option value="present">حاضر</option>
                <option value="absent">غائب</option>
                <option value="late">متأخر</option>
                <option value="excused">معذور</option>
              </select>
            </td>
            <td>
              <input type="text" v-model="recordMap[s.id].note" placeholder="اختياري" class="form-control" />
            </td>
          </tr>
        </tbody>
      </table>
      <div class="actions d-flex align-items-center gap-3" v-if="students.length">
        <button @click="save" :disabled="saving" class="btn btn-maron">حفظ</button>
        <span v-if="saveMsg" class="msg">{{ saveMsg }}</span>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, computed } from 'vue';
import { getAttendanceStudents, getAttendanceRecords, postAttendanceBulkSave, getTeacherClasses, getTeacherTimetableToday } from '../../../shared/api/client';
import { useToast } from 'vue-toastification';
import TeacherMenu from '../components/TeacherMenu.vue';

const toast = useToast();
const today = new Date().toISOString().slice(0, 10);
const classId = ref<number | null>(null);
const dateStr = ref<string>(today);
const loading = ref(false);
const saving = ref(false);
const saveMsg = ref('');

// Today periods for the teacher
const todayPeriods = ref<{ period_number:number; classroom_id:number; classroom_name?:string; subject_id:number; subject_name?:string }[]>([]);
const periodNo = ref<number | null>(null);

interface StudentBrief { id: number; first_name: string; last_name: string; }
interface Rec { student_id: number; status: string; note?: string | null }

const classes = ref<{ id: number; name?: string }[]>([]);
const students = ref<StudentBrief[]>([]);
const recordMap = reactive<Record<number, Rec>>({});

const totalStudents = computed(() => students.value.length);
const presentCount = computed(() => Object.values(recordMap).filter(r => r.status === 'present').length);
const absentCount = computed(() => Object.values(recordMap).filter(r => r.status === 'absent').length);
const lateCount = computed(() => Object.values(recordMap).filter(r => r.status === 'late').length);
const excusedCount = computed(() => Object.values(recordMap).filter(r => r.status === 'excused').length);

function setAll(st: 'present'|'absent'|'late'|'excused') {
  for (const s of students.value) {
    if (recordMap[s.id]) recordMap[s.id].status = st;
  }
}

const collator = new Intl.Collator('ar');

async function loadData() {
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
      getAttendanceRecords({ class_id: classId.value, date: dateStr.value })
    ]);
    // Arabic ascending sort by full_name
    students.value = [...sres.students].sort((a: any, b: any) => {
      return collator.compare(a.full_name || '', b.full_name || '');
    });
    // reset map
    for (const k of Object.keys(recordMap)) delete (recordMap as any)[k];
    for (const st of students.value) {
      (recordMap as any)[st.id] = { student_id: st.id, status: 'present', note: '' };
    }
    for (const r of rres.records) {
      (recordMap as any)[r.student_id] = { student_id: r.student_id, status: r.status, note: r.note ?? '' };
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
  saving.value = true;
  saveMsg.value = '';
  try {
    const records = Object.values(recordMap);
    const res = await postAttendanceBulkSave({ class_id: classId.value, date: dateStr.value, records });
    const msg = `تم الحفظ (${res.saved})`;
    saveMsg.value = msg;
    try { toast.success(msg, { autoClose: 2500 }); } catch {}
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
  try {
    const res = await getTeacherTimetableToday({ date: dateStr.value });
    todayPeriods.value = res.periods || [];
  } catch {
    todayPeriods.value = [];
  }
}

function onPickPeriod() {
  if (!periodNo.value) return;
  const p = todayPeriods.value.find(pp => pp.period_number === periodNo.value);
  if (p) {
    classId.value = p.classroom_id;
  }
}

onMounted(async () => {
  await loadClasses();
  await loadTodayPeriods();
});
</script>

<style scoped>
.summary { display: flex; flex-wrap: wrap; gap: 0.75rem; margin: 0.5rem 0 1rem; padding: 0.5rem 0; }
.summary span { background: #f4f6f8; padding: 2px 6px; border-radius: 4px; }
.actions { margin-top: 0.75rem; display: flex; align-items: center; gap: 1rem; }
.msg { color: #0a7; }
</style>