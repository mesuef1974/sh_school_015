<template>
  <section>
    <h1 class="h5 page-header">سجل الغياب للمعلم</h1>
    <TeacherMenu />
    <p class="text-muted">استعراض وحفظ السجلات خلال فترة زمنية. (إصدار أولي)</p>

    <form @submit.prevent="loadHistory" class="d-flex gap-2 align-items-end mb-3 flex-wrap">
      <div>
        <label class="form-label">الصف</label>
        <input type="number" v-model.number="classId" min="1" required class="form-control" />
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
      <div class="ms-auto">
        <a href="/loads/matrix/export.xlsx" class="btn btn-outline-secondary" target="_blank">تصدير (Excel)</a>
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
            <td>{{ i + 1 }}</td>
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
    </div>

    <div class="mt-3">
      <small class="text-muted">ملاحظة: يتم جلب بيانات اليوم عبر /api/v1/attendance/records مؤقتًا؛ سنضيف نطاقًا تاريخيًا في API لاحقًا.</small>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { getAttendanceRecords } from '../../../shared/api/client';
import TeacherMenu from '../components/TeacherMenu.vue';

const today = new Date().toISOString().slice(0,10);
const classId = ref<number | null>(null);
const fromStr = ref<string>(today);
const toStr = ref<string>(today);
const loading = ref(false);

interface Row { date: string; student_name: string; status: string; note?: string | null }
const rows = ref<Row[]>([]);

function statusLabel(s: string) {
  switch (s) {
    case 'present': return 'حاضر';
    case 'absent': return 'غائب';
    case 'late': return 'متأخر';
    case 'excused': return 'معذور';
    default: return s;
  }
}
function statusClass(s: string) {
  return {
    'text-bg-success': s === 'present',
    'text-bg-danger': s === 'absent',
    'text-bg-warning': s === 'late',
    'text-bg-secondary': s === 'excused'
  };
}

async function loadHistory() {
  if (!classId.value) return;
  loading.value = true;
  try {
    // مؤقتًا: نجلب يوم "من" فقط حتى يتوفر Endpoint نطاق زمني
    const res = await getAttendanceRecords({ class_id: classId.value, date: fromStr.value });
    rows.value = (res.records || []).map(r => ({
      date: fromStr.value,
      student_name: `#${r.student_id}`,
      status: r.status,
      note: r.note
    }));
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.badge { font-weight: 600; }
</style>