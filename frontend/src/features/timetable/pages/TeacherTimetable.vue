<template>
  <section class="d-grid gap-3">
    <!-- Header Card -->
    <DsCard
      v-motion
      :initial="{ opacity: 0, y: -30 }"
      :enter="{ opacity: 1, y: 0, transition: { duration: 400 } }"
    >
      <div class="d-flex align-items-center gap-3">
        <Icon icon="solar:calendar-bold-duotone" class="text-4xl" style="color: var(--color-info)" />
        <div class="flex-grow-1">
          <div class="text-xl font-bold">جدولي الأسبوعي</div>
          <div class="text-muted text-sm">جدول الحصص الدراسية للأسبوع الحالي</div>
        </div>
        <DsBadge variant="info" icon="solar:calendar-mark-bold-duotone">
          {{ getCurrentWeek() }}
        </DsBadge>
      </div>
    </DsCard>

    <!-- Stats Cards -->
    <div class="row g-3">
      <div class="col-6 col-md-3">
        <DsCard
          v-motion
          :initial="{ opacity: 0, scale: 0.8 }"
          :enter="{ opacity: 1, scale: 1, transition: { duration: 400, delay: 50 } }"
          :interactive="true"
        >
          <div class="text-center">
            <Icon icon="solar:book-bold-duotone" class="text-3xl mb-2" style="color: var(--color-info)" />
            <div class="small text-muted mb-1">إجمالي الحصص</div>
            <div class="h5 fw-bold mb-0">{{ totalPeriods }}</div>
          </div>
        </DsCard>
      </div>
      <div class="col-6 col-md-3">
        <DsCard
          v-motion
          :initial="{ opacity: 0, scale: 0.8 }"
          :enter="{ opacity: 1, scale: 1, transition: { duration: 400, delay: 100 } }"
          :interactive="true"
        >
          <div class="text-center">
            <Icon icon="solar:layers-minimalistic-bold-duotone" class="text-3xl mb-2" style="color: var(--color-success)" />
            <div class="small text-muted mb-1">الصفوف</div>
            <div class="h5 fw-bold mb-0">{{ uniqueClasses }}</div>
          </div>
        </DsCard>
      </div>
      <div class="col-6 col-md-3">
        <DsCard
          v-motion
          :initial="{ opacity: 0, scale: 0.8 }"
          :enter="{ opacity: 1, scale: 1, transition: { duration: 400, delay: 150 } }"
          :interactive="true"
        >
          <div class="text-center">
            <Icon icon="solar:document-text-bold-duotone" class="text-3xl mb-2" style="color: var(--color-warning)" />
            <div class="small text-muted mb-1">المواد</div>
            <div class="h5 fw-bold mb-0">{{ uniqueSubjects }}</div>
          </div>
        </DsCard>
      </div>
      <div class="col-6 col-md-3">
        <DsCard
          v-motion
          :initial="{ opacity: 0, scale: 0.8 }"
          :enter="{ opacity: 1, scale: 1, transition: { duration: 400, delay: 200 } }"
          :interactive="true"
        >
          <div class="text-center">
            <Icon icon="solar:calendar-date-bold-duotone" class="text-3xl mb-2" style="color: var(--maron-primary)" />
            <div class="small text-muted mb-1">اليوم</div>
            <div class="h5 fw-bold mb-0">{{ getCurrentDay() }}</div>
          </div>
        </DsCard>
      </div>
    </div>

    <!-- Loading State -->
    <DsCard v-if="loading" class="text-center py-5">
      <Icon icon="solar:refresh-bold-duotone" class="text-5xl mb-3 animate-spin" style="color: var(--maron-primary)" />
      <div class="text-muted">جاري تحميل الجدول...</div>
    </DsCard>

    <!-- Empty State -->
    <DsCard v-else-if="empty" class="text-center py-5">
      <Icon icon="solar:calendar-minimalistic-bold-duotone" class="text-6xl mb-3" style="opacity: 0.3; color: var(--color-info)" />
      <div class="h5 mb-2">لا توجد حصص مجدولة</div>
      <div class="text-muted small">لا توجد حصص مجدولة لك في هذا الأسبوع</div>
    </DsCard>

    <!-- Timetable Card -->
    <DsCard v-else class="p-0 overflow-hidden timetable-card">
      <div class="timetable-wrapper">
        <table class="timetable-modern">
          <thead>
            <tr>
              <th class="timetable-th day-column">
                <div class="th-content">
                  <Icon icon="solar:calendar-bold-duotone" width="20" />
                  <span>اليوم</span>
                </div>
              </th>
              <th v-for="p in periodsDesc" :key="'h'+p" class="timetable-th period-column">
                <div class="th-content">
                  <Icon icon="solar:clock-circle-bold-duotone" width="18" />
                  <span>حصة {{ p }}</span>
                </div>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(d, idx) in daysOrder"
              :key="'d'+d"
              class="timetable-tr"
              v-motion
              :initial="{ opacity: 0, x: -20 }"
              :enter="{ opacity: 1, x: 0, transition: { duration: 400, delay: 250 + (idx * 80) } }"
            >
              <th class="day-cell" :class="{ 'today-cell': isToday(d) }">
                <div class="day-label">
                  <Icon v-if="isToday(d)" icon="solar:calendar-mark-bold-duotone" width="18" class="me-1" />
                  {{ dayLabel(d) }}
                </div>
              </th>
              <td
                v-for="p in periodsDesc"
                :key="'c'+d+'-'+p"
                class="period-cell"
                :class="{ 'has-class': cell(d, p), 'current-period': isCurrentPeriod(d, p) }"
                :style="cell(d, p) ? { background: getClassColor(cell(d, p)!.classroom_id).light } : {}"
              >
                <div v-if="cell(d, p)" class="period-content">
                  <div
                    class="subject-badge"
                    :style="{
                      background: getClassColor(cell(d, p)!.classroom_id).bg,
                      color: getClassColor(cell(d, p)!.classroom_id).text
                    }"
                  >
                    <Icon icon="solar:book-2-bold-duotone" width="16" />
                    <span class="subject-name">{{ cell(d, p)?.subject_name || '—' }}</span>
                  </div>
                  <div class="classroom-info">
                    <div
                      class="classroom-badge"
                      :style="{
                        borderColor: getClassColor(cell(d, p)!.classroom_id).bg.split(',')[0].split('(')[1],
                        color: getClassColor(cell(d, p)!.classroom_id).bg.split(',')[0].split('(')[1]
                      }"
                    >
                      <Icon icon="solar:home-2-bold-duotone" width="14" />
                      <span>{{ cell(d, p)?.classroom_name || ('صف #' + cell(d,p)?.classroom_id) }}</span>
                    </div>
                  </div>
                  <div class="time-info" v-if="cellTime(d,p)">
                    <Icon icon="solar:clock-circle-bold-duotone" width="14" style="opacity: 0.6" />
                    <span>{{ fmtTime(cellTime(d,p)?.[0]) }} – {{ fmtTime(cellTime(d,p)?.[1]) }}</span>
                  </div>
                </div>
                <div v-else class="empty-period">
                  <Icon icon="solar:minus-circle-bold-duotone" width="20" style="opacity: 0.2" />
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Color Legend -->
      <div class="color-legend">
        <div class="legend-title">
          <Icon icon="solar:palette-bold-duotone" width="18" />
          <span>دليل ألوان الصفوف</span>
        </div>
        <div class="legend-items">
          <div
            v-for="(classId, index) in Object.keys(classColorMap).map(Number)"
            :key="classId"
            class="legend-item"
          >
            <div
              class="legend-color"
              :style="{ background: getClassColor(classId).bg }"
            ></div>
            <span class="legend-label">
              {{ getClassNameById(classId) }}
            </span>
          </div>
        </div>
      </div>
    </DsCard>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref, computed } from 'vue';
import { getTeacherTimetableWeekly } from '../../../shared/api/client';
import DsCard from '../../../components/ui/DsCard.vue';
import DsBadge from '../../../components/ui/DsBadge.vue';

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

// Stats calculations
const totalPeriods = computed(() => {
  let count = 0;
  for (const dayKey in days.value) {
    count += (days.value[dayKey] || []).length;
  }
  return count;
});

const uniqueClasses = computed(() => {
  const classIds = new Set<number>();
  for (const dayKey in days.value) {
    for (const period of days.value[dayKey] || []) {
      classIds.add(period.classroom_id);
    }
  }
  return classIds.size;
});

const uniqueSubjects = computed(() => {
  const subjectIds = new Set<number>();
  for (const dayKey in days.value) {
    for (const period of days.value[dayKey] || []) {
      subjectIds.add(period.subject_id);
    }
  }
  return subjectIds.size;
});

function getCurrentWeek(): string {
  const now = new Date();
  const start = new Date(now.getFullYear(), 0, 1);
  const days = Math.floor((now.getTime() - start.getTime()) / (24 * 60 * 60 * 1000));
  const weekNumber = Math.ceil((days + start.getDay() + 1) / 7);
  return `الأسبوع ${weekNumber}`;
}

function getCurrentDay(): string {
  const days = ['الأحد', 'الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت'];
  return days[new Date().getDay()];
}

function isToday(d: number): boolean {
  const today = new Date().getDay();
  // Map: 1=الأحد (Sunday)... adjust based on your system
  return d === (today === 0 ? 7 : today);
}

function isCurrentPeriod(d: number, p: number): boolean {
  if (!isToday(d)) return false;

  const now = new Date();
  const currentTime = now.getHours() * 60 + now.getMinutes();

  const times = cellTime(d, p);
  if (!times) return false;

  const [start, end] = times;
  const [startH, startM] = start.split(':').map(Number);
  const [endH, endM] = end.split(':').map(Number);

  const startTime = startH * 60 + startM;
  const endTime = endH * 60 + endM;

  return currentTime >= startTime && currentTime <= endTime;
}

// Color palette for classes (Maroon-themed harmony)
const classColors = [
  { bg: 'linear-gradient(135deg, #8b1e3f 0%, #a52a2a 100%)', text: '#ffffff', light: '#f8e5e9' }, // Maroon
  { bg: 'linear-gradient(135deg, #6a4c93 0%, #8b6fb0 100%)', text: '#ffffff', light: '#f3eef8' }, // Purple
  { bg: 'linear-gradient(135deg, #c1666b 0%, #d4737c 100%)', text: '#ffffff', light: '#fdf0f1' }, // Rose
  { bg: 'linear-gradient(135deg, #9c6644 0%, #b87c5a 100%)', text: '#ffffff', light: '#f9f3ef' }, // Brown
  { bg: 'linear-gradient(135deg, #7b1e1e 0%, #a52a2a 100%)', text: '#ffffff', light: '#fae5e5' }, // Dark Maroon
  { bg: 'linear-gradient(135deg, #8b4367 0%, #a5577d 100%)', text: '#ffffff', light: '#f8ecf3' }, // Burgundy
  { bg: 'linear-gradient(135deg, #9c4f5f 0%, #b56576 100%)', text: '#ffffff', light: '#fceef1' }, // Wine
  { bg: 'linear-gradient(135deg, #7b5e57 0%, #947265 100%)', text: '#ffffff', light: '#f7f1ef' }, // Taupe
];

// Get unique class ID to color mapping
const classColorMap = computed(() => {
  const classIds = new Set<number>();
  for (const dayKey in days.value) {
    for (const period of days.value[dayKey] || []) {
      classIds.add(period.classroom_id);
    }
  }

  const map: Record<number, typeof classColors[0]> = {};
  const sortedIds = Array.from(classIds).sort((a, b) => a - b);
  sortedIds.forEach((id, index) => {
    map[id] = classColors[index % classColors.length];
  });

  return map;
});

function getClassColor(classId: number) {
  return classColorMap.value[classId] || classColors[0];
}

function getClassNameById(classId: number): string {
  for (const dayKey in days.value) {
    for (const period of days.value[dayKey] || []) {
      if (period.classroom_id === classId) {
        return period.classroom_name || `صف #${classId}`;
      }
    }
  }
  return `صف #${classId}`;
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
/* Timetable Professional Styles */
.timetable-card {
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
  border-radius: 12px;
}

.timetable-wrapper {
  overflow-x: auto;
  overflow-y: visible;
}

.timetable-modern {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  min-width: 900px;
}

/* Table Header */
.timetable-th {
  background: linear-gradient(135deg, var(--maron-primary, #7b1e1e) 0%, #a52a2a 100%);
  color: white;
  padding: 1rem;
  text-align: center;
  font-weight: 600;
  border: none;
  position: sticky;
  top: 0;
  z-index: 10;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.timetable-th.day-column {
  min-width: 120px;
}

.timetable-th.period-column {
  min-width: 140px;
}

.th-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}

/* Table Body */
.timetable-tr {
  transition: all 0.2s ease;
}

.timetable-tr:hover {
  background: #f8f9fa;
}

/* Day Cell */
.day-cell {
  background: linear-gradient(135deg, #e9ecef 0%, #f8f9fa 100%);
  padding: 1.25rem 1rem;
  text-align: center;
  font-weight: 700;
  color: #495057;
  border-bottom: 1px solid #dee2e6;
  position: sticky;
  right: 0;
  z-index: 5;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.05);
}

.today-cell {
  background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
  color: #856404;
  border: 2px solid #ffc107;
  box-shadow: 0 0 12px rgba(255, 193, 7, 0.3);
}

.day-label {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  font-size: 1rem;
}

/* Period Cell */
.period-cell {
  padding: 0.75rem;
  border: 1px solid #e9ecef;
  text-align: center;
  vertical-align: middle;
  background: white;
  transition: all 0.3s ease;
  position: relative;
}

.period-cell.has-class:hover {
  transform: scale(1.03);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
  z-index: 2;
  cursor: pointer;
  filter: brightness(0.98);
}

.period-cell.current-period {
  border: 3px solid #28a745;
  box-shadow: 0 0 20px rgba(40, 167, 69, 0.6), inset 0 0 20px rgba(40, 167, 69, 0.15);
  animation: pulse 2s ease-in-out infinite;
  position: relative;
}

.period-cell.current-period::before {
  content: '';
  position: absolute;
  top: 8px;
  left: 8px;
  width: 12px;
  height: 12px;
  background: #28a745;
  border-radius: 50%;
  animation: blink 1.5s ease-in-out infinite;
  box-shadow: 0 0 8px rgba(40, 167, 69, 0.8);
}

@keyframes pulse {
  0%, 100% {
    box-shadow: 0 0 20px rgba(40, 167, 69, 0.6), inset 0 0 20px rgba(40, 167, 69, 0.15);
  }
  50% {
    box-shadow: 0 0 30px rgba(40, 167, 69, 0.8), inset 0 0 30px rgba(40, 167, 69, 0.25);
  }
}

@keyframes blink {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.3;
  }
}

/* Period Content */
.period-content {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  align-items: center;
}

.subject-badge {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  background: linear-gradient(135deg, var(--maron-primary, #7b1e1e) 0%, #a52a2a 100%);
  color: white;
  border-radius: 20px;
  font-weight: 600;
  font-size: 0.9rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  width: 100%;
  justify-content: center;
}

.subject-name {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 120px;
}

.classroom-info {
  width: 100%;
  display: flex;
  justify-content: center;
}

.classroom-badge {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.8rem;
  font-weight: 600;
  padding: 0.375rem 0.75rem;
  border-radius: 12px;
  border: 2px solid;
  background: white;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.time-info {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.8rem;
  color: #6c757d;
}

.time-info {
  background: #f8f9fa;
  padding: 0.25rem 0.5rem;
  border-radius: 12px;
  border: 1px solid #dee2e6;
}

/* Color Legend */
.color-legend {
  padding: 1.5rem;
  background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
  border-top: 2px solid #e9ecef;
}

.legend-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 700;
  font-size: 0.95rem;
  color: var(--maron-primary, #7b1e1e);
  margin-bottom: 1rem;
}

.legend-items {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: white;
  border-radius: 20px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
  transition: all 0.2s ease;
}

.legend-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.legend-color {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
  border: 2px solid white;
  flex-shrink: 0;
}

.legend-label {
  font-weight: 600;
  font-size: 0.9rem;
  color: #495057;
  white-space: nowrap;
}

/* Empty Period */
.empty-period {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 80px;
  color: #dee2e6;
}

/* Loading Animation */
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.animate-spin {
  animation: spin 2s linear infinite;
}

/* Responsive Design */
@media (max-width: 768px) {
  .timetable-th,
  .day-cell,
  .period-cell {
    padding: 0.75rem 0.5rem;
    font-size: 0.85rem;
  }

  .subject-badge {
    font-size: 0.8rem;
    padding: 0.375rem 0.5rem;
  }

  .subject-name {
    max-width: 80px;
  }

  .timetable-th.period-column {
    min-width: 100px;
  }

  .classroom-info,
  .time-info {
    font-size: 0.75rem;
  }
}

/* Print Styles */
@media print {
  .timetable-card {
    box-shadow: none;
    border: 1px solid #dee2e6;
  }

  .period-cell.has-class:hover {
    transform: none;
    box-shadow: none;
  }

  .timetable-th {
    position: static;
    background: #f8f9fa;
    color: #212529;
    border: 1px solid #dee2e6;
  }

  .day-cell {
    position: static;
    border: 1px solid #dee2e6;
  }
}
</style>