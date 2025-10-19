<template>
  <section>
    <h1 class="h5 page-header">سجل الغياب للمعلم</h1>
    <p class="text-muted">استعراض سجلات الغياب لفترة زمنية قابلة للتخصيص مع ترقيم صفحات.</p>

    <form @submit.prevent="loadHistory" class="d-flex gap-2 align-items-end mb-3 flex-wrap">
      <div>
        <label class="form-label">الصف</label>
        <select v-model.number="classId" required class="form-select">
          <option :value="null" disabled>اختر الصف</option>
          <option v-for="c in classes" :key="c.id" :value="c.id">{{ c.name || ('صف #' + c.id) }}</option>
        </select>
      </div>
      <div>
        <label class="form-label">من</label>
        <input type="date" v-model="fromStr" class="form-control" />
      </div>
      <div>
        <label class="form-label">إلى</label>
        <input type="date" v-model="toStr" class="form-control" />
      </div>
      <div>
        <button class="btn btn-maron">تحميل</button>
      </div>
    </form>

    <div v-if="loading">جاري التحميل…</div>
    <div v-else class="table-card">
      <table class="table table-hover">
        <thead>
          <tr>
            <th>#</th>
            <th>التاريخ</th>
            <th>الطالب</th>
            <th>الحالة</th>
            <th>ملاحظة</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, i) in rows" :key="i">
            <td>{{ (page - 1) * pageSize + i + 1 }}</td>
            <td>{{ row.date }}</td>
            <td>{{ row.student_name }}</td>
            <td>
              <span class="badge" :class="statusClass(row.status)">{{ statusLabel(row.status) }}</span>
            </td>
            <td>{{ row.note || '' }}</td>
          </tr>
        </tbody>
      </table>
      <div v-if="rows.length === 0" class="p-3">لا توجد سجلات في النطاق المحدد.</div>
      <div class="d-flex align-items-center gap-2 justify-content-end mt-2">
        <button type="button" class="btn btn-sm btn-outline-secondary" :disabled="page<=1 || loading" @click="prevPage">السابق</button>
        <span class="small text-muted">صفحة {{ page }} من {{ Math.max(1, Math.ceil(total / pageSize)) }}</span>
        <button type="button" class="btn btn-sm btn-outline-secondary" :disabled="page*pageSize>=total || loading" @click="nextPage">التالي</button>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { getAttendanceHistory, getTeacherClasses } from '../../../shared/api/client';

const today = new Date();
const iso = (d: Date) => d.toISOString().slice(0,10);
const defaultTo = iso(today);
const defaultFrom = iso(new Date(today.getTime() - 6*24*60*60*1000));

const classId = ref<number | null>(null);
const classes = ref<{ id: number; name?: string }[]>([]);
const fromStr = ref<string>(defaultFrom);
const toStr = ref<string>(defaultTo);
const loading = ref(false);
const page = ref(1);
const pageSize = ref(100);
const total = ref(0);

interface Row { date: string; student_name: string; status: string; note?: string | null }
const rows = ref<Row[]>([]);


function statusLabel(s: string) {
  switch (s) {
    case 'present': return 'حاضر';
    case 'absent': return 'غائب';
    case 'late': return 'متأخر';
    case 'excused': return 'إذن خروج';
    case 'runaway': return 'هروب';
    case 'left_early': return 'انصراف مبكر';
    default: return s;
  }
}
function statusClass(s: string) {
  return {
    'text-bg-success': s === 'present',
    'text-bg-danger': s === 'absent' || s === 'runaway',
    'text-bg-warning': s === 'late',
    'text-bg-secondary': s === 'excused',
    'text-bg-info': s === 'left_early'
  };
}

async function loadHistory() {
  if (!classId.value) return;
  loading.value = true;
  try {
    const res = await getAttendanceHistory({ class_id: classId.value, from: fromStr.value, to: toStr.value, page: page.value, page_size: pageSize.value });
    total.value = res.count || 0;
    rows.value = (res.results || []).map(r => ({
      date: r.date,
      student_name: r.student_name || `#${r.student_id}`,
      status: r.status,
      note: r.note
    }));
  } finally {
    loading.value = false;
  }
}

function nextPage() { if (page.value * pageSize.value < total.value) { page.value += 1; loadHistory(); } }
function prevPage() { if (page.value > 1) { page.value -= 1; loadHistory(); } }

onMounted(async () => {
  try {
    const res = await getTeacherClasses();
    classes.value = res.classes || [];
    if (!classId.value && classes.value.length) {
      classId.value = classes.value[0].id;
    }
  } catch {
    classes.value = [];
  }
});
</script>

<style scoped>
.badge { font-weight: 600; }
</style>