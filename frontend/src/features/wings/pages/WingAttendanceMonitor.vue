<template>
  <section class="d-grid gap-3 page-grid page-grid-wide" dir="rtl">
    <!-- صفحة مراقبة حضور الجناح - رأس موحّد مع أيقونة الطباعة -->
    <WingPageHeader :icon="tileMeta.icon" :title="tileMeta.title" :color="tileMeta.color">
      <template #actions>
        <span class="d-inline-flex align-items-center gap-2 flex-wrap align-items-center">
          <span class="small text-muted" aria-live="polite">
            <template v-if="isToday">اليوم: {{ selectedDateDMY }} • {{ liveTime }}</template>
            <template v-else>التاريخ: {{ selectedDateDMY }}</template>
          </span>
        </span>
        <WingWingPicker id="pick-monitor-wing" />
      </template>
    </WingPageHeader>

    <!-- شريط أدوات التصفية -->
    <div class="auto-card p-2 d-flex align-items-center gap-2 flex-wrap" role="search" aria-label="مرشحات مراقبة الحضور">
      <div class="d-flex align-items-center gap-2 flex-wrap">
        <label class="form-label m-0 small">التاريخ</label>
        <DatePickerDMY
          :id="'wing-monitor-date'"
          :aria-label="'اختيار التاريخ'"
          wrapperClass="m-0"
          inputClass="form-control form-control-sm w-auto"
          v-model="dateDMY"
          @change="onDateChanged"
        />
      </div>
      <div class="d-flex align-items-center gap-2 flex-wrap ms-3">
        <label class="form-label m-0 small">الوضع</label>
        <div class="btn-group btn-group-sm" role="group" aria-label="وضع العرض">
          <button type="button" class="btn" :class="mode==='daily'? 'btn-primary' : 'btn-outline-primary'" @click="setMode('daily')">يومي</button>
          <button type="button" class="btn" :class="mode==='period'? 'btn-primary' : 'btn-outline-primary'" @click="setMode('period')">حسب الحصص</button>
        </div>
      </div>

      <!-- مرشّح الصفوف -->
      <div class="dropdown ms-3">
        <button class="btn btn-sm btn-outline-secondary dropdown-toggle" data-bs-toggle="dropdown" data-bs-display="static" type="button" aria-label="ترشيح الصفوف">{{ classesLabel }}</button>
        <ul class="dropdown-menu dropdown-menu-end p-2 small" style="min-width: 260px; max-height: 300px; overflow: auto">
          <li class="px-2 pb-2 d-flex gap-1 flex-wrap">
            <button class="btn btn-light btn-sm" @click="selectAllClasses">الكل</button>
            <button class="btn btn-light btn-sm" @click="clearAllClasses">إلغاء</button>
            <button class="btn btn-light btn-sm" @click="invertClasses">عكس</button>
          </li>
          <li v-for="opt in classOptions" :key="'cl-' + opt.id" class="dropdown-item d-flex align-items-center gap-2">
            <input class="form-check-input m-0" type="checkbox" :id="'cl-' + opt.id" :checked="selectedClassesSet.has(opt.id)" @change="toggleClass(opt.id)" />
            <label class="form-check-label flex-fill" :for="'cl-' + opt.id">{{ opt.name || ('صف #' + opt.id) }}</label>
          </li>
          <li v-if="classOptions.length === 0" class="dropdown-item text-muted">لا توجد صفوف</li>
        </ul>
      </div>

      <!-- مرشّح الحصص -->
      <div class="dropdown ms-1">
        <button class="btn btn-sm btn-outline-secondary dropdown-toggle" data-bs-toggle="dropdown" data-bs-display="static" type="button" aria-label="ترشيح الحصص">{{ periodsLabel }}</button>
        <ul class="dropdown-menu dropdown-menu-end p-2 small" style="min-width: 220px; max-height: 300px; overflow: auto">
          <li class="px-2 pb-2 d-flex gap-1 flex-wrap">
            <button class="btn btn-light btn-sm" @click="selectAllPeriods">الكل</button>
            <button class="btn btn-light btn-sm" @click="clearAllPeriods">إلغاء</button>
            <button class="btn btn-light btn-sm" @click="invertPeriods">عكس</button>
          </li>
          <li v-for="p in periodOptions" :key="'p-' + p" class="dropdown-item d-flex align-items-center gap-2">
            <input class="form-check-input m-0" type="checkbox" :id="'prd-' + p" :checked="selectedPeriodsSet.has(p)" @change="togglePeriod(p)" />
            <label class="form-check-label flex-fill" :for="'prd-' + p">حصة {{ p }}</label>
          </li>
          <li v-if="periodOptions.length === 0" class="dropdown-item text-muted">لا توجد حصص</li>
        </ul>
      </div>

      <!-- مرشّح المعلم -->
      <div class="dropdown ms-1">
        <button class="btn btn-sm btn-outline-secondary dropdown-toggle" data-bs-toggle="dropdown" data-bs-display="static" type="button" aria-label="ترشيح المعلم">{{ teachersLabel }}</button>
        <ul class="dropdown-menu dropdown-menu-end p-2 small" style="min-width: 260px; max-height: 300px; overflow: auto">
          <li class="px-2 pb-2 d-flex gap-1 flex-wrap">
            <button class="btn btn-light btn-sm" @click="selectAllTeachers">الكل</button>
            <button class="btn btn-light btn-sm" @click="clearAllTeachers">إلغاء</button>
            <button class="btn btn-light btn-sm" @click="invertTeachers">عكس</button>
          </li>
          <li v-for="t in teacherOptions" :key="'t-' + (t.id || t.name)" class="dropdown-item d-flex align-items-center gap-2">
            <input class="form-check-input m-0" type="checkbox" :id="'tch-' + (t.id || t.name)" :checked="selectedTeachersSet.has(t.id || t.name)" @change="toggleTeacher(t.id || t.name)" />
            <label class="form-check-label flex-fill" :for="'tch-' + (t.id || t.name)">{{ t.name || ('#' + t.id) }}</label>
          </li>
          <li v-if="teacherOptions.length === 0" class="dropdown-item text-muted">لا يوجد معلمون</li>
        </ul>
      </div>

      <div class="d-flex align-items-center gap-2 ms-3">
        <button class="btn btn-sm" :class="isPaused? 'btn-outline-secondary' : 'btn-outline-success'" @click="toggleLive" :aria-pressed="!isPaused" :aria-label="isPaused? 'تشغيل التحديث الحي' : 'إيقاف التحديث الحي'">
          <Icon :icon="isPaused? 'solar:play-bold-duotone' : 'solar:pause-bold-duotone'" />
          <span class="ms-1">تحديث حي</span>
        </button>
      </div>
      <span class="ms-auto small text-muted" aria-live="polite">
        {{ subtitle }}
        <template v-if="lastUpdated"> • آخر تحديث: {{ lastUpdated }}</template>
      </span>
    </div>

    <!-- بطاقات مؤشرات مختصرة -->
    <div class="row g-3">
      <div class="col-6 col-md-3">
        <div class="card h-100">
          <div class="card-body d-flex flex-column">
            <div class="text-muted small">إجمالي الصفوف</div>
            <div class="display-6" dir="ltr">{{ kpis.classes ?? '--' }}</div>
          </div>
        </div>
      </div>
      <div class="col-6 col-md-3">
        <div class="card h-100">
          <div class="card-body d-flex flex-column">
            <div class="text-muted small">إجمالي الطلبة</div>
            <div class="display-6" dir="ltr">{{ kpis.students ?? '--' }}</div>
          </div>
        </div>
      </div>
      <div class="col-6 col-md-3">
        <div class="card h-100">
          <div class="card-body d-flex flex-column">
            <div class="text-muted small">نسبة الحضور</div>
            <div class="display-6" dir="ltr">{{ kpis.attendance_rate ?? '--%' }}</div>
          </div>
        </div>
      </div>
      <div class="col-6 col-md-3">
        <div class="card h-100">
          <div class="card-body d-flex flex-column">
            <div class="text-muted small">عدد التأخرات</div>
            <div class="display-6" dir="ltr">{{ kpis.lates ?? '--' }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- جدول تفصيلي للصفوف -->
    <div class="card">
      <div class="card-body">
        <div class="d-flex align-items-center gap-2 mb-2">
          <Icon icon="solar:radar-2-bold-duotone" class="text-primary" width="22" height="22" />
          <h5 class="m-0 card-title-maroon">تفصيل الصفوف</h5>
          <span class="ms-auto small text-muted" aria-live="polite">{{ filteredRows.length }} عنصر</span>
        </div>

        <div v-if="loading" class="alert alert-light d-flex align-items-center gap-2">
          <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
          <span>جاري تحميل البيانات...</span>
        </div>
        <div v-else-if="error" class="alert alert-danger d-flex align-items-center gap-2">
          <Icon icon="solar:danger-triangle-bold-duotone" />
          <span class="flex-fill">حدث خطأ أثناء التحميل: {{ error }}</span>
          <button class="btn btn-sm btn-outline-light" @click="reloadNow">إعادة المحاولة</button>
        </div>

        <div v-else>
          <div class="table-responsive overflow-visible">
            <table class="table table-sm align-middle print-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>الصف</th>
                  <th>الحصة</th>
                  <th>المادة</th>
                  <th>المعلم</th>
                  <th class="text-center">الحالة</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, i) in filteredRows" :key="row.key">
                  <td class="text-muted">{{ i + 1 }}</td>
                  <td>{{ row.class_name || ('#' + row.class_id) }}</td>
                  <td>حصة {{ row.period_number }}</td>
                  <td>{{ getSubjectName(row) || '-' }}</td>
                  <td>{{ row.teacher_name || ('#' + (row.teacher_id || '')) }}</td>
                  <td class="text-center">
                    <span class="att-chip" :class="row.status === 'entered' ? 'att-entered' : 'att-missing'">
                      {{ row.status === 'entered' ? 'تم الإدخال' : 'بلا إدخال' }}
                    </span>
                  </td>
                </tr>
                <tr v-if="!filteredRows.length">
                  <td colspan="6" class="text-muted">لا توجد صفوف ضمن نطاق الترشيح في هذا التاريخ.</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="mt-2"><StatusLegend /></div>
        </div>
      </div>
    </div>
  </section>
</template>
<script setup lang="ts">
import { Icon } from "@iconify/vue";
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { tiles } from "../../../home/icon-tiles.config";
import WingPageHeader from "../../../components/ui/WingPageHeader.vue";
import WingWingPicker from "../../../components/ui/WingWingPicker.vue";
import DatePickerDMY from "../../../components/ui/DatePickerDMY.vue";
import { useWingContext } from '../../../shared/composables/useWingContext';
import { useWingPrefs } from '../../../shared/composables/useWingPrefs';
import { useRoute, useRouter } from 'vue-router';
import { formatDateDMY, formatISOtoDMY, parseDMYtoISO, toIsoDate } from '../../../shared/utils/date';
import { getWingOverview, getWingMissing, getWingEntered } from '../../../shared/api/client';
import StatusLegend from '../../../components/ui/StatusLegend.vue';

function getSubjectName(it: any): string {
  try {
    const name = it?.subject_name
      ?? it?.subjectName
      ?? it?.subject__name
      ?? it?.tt_subject_name
      ?? it?.subject?.name
      ?? it?.subject_title
      ?? it?.subject_label
      ?? it?.course_name
      ?? it?.course
      ?? it?.subject;
    const s = (name ?? '').toString().trim();
    return s || '';
  } catch {
    return '';
  }
}

const route = useRoute();
const router = useRouter();

const tileMeta = computed(() => tiles.find(t => t.to === "/attendance/wing/monitor") || { title: "مراقبة حضور الجناح", icon: "solar:radar-2-bold-duotone", color: "#0d47a1" });

const { ensureLoaded, wingLabelFull, selectedWingId } = useWingContext();
const { default_date_mode } = useWingPrefs();

const dateDMY = ref<string>("");
const dateISO = computed(() => parseDMYtoISO(dateDMY.value) || toIsoDate(new Date()));
const selectedDateDMY = computed(() => dateDMY.value || formatISOtoDMY(dateISO.value));
const isToday = computed(() => dateISO.value === toIsoDate(new Date()));
const liveTime = ref<string>("");
function updateLiveTime() {
  const now = new Date();
  // ASCII HH:mm only
  const hh = String(now.getHours()).padStart(2, '0');
  const mm = String(now.getMinutes()).padStart(2, '0');
  liveTime.value = `${hh}:${mm}`;
}
let liveClockTimer: any = null;
function startLiveClock() { stopLiveClock(); updateLiveTime(); liveClockTimer = setInterval(updateLiveTime, 60_000); }
function stopLiveClock() { if (liveClockTimer) { clearInterval(liveClockTimer); liveClockTimer = null; } }
const mode = ref<'daily'|'period'>('daily');
const isPaused = ref<boolean>(false);
const lastUpdated = ref<string>("");

function asciiTime(d: Date) {
  const hh = String(d.getHours()).padStart(2, '0');
  const mm = String(d.getMinutes()).padStart(2, '0');
  return `${hh}:${mm}`;
}

function updateLastUpdated() {
  lastUpdated.value = asciiTime(new Date());
}

function setMode(m: 'daily'|'period') {
  mode.value = m;
  syncQuery();
}

function onDateChanged() {
  syncQuery();
  loadData();
}

function syncQuery() {
  const q = { ...route.query } as any;
  const iso = dateISO.value;
  if (iso) q.date = iso; else delete q.date;
  q.mode = mode.value;
  q.paused = isPaused.value ? '1' : undefined;
  router.replace({ query: q }).catch(() => {});
}

// Live polling
let timer: any = null;
const INTERVAL_MS = 15_000; // 15s
function startLive() {
  stopLive();
  if (isPaused.value) return;
  timer = setInterval(() => {
    if (!document.hidden) loadData();
  }, INTERVAL_MS);
}
function stopLive() { if (timer) { clearInterval(timer); timer = null; } }
function toggleLive() { isPaused.value = !isPaused.value; syncQuery(); if (!isPaused.value) { loadData(); startLive(); } else { stopLive(); } }

// KPIs and rows
const kpis = ref<{ classes?: number; students?: number; attendance_rate?: string; lates?: number }>({});

type Row = {
  key: string;
  class_id: number;
  class_name?: string;
  period_number: number;
  subject_id?: number;
  subject_name?: string;
  teacher_id?: number;
  teacher_name?: string;
  status: 'entered' | 'missing';
};
const rows = ref<Row[]>([]);

// Loading/error and progressive rendering
const loading = ref<boolean>(false);
const error = ref<string | null>(null);
const showLimit = ref<number>(300);
const visibleRows = computed(() => filteredRows.value.slice(0, showLimit.value));
const scrollEl = ref<HTMLElement | null>(null);
function onScroll() {
  const el = scrollEl.value as HTMLElement | null;
  if (!el) return;
  const nearBottom = el.scrollTop + el.clientHeight >= el.scrollHeight - 8;
  if (nearBottom && showLimit.value < filteredRows.value.length) {
    showLimit.value = Math.min(filteredRows.value.length, showLimit.value + 300);
  }
}

// ---- Filters (classes, periods, teachers) ----
const classOptions = computed<{ id: number; name?: string }[]>(() => {
  const map = new Map<number, string | undefined>();
  for (const r of rows.value) map.set(r.class_id, r.class_name);
  return Array.from(map.entries())
    .map(([id, name]) => ({ id, name }))
    .sort((a, b) => (a.name || '').localeCompare(b.name || '') || a.id - b.id);
});
const periodOptions = computed<number[]>(() => {
  const set = new Set<number>();
  for (const r of rows.value) set.add(Number(r.period_number));
  return Array.from(set.values()).sort((a, b) => a - b);
});
const teacherOptions = computed<{ id?: number; name?: string }[]>(() => {
  const map = new Map<string, { id?: number; name?: string }>();
  for (const r of rows.value) {
    const id = r.teacher_id || undefined;
    const name = (r.teacher_name || '').toString().trim() || undefined;
    const key = id ? `id:${id}` : name ? `name:${name}` : '';
    if (!key) continue;
    if (!map.has(key)) map.set(key, { id, name });
  }
  return Array.from(map.values()).sort((a, b) => (a.name || '').localeCompare(b.name || ''));
});

const selectedClassesSet = ref<Set<number>>(new Set());
const selectedPeriodsSet = ref<Set<number>>(new Set());
const selectedTeachersSet = ref<Set<number | string>>(new Set());

function parseNumList(val: any): number[] {
  const s = Array.isArray(val) ? val.join(',') : (val || '');
  return s.split(',').map((x: string) => parseInt(String(x).trim(), 10)).filter((n) => Number.isFinite(n));
}

// Initialize from URL/localStorage
function initFiltersFromUrlOrStorage() {
  try {
    const q = route.query as any;
    const cls = parseNumList(q.classes);
    const prd = parseNumList(q.periods);
    const tch = parseNumList(q.teachers);
    const fromLsC = JSON.parse(localStorage.getItem('wing_monitor_classes') || '[]');
    const fromLsP = JSON.parse(localStorage.getItem('wing_monitor_periods') || '[]');
    const fromLsT = JSON.parse(localStorage.getItem('wing_monitor_teachers') || '[]');
    const initC = cls.length ? cls : Array.isArray(fromLsC) ? fromLsC : [];
    const initP = prd.length ? prd : Array.isArray(fromLsP) ? fromLsP : [];
    const initT = tch.length ? tch : Array.isArray(fromLsT) ? fromLsT : [];
    if (initC.length) selectedClassesSet.value = new Set(initC);
    if (initP.length) selectedPeriodsSet.value = new Set(initP);
    if (initT.length) selectedTeachersSet.value = new Set(initT);
  } catch {}
}

// Sync to URL/localStorage
watch(selectedClassesSet, (set) => {
  const ids = Array.from(set.values());
  const q = { ...route.query } as any;
  if (ids.length) q.classes = ids.join(','); else delete q.classes;
  router.replace({ query: q }).catch(() => {});
  try { localStorage.setItem('wing_monitor_classes', JSON.stringify(ids)); } catch {}
}, { deep: true });
watch(selectedPeriodsSet, (set) => {
  const ids = Array.from(set.values());
  const q = { ...route.query } as any;
  if (ids.length) q.periods = ids.join(','); else delete q.periods;
  router.replace({ query: q }).catch(() => {});
  try { localStorage.setItem('wing_monitor_periods', JSON.stringify(ids)); } catch {}
}, { deep: true });
watch(selectedTeachersSet, (set) => {
  const ids = Array.from(set.values()).filter((v) => typeof v === 'number') as number[];
  const q = { ...route.query } as any;
  if (ids.length) q.teachers = ids.join(','); else delete q.teachers;
  router.replace({ query: q }).catch(() => {});
  try { localStorage.setItem('wing_monitor_teachers', JSON.stringify(ids)); } catch {}
}, { deep: true });

// Labels
const classesLabel = computed(() => {
  const total = classOptions.value.length;
  const cnt = selectedClassesSet.value.size;
  if (!total) return 'لا صفوف';
  if (!cnt || cnt === total) return 'كل الصفوف';
  return `صفوف (${cnt}/${total})`;
});
const periodsLabel = computed(() => {
  const total = periodOptions.value.length;
  const cnt = selectedPeriodsSet.value.size;
  if (!total) return 'لا حصص';
  if (!cnt || cnt === total) return 'كل الحصص';
  return `حصص (${cnt}/${total})`;
});
const teachersLabel = computed(() => {
  const total = teacherOptions.value.length;
  const cnt = selectedTeachersSet.value.size;
  if (!total) return 'لا معلمين';
  if (!cnt || cnt === total) return 'كل المعلمين';
  return `معلمين (${cnt}/${total})`;
});

// Toggle helpers
function toggleClass(id: number) { const s = new Set(selectedClassesSet.value); if (s.has(id)) s.delete(id); else s.add(id); selectedClassesSet.value = s; }
function selectAllClasses() { selectedClassesSet.value = new Set(classOptions.value.map(c => c.id)); }
function clearAllClasses() { selectedClassesSet.value = new Set(); }
function invertClasses() { const s = new Set<number>(); for (const c of classOptions.value) if (!selectedClassesSet.value.has(c.id)) s.add(c.id); selectedClassesSet.value = s; }

function togglePeriod(p: number) { const s = new Set(selectedPeriodsSet.value); if (s.has(p)) s.delete(p); else s.add(p); selectedPeriodsSet.value = s; }
function selectAllPeriods() { selectedPeriodsSet.value = new Set(periodOptions.value); }
function clearAllPeriods() { selectedPeriodsSet.value = new Set(); }
function invertPeriods() { const s = new Set<number>(); for (const p of periodOptions.value) if (!selectedPeriodsSet.value.has(p)) s.add(p); selectedPeriodsSet.value = s; }

function toggleTeacher(idOrName: number | string) { const s = new Set(selectedTeachersSet.value); if (s.has(idOrName)) s.delete(idOrName); else s.add(idOrName); selectedTeachersSet.value = s; }
function selectAllTeachers() { const s = new Set<number|string>(); for (const t of teacherOptions.value) s.add(t.id ?? t.name ?? ''); selectedTeachersSet.value = s; }
function clearAllTeachers() { selectedTeachersSet.value = new Set(); }
function invertTeachers() { const s = new Set<number|string>(); for (const t of teacherOptions.value) { const key = t.id ?? t.name ?? ''; if (!selectedTeachersSet.value.has(key)) s.add(key); } selectedTeachersSet.value = s; }

const filteredRows = computed(() => {
  let arr = rows.value.slice();
  if (selectedClassesSet.value.size) arr = arr.filter(r => selectedClassesSet.value.has(r.class_id));
  if (selectedPeriodsSet.value.size) arr = arr.filter(r => selectedPeriodsSet.value.has(r.period_number));
  const teacherIds = new Set(Array.from(selectedTeachersSet.value.values()).filter(v => typeof v === 'number') as number[]);
  if (teacherIds.size) arr = arr.filter(r => teacherIds.has(Number(r.teacher_id || 0)));
  return arr;
});

const subtitle = computed(() => wingLabelFull.value || '');

async function loadData() {
  loading.value = true;
  error.value = null;
  try {
    const params: any = { date: dateISO.value };
    if (selectedWingId?.value) params.wing_id = selectedWingId.value;
    // Load KPIs and per-class/period status in parallel
    const [ov, missing, entered] = await Promise.all([
      getWingOverview(params).catch((e) => { console.warn('overview failed', e); return null; }),
      getWingMissing(params).catch((e) => { console.warn('missing failed', e); return null; }),
      getWingEntered(params).catch((e) => { console.warn('entered failed', e); return null; }),
    ]);
    const k = (ov as any)?.kpis || {};
    kpis.value = {
      classes: undefined,
      students: typeof k.total === 'number' ? k.total : undefined,
      attendance_rate: typeof k.present_pct === 'number' ? `${k.present_pct.toFixed(1)}%` : undefined,
      lates: typeof k.late === 'number' ? k.late : undefined,
    };
    // Merge rows: union of missing and entered by class_id+period
    const map = new Map<string, Row>();
    const pushItem = (it: any, status: 'entered'|'missing') => {
      const cid = Number(it.class_id);
      const per = Number(it.period_number || it.period);
      if (!cid || !per) return;
      const key = `${cid}-${per}`;
      const prev = map.get(key);
      const base: Row = {
        key,
        class_id: cid,
        class_name: it.class_name,
        period_number: per,
        subject_id: (it.subject_id ?? (it.subject && (it.subject.id || it.subject.subject_id))) as any,
        subject_name: getSubjectName(it),
        teacher_id: (it.teacher_id ?? (it.teacher && (it.teacher.id || it.teacher.teacher_id))) as any,
        teacher_name: it.teacher_name,
        status,
      };
      // If both statuses exist, prefer 'entered'
      if (!prev || status === 'entered') map.set(key, base);
    };
    const missingItems = (missing as any)?.items || [];
    for (const it of missingItems) pushItem(it, 'missing');
    const enteredItems = (entered as any)?.items || [];
    for (const it of enteredItems) pushItem(it, 'entered');
    // Sort by class then period
    rows.value = Array.from(map.values()).sort((a, b) => (a.class_name || '').localeCompare(b.class_name || '') || a.class_id - b.class_id || a.period_number - b.period_number);
    // Reset progressive window after new data
    showLimit.value = 300;
  } catch (e: any) {
    error.value = e?.message || 'تعذر تحميل بيانات المراقبة';
  } finally {
    updateLastUpdated();
    loading.value = false;
  }
}

watch([dateISO, mode, selectedWingId], () => {
  loadData();
});

onMounted(async () => {
  await ensureLoaded();
  // Initialize from query
  const qd = String(route.query.date || '').trim();
  if (qd) dateDMY.value = formatISOtoDMY(qd); else dateDMY.value = formatDateDMY(new Date());
  const qm = String(route.query.mode || '').trim();
  if (qm === 'daily' || qm === 'period') mode.value = qm as any;
  isPaused.value = String(route.query.paused || '') === '1';
  loadData();
  startLive();
  document.addEventListener('visibilitychange', onVisChange);
});

function onVisChange() { if (!document.hidden && !isPaused.value) { loadData(); } }

onBeforeUnmount(() => {
  stopLive();
  document.removeEventListener('visibilitychange', onVisChange);
});
</script>
<style scoped>
.table-card { margin-top: 0.5rem; }
</style>
