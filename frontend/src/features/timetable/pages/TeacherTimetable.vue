<template>
  <section class="d-grid gap-3 timetable-page">
    <!-- Header Card -->
    <DsCard
      class="outlined-card"
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

    <!-- Split cards: A) Day/Date/Time, B) Live KPIs -->
    <div class="row g-3 align-items-stretch">
      <!-- Card A: اليوم | الميلادي | الساعة -->
      <div class="col-12 col-md-6">
        <DsCard
          v-motion
          :initial="{ opacity: 0, scale: 0.9 }"
          :enter="{ opacity: 1, scale: 1, transition: { duration: 400, delay: 80 } }"
          :interactive="true"
          class="h-100 outlined-card"
        >
          <div class="mini-table-wrap">
            <table class="mini-table" dir="rtl">
              <thead>
                <tr>
                  <th>اليوم</th>
                  <th>التاريخ الهجري</th>
                  <th>التاريخ الميلادي</th>
                  <th>الساعة</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td class="fw-bold">{{ liveDay }}</td>
                  <td>{{ liveHijri }}</td>
                  <td>{{ liveDate }}</td>
                  <td class="live-clock fw-semibold">{{ liveTime }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </DsCard>
      </div>

      <!-- Card B: المؤشرات الحية -->
      <div class="col-12 col-md-6">
        <DsCard
          v-motion
          :initial="{ opacity: 0, scale: 0.9 }"
          :enter="{ opacity: 1, scale: 1, transition: { duration: 400, delay: 120 } }"
          :interactive="true"
          class="h-100 outlined-card"
        >
          <div class="mini-stats">
            <div class="mini-stat">
              <Icon icon="solar:book-bold-duotone" class="me-1" style="color: var(--color-info)" />
              <span class="label">إجمالي الحصص</span>
              <span class="value">{{ totalPeriods }}</span>
            </div>
            <div class="mini-stat">
              <Icon icon="solar:layers-minimalistic-bold-duotone" class="me-1" style="color: var(--color-success)" />
              <span class="label">الصفوف</span>
              <span class="value">{{ uniqueClasses }}</span>
            </div>
            <div class="mini-stat">
              <Icon icon="solar:document-text-bold-duotone" class="me-1" style="color: var(--color-warning)" />
              <span class="label">المواد</span>
              <span class="value">{{ uniqueSubjects }}</span>
            </div>
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
    <DsCard v-else ref="timetableRef" class="p-0 overflow-hidden timetable-card outlined-card">
      <!-- Actions toolbar -->
      <div class="timetable-toolbar">
        <button class="tt-btn" @click="toggle()" :title="isFullscreen ? 'الخروج من ملء الشاشة' : 'ملء الشاشة'">
          <Icon :icon="isFullscreen ? 'solar:minimize-square-bold-duotone' : 'solar:maximize-square-bold-duotone'" width="18" />
          <span class="d-none d-sm-inline">{{ isFullscreen ? 'إغلاق ملء الشاشة' : 'ملء الشاشة' }}</span>
        </button>
        <button class="tt-btn" @click="handlePrint" title="طباعة الجدول">
          <Icon icon="solar:printer-minimalistic-bold-duotone" width="18" />
          <span class="d-none d-sm-inline">طباعة</span>
        </button>
        <button class="tt-btn" @click="showPrefs = !showPrefs" title="إعدادات العرض">
          <Icon icon="solar:settings-bold-duotone" width="18" />
          <span class="d-none d-sm-inline">إعدادات</span>
        </button>
        <div class="flex-grow-1"></div>
        <label class="tt-toggle" :title="prefs.dense ? 'نمط افتراضي' : 'نمط مضغوط'">
          <input type="checkbox" v-model="prefs.dense" />
          <span>نمط مضغوط</span>
        </label>
        <label class="tt-toggle" title="إظهار/إخفاء العدّاد">
          <input type="checkbox" v-model="prefs.showCountdown" />
          <span>العدّاد</span>
        </label>
      </div>

      <!-- Simple preferences panel -->
      <div v-if="showPrefs" class="prefs-panel">
        <div class="prefs-header">
          <div class="title">
            <Icon icon="solar:settings-bold-duotone" width="20" />
            <span>إعدادات الجدول</span>
          </div>
          <button class="tt-btn" @click="showPrefs = false" title="إغلاق">
            <Icon icon="solar:close-circle-bold-duotone" width="18" />
          </button>
        </div>
        <div class="prefs-body">
          <label class="row-item">
            <input type="checkbox" v-model="prefs.autoFullscreen" />
            <span>تفعيل ملء الشاشة تلقائيًا عند فتح الصفحة</span>
          </label>
          <label class="row-item">
            <input type="checkbox" v-model="prefs.notifications" />
            <span>السماح بإشعارات المتصفح عند قرب نهاية الحصة</span>
          </label>
        </div>
      </div>

      <div class="timetable-wrapper" :class="{ dense: prefs.dense }">
        <div class="tt-scale-95">
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
                <!-- Green countdown near the green dot when current period -->
                <div
                  v-if="prefs.showCountdown && isCurrentPeriod(d, p) && remainingTime(d,p)"
                  class="countdown-badge"
                  :title="'الوقت المتبقي للحصة'"
                >
                  {{ remainingTime(d,p) }}
                </div>
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
                <!-- Current period progress bar -->
                <div v-if="isCurrentPeriod(d,p)" class="progress-wrap">
                  <div class="progress-bar" :style="{ width: periodProgress(d,p) + '%' }"></div>
                </div>
              </td>
            </tr>
          </tbody>
          </table>
        </div>
      </div>

    </DsCard>
  </section>
</template>

<style scoped>
/* Modern timetable styling - maroon themed, clean and readable */
.timetable-wrapper{
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.timetable-modern{
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  background: #fff;
}

.timetable-modern thead th{
  position: sticky;
  top: 0;
  z-index: 3;
  background: #faf6f5;
  backdrop-filter: saturate(140%) blur(3px);
  text-align: start;
  font-weight: 700;
  color: #5a3b3b;
  border-bottom: 1px solid rgba(0,0,0,.06);
}

.timetable-th{
  padding: .75rem .75rem;
  white-space: nowrap;
}

.th-content{ display:flex; align-items:center; gap:.5rem; }

.timetable-tr th,
.timetable-tr td{
  border-bottom: 1px solid rgba(0,0,0,.06);
}

.day-column{ position: sticky; inset-inline-start: 0; z-index: 2; background: #fff; min-width: 120px; }
.day-cell{ background: linear-gradient(90deg, #fff, #fff9f8); font-weight: 600; color: #4a2b2b; }
.today-cell{ background: linear-gradient(90deg, #fff5f3, #fff); border-inline-start: 3px solid var(--maron-accent); }

.period-column{ text-align: center; min-width: 140px; }
.period-cell{ padding: .65rem .5rem; vertical-align: top; position: relative; transition: background-color .15s ease, box-shadow .15s ease; }
.period-cell:hover{ background: #fafafa; box-shadow: inset 0 0 0 1px rgba(0,0,0,.04); }
.period-cell.has-class{ background: #fffdfa; }

/* Current period highlight */
.period-cell.current-period{ outline: 2px solid #22c55e; box-shadow: 0 0 0 2px #22c55e22; background: #f0fdf4; }

/* Content blocks */
.period-content{ display: grid; gap: .35rem; align-items: start; }
.subject-badge{ display: inline-flex; align-items: center; gap: .4rem; padding: .25rem .5rem; border-radius: 999px; font-weight: 600; box-shadow: 0 1px 0 rgba(0,0,0,.04) inset; }
.subject-name{ line-height: 1; }
.classroom-info{ display:flex; align-items:center; gap:.5rem; }
.classroom-badge{ display:inline-flex; align-items:center; gap:.35rem; padding: .15rem .5rem; border:1px solid currentColor; border-radius: 999px; font-size: .8rem; background: #fff; }
.time-info{ display:flex; align-items:center; gap:.35rem; color:#6b7280; font-size:.85rem; }

.empty-period{ display:flex; align-items:center; justify-content:center; min-height: 54px; color:#c4c4c4; }

/* Legend */
.color-legend{ border-top: 1px dashed rgba(0,0,0,.08); background: #fff; padding: .75rem 1rem; display:grid; gap:.75rem; }
.legend-title{ display:flex; align-items:center; gap:.5rem; font-weight:700; color:#5a3b3b; }
.legend-items{ display:flex; flex-wrap: nowrap; overflow-x: auto; gap:.75rem; padding-block:.25rem; }
.legend-item{ display:flex; align-items:center; gap:.5rem; white-space: nowrap; }
.legend-color{ width: 18px; height: 18px; border-radius:4px; box-shadow: 0 0 0 1px rgba(0,0,0,.06) inset; }
.legend-label{ font-size:.9rem; color:#444; }

/* Live clock in stats card */
.live-clock{
  font-size: 1.125rem;
  letter-spacing: 0.5px;
  color: var(--maron-primary);
}

/* Mini table styles */
.mini-table-wrap{ overflow-x:auto; height:100%; }
.mini-table{ width:100%; border-collapse:separate; border-spacing:0; border:1px solid rgba(0,0,0,.06); border-radius:10px; overflow:hidden; }
.mini-table thead th,
.mini-table tbody td{ text-align:center; vertical-align: middle; }
.mini-table thead th{ background:#faf6f5; color:#5a3b3b; font-weight:700; padding:.5rem .6rem; border-bottom:1px solid rgba(0,0,0,.06); white-space:nowrap; }
.mini-table tbody td{ padding:.55rem .6rem; border-inline-start:1px solid rgba(0,0,0,.06); white-space:nowrap; }
.mini-table tbody td:first-child{ border-inline-start:none; }

/* Compact stats row */
.mini-stats{ display:grid; grid-template-columns: repeat(3, 1fr); gap:.5rem; height:100%; align-content:center; }
.mini-stat{ display:flex; align-items:center; justify-content:center; text-align:center; flex-direction:column; gap:.35rem; padding:.45rem .5rem; border:1px dashed rgba(0,0,0,.08); border-radius:8px; background:#fff; }
.mini-stat .label{ color:#6b7280; font-size:.85rem; }
.mini-stat .value{ font-weight:700; color:#4a2b2b; }

/* 2px maroon border for outer cards */
.outlined-card{ border: 2px solid var(--maron-primary, #7b1e1e); border-radius: 12px; }

/* Toolbar */
.timetable-toolbar{ display:flex; align-items:center; gap:.5rem; padding:.5rem .75rem; border-bottom:1px solid rgba(0,0,0,.06); background: #fff; position: sticky; top: 0; z-index: 5; }
.tt-btn{ display:inline-flex; align-items:center; gap:.4rem; padding:.35rem .6rem; border:1px solid rgba(0,0,0,.08); background:#fff; border-radius:8px; cursor:pointer; color:#4a2b2b; transition: background .15s ease, box-shadow .15s ease; }
.tt-btn:hover{ background:#fff8f7; box-shadow:0 1px 4px rgba(0,0,0,.06); }
.tt-toggle{ display:inline-flex; align-items:center; gap:.35rem; color:#4a2b2b; font-size:.9rem; }
.tt-toggle input{ accent-color: var(--maron-primary, #7b1e1e); }

/* Prefs panel */
.prefs-panel{ position: relative; border-top:1px dashed rgba(0,0,0,.08); background:#fff; }
.prefs-header{ display:flex; align-items:center; justify-content:space-between; padding:.5rem .75rem; }
.prefs-header .title{ display:flex; align-items:center; gap:.5rem; font-weight:700; color:#4a2b2b; }
.prefs-body{ display:grid; gap:.5rem; padding:.5rem .75rem .75rem; }
.prefs-body .row-item{ display:flex; align-items:center; gap:.5rem; }
.prefs-body input{ accent-color: var(--maron-primary, #7b1e1e); }

/* Progress bar in current period */
.progress-wrap{ position:absolute; left:8px; right:8px; bottom:6px; height:6px; background:#eafff0; border-radius:999px; overflow:hidden; box-shadow: inset 0 0 0 1px #22c55e22; }
.progress-bar{ height:100%; background: linear-gradient(90deg,#16a34a,#22c55e); transition: width .6s ease; }

/* Dense mode adjustments */
.timetable-wrapper.dense .period-cell{ padding:.45rem .4rem; }
.timetable-wrapper.dense .subject-badge{ font-size:.8rem; }

/* Scale down table content inside timetable card by 5% (width and height) */
.tt-scale-95{ transform: scale(0.95); transform-origin: top center; }

/* Page-level adjustments to avoid window scrollbars on timetable page */
.timetable-page{
  gap: .5rem; /* override gap-3 */
  max-width: 100%;
  overflow: hidden; /* prevent accidental page scrollbars */
  transform: scale(0.965);
  transform-origin: top center;
}

/* Slightly reduce default card padding inside this page */
.timetable-page :deep(.ds-card){ padding: var(--space-4); }

/* Compact the toolbar and legend a bit */
.timetable-toolbar{ padding:.4rem .6rem; }
.color-legend{ padding: .5rem .75rem; }
.legend-items{ gap: .5rem; }

/* Make timetable table content a bit denser */
.timetable-page .timetable-modern{ font-size: .95rem; min-width: unset; }
.timetable-page .timetable-th{ padding: .6rem .5rem; }
.timetable-page .period-cell{ padding: .5rem .45rem; }
.timetable-page .empty-period{ min-height: 46px; }

/* Reduce min-widths to avoid horizontal overflow */
.timetable-page .day-column{ min-width: 110px; }
.timetable-page .period-column{ min-width: 120px; }

/* Mini cards compact */
.timetable-page .mini-table thead th{ padding:.4rem .5rem; }
.timetable-page .mini-table tbody td{ padding:.45rem .5rem; }
.timetable-page .mini-stats{ gap:.4rem; }
.timetable-page .mini-stat{ gap:.3rem; padding:.35rem .4rem; }
.timetable-page .live-clock{ font-size: 1rem; }

/* Print styles */
@media print {
  .outlined-card, .timetable-card{ border:none !important; box-shadow:none !important; }
  .timetable-toolbar, .prefs-panel, .mini-table-wrap, .mini-stats, .outlined-card:first-of-type{ display:none !important; }
  .timetable-modern thead th{ position: static !important; box-shadow:none !important; }
}
</style>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, computed } from 'vue';
import { useFullscreen } from '@vueuse/core';
import { getTeacherTimetableWeekly } from '../../../shared/api/client';
import { formatDateDMY } from '../../../shared/utils/date';
import DsCard from '../../../components/ui/DsCard.vue';
import DsBadge from '../../../components/ui/DsBadge.vue';
import { useTeacherPrefs } from '../../../app/stores/teacherPrefs';

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
  // Expect 'HH:MM[:SS]' — show only HH:MM using Latin numerals
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
  const jsDay = new Date().getDay(); // Sun=0, Mon=1, Tue=2, ...
  // Convert to school format: Sun=1, Mon=2, Tue=3, Wed=4, Thu=5, Fri=6, Sat=7
  const schoolDow = jsDay === 0 ? 1 : (jsDay + 1);
  return d === schoolDow;
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

// Remaining time for current period as small mm:ss (or h:mm:ss if > 1h)
function remainingTime(d: number, p: number): string | '' {
  // Establish reactive dependency on the ticking ref
  void secondTick.value;

  if (!isCurrentPeriod(d, p)) return '';
  const times = cellTime(d, p);
  if (!times) return '';
  const end = times[1];
  const [endH, endM] = end.split(':').map(Number);
  const now = new Date();
  const endDate = new Date();
  endDate.setHours(endH, endM, 0, 0);
  let diffSec = Math.floor((endDate.getTime() - now.getTime()) / 1000);
  if (diffSec < 0) diffSec = 0;

  const h = Math.floor(diffSec / 3600);
  const m = Math.floor((diffSec % 3600) / 60);
  const s = diffSec % 60;

  const pad = (n: number) => n.toString().padStart(2, '0');
  if (h > 0) return `${h}:${pad(m)}:${pad(s)}`;
  return `${pad(m)}:${pad(s)}`;
}

// Progress percentage for the running period
function periodProgress(d: number, p: number): number {
  void secondTick.value;
  const t = cellTime(d,p);
  if (!t) return 0;
  const [start,end] = t;
  const [sh,sm] = start.split(':').map(Number);
  const [eh,em] = end.split(':').map(Number);
  const startDate = new Date(); startDate.setHours(sh,sm,0,0);
  const endDate = new Date();   endDate.setHours(eh,em,0,0);
  const total = endDate.getTime() - startDate.getTime();
  const now = Date.now();
  const passed = Math.min(Math.max(now - startDate.getTime(), 0), total);
  return total > 0 ? Math.round((passed/total)*100) : 0;
}

// UI state and preferences
const prefs = useTeacherPrefs();
const showPrefs = ref(false);
const timetableRef = ref<HTMLElement|null>(null);
const { isFullscreen, toggle } = useFullscreen(timetableRef);

function handlePrint(){
  try { window.print(); } catch(_) {}
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

// Live day/date/time (Arabic) for the header card
const liveDay = ref<string>('');
const liveHijri = ref<string>('');
const liveDate = ref<string>('');
const liveTime = ref<string>('');
// A ticking ref to trigger reactive updates each second (used by countdown)
const secondTick = ref<number>(0);
let _clockTimer: any = null;

function updateNowClock(){
  const now = new Date();
  // Arabic long weekday with Latin numerals
  liveDay.value = new Intl.DateTimeFormat('ar-SA-u-nu-latn', { weekday: 'long' }).format(now);
  // Hijri date using Islamic calendar with Latin numerals
  try {
    liveHijri.value = new Intl.DateTimeFormat('ar-SA-u-ca-islamic-nu-latn', { day: 'numeric', month: 'long', year: 'numeric' }).format(now);
  } catch(_){
    // Fallback if calendar not supported
    liveHijri.value = new Intl.DateTimeFormat('ar-SA-u-nu-latn', { day: 'numeric', month: 'long', year: 'numeric' }).format(now);
  }
  // Gregorian date shown as DD:MM:YYYY with Latin numerals
  liveDate.value = formatDateDMY(now);
  // Live time HH:MM:SS with Latin numerals
  liveTime.value = new Intl.DateTimeFormat('ar-SA-u-nu-latn', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }).format(now);
  // Bump the tick to re-compute countdowns
  secondTick.value = (secondTick.value + 1) % 1_000_000_000;
}

let _escHandler: any = null;

onMounted(() => {
  try { updateNowClock(); } catch(_) {}
  try { _clockTimer = setInterval(updateNowClock, 1000); } catch(_) {}
  // Auto fullscreen if enabled
  try { if (prefs.autoFullscreen && !isFullscreen.value) toggle(); } catch(_) {}
  // Keyboard: ESC to close prefs
  try {
    _escHandler = (e: KeyboardEvent) => { if (e.key === 'Escape') { showPrefs.value = false } };
    document.addEventListener('keydown', _escHandler);
  } catch(_) {}
});

onUnmounted(() => {
  try { if (_clockTimer) clearInterval(_clockTimer); } catch(_) {}
  try { if (_escHandler) document.removeEventListener('keydown', _escHandler); } catch(_) {}
});

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

/* Small green countdown badge near the green dot */
.countdown-badge {
  position: absolute;
  top: 6px;
  left: 26px; /* next to the dot */
  padding: 2px 6px;
  font-size: 0.72rem;
  font-weight: 700;
  line-height: 1.1;
  color: #16a34a; /* green text */
  background: #eafff0; /* very light green background */
  border: 1px solid #22c55e;
  border-radius: 999px;
  box-shadow: 0 1px 4px rgba(16, 185, 129, 0.25);
  pointer-events: none; /* avoid interfering with hover */
  z-index: 3;
}
@media (max-width: 576px) {
  .countdown-badge { font-size: 0.66rem; padding: 1px 5px; left: 24px; top: 6px; }
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