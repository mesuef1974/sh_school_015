<template>
  <section>
    <div class="d-flex align-items-center gap-2 mb-3 page-header">
      <i class="bi bi-calendar2-week"></i>
      <h1 class="h5 m-0">جدولي الأسبوعي</h1>
      <span class="ms-auto"></span>
      <a class="btn btn-sm btn-outline-secondary" :href="backendUrl('/timetable/teachers/compact/')" target="_blank" rel="noopener noreferrer">النسخة القديمة</a>
    </div>

    <TeacherMenu />

    <div v-if="loading" class="loader-line"></div>
    <div v-else>
      <div class="auto-card p-3">
        <div class="table-responsive">
          <table class="table table-hover align-middle mb-0 text-center">
            <thead>
              <tr>
                <th class="text-center">اليوم</th>
                <th v-for="p in periodsDesc" :key="'h'+p" class="text-center">حصة {{ p }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="d in daysOrder" :key="'d'+d">
                <th class="text-nowrap text-center">{{ dayLabel(d) }}</th>
                <td v-for="p in periodsDesc" :key="'c'+d+'-'+p" class="text-center">
                  <div v-if="cell(d, p)" class="small text-center">
                    <div class="fw-bold">{{ cell(d, p)?.subject_name || '—' }}</div>
                    <div class="text-muted">{{ cell(d, p)?.classroom_name || ('صف #' + cell(d,p)?.classroom_id) }}</div>
                    <div class="text-muted" v-if="cellTime(d,p)">
                      {{ fmtTime(cellTime(d,p)?.[0]) }} – {{ fmtTime(cellTime(d,p)?.[1]) }}
                    </div>
                  </div>
                  <div v-else class="text-muted">—</div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <div v-if="empty" class="alert alert-secondary mt-2 mb-0">لا توجد حصص مجدولة لهذا الأسبوع.</div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref, computed } from 'vue';
import { getTeacherTimetableWeekly } from '../../../shared/api/client';
import { backendUrl } from '../../../shared/config';
import TeacherMenu from '../../attendance/components/TeacherMenu.vue';

const loading = ref(false);
const days = ref<Record<string, { period_number:number; classroom_id:number; classroom_name?:string; subject_id:number; subject_name?:string; start_time?: string; end_time?: string }[]>>({});
// Fallback period times per period_number when entry lacks embedded times
const periodTimes = ref<Record<number, [string, string]>>({} as any);

const daysOrder = [1,2,3,4,5];
const periodsDesc = [1,2,3,4,5,6,7];
const empty = computed(() => Object.values(days.value || {}).every(arr => (arr||[]).length === 0));
const maxPeriods = computed(() => {
  let m = 0;
  for (const k of Object.keys(days.value || {})) {
    for (const e of days.value[k] || []) {
      if (e.period_number > m) m = e.period_number;
    }
  }
  return Math.max(m, 7);
});

function dayLabel(d: number) {
  const map: Record<number,string> = {1:'الأحد',2:'الاثنين',3:'الثلاثاء',4:'الأربعاء',5:'الخميس',6:'الجمعة',7:'الأحد'};
  // isoweekday: 1=Mon..7=Sun; يمكن تعديل حسب سياسة المدرسة
  return map[d] || String(d);
}

function fmtTime(t?: string) {
  if (!t) return '';
  // Expect 'HH:MM[:SS]' — show only HH:MM
  return t.slice(0,5);
}

function cell(d: number, p: number) {
  const arr = days.value[String(d)] || [];
  return arr.find(e => e.period_number === p);
}

function cellTime(d: number, p: number): [string, string] | null {
  const c = cell(d, p) as any;
  if (c && c.start_time && c.end_time) {
    return [String(c.start_time), String(c.end_time)];
  }
  const t = (periodTimes.value as any)?.[p];
  return t ? [String(t[0]), String(t[1])] : null;
}

async function load() {
  loading.value = true;
  try {
    const res = await getTeacherTimetableWeekly();
    days.value = res.days || {};
    const pt = (res as any)?.meta?.period_times || {};
    // Normalize keys to numbers
    const out: Record<number,[string,string]> = {} as any;
    for (const k of Object.keys(pt)) {
      const num = Number(k);
      const val = pt[k];
      if (num && Array.isArray(val) && val.length >= 2) {
        out[num] = [String(val[0]), String(val[1])];
      }
    }
    periodTimes.value = out;
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>

<style scoped>
.table-responsive { overflow-x: auto; }
</style>