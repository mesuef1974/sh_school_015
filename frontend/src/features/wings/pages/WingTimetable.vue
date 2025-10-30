<template>
  <section class="d-grid gap-3 page-grid page-grid-wide" dir="rtl">
    <div class="d-flex align-items-center gap-2 mb-2 header-bar frame">
      <Icon :icon="tileMeta.icon" class="header-icon" width="28" height="28" :style="{ color: tileMeta.color }" />
      <div>
        <div class="fw-bold">{{ tileMeta.title }}</div>
        <div class="text-muted small" v-if="wingLabelFull">{{ wingLabelFull }}</div>
        <div class="text-muted small" v-else>ملخص ومؤشرات اليوم لنطاق جناحك</div>
      </div>
      <span class="ms-auto"></span>
      <!-- Merged toolbar controls into the page header -->
      <div class="d-flex align-items-center gap-2 flex-wrap toolbar-controls">
        <div class="d-flex align-items-center gap-2">
          <Icon icon="solar:home-2-bold-duotone" />
          <label class="visually-hidden" for="wingSelect">اختر الجناح</label>
          <select
            id="wingSelect"
            aria-label="اختيار الجناح"
            class="form-select form-select-sm"
            v-model.number="wingId"
            @change="loadData"
          >
            <option :value="null" disabled>اختر الجناح</option>
            <option v-for="(name, id) in wingOptions" :key="id" :value="Number(id)">
              {{ name }}
            </option>
          </select>
        </div>
        <div class="d-flex align-items-center gap-2">
          <Icon icon="solar:calendar-bold-duotone" />
          <label class="visually-hidden" for="tt-date">التاريخ</label>
          <DatePickerDMY
            :id="'tt-date'"
            :aria-label="'اختيار التاريخ'"
            inputClass="form-control form-control-sm"
            wrapperClass="m-0"
            v-model="dateStr"
            @change="loadData"
          />
        </div>
        <!-- Mode toggle hidden: separated into two pages (daily/weekly) -->
        <div class="btn-group btn-group-sm" role="group" aria-label="وضع العرض" style="display:none">
          <button
            type="button"
            class="btn"
            :class="mode === 'daily' ? 'btn-primary' : 'btn-outline-secondary'"
            @click="setMode('daily')"
          >
            اليوم
          </button>
          <button
            type="button"
            class="btn"
            :class="mode === 'weekly' ? 'btn-primary' : 'btn-outline-secondary'"
            @click="setMode('weekly')"
          >
            أسبوع
          </button>
        </div>
        <!-- Weekly-only column width controls -->
        <DsButton
          size="sm"
          variant="outline"
          icon="solar:printer-bold-duotone"
          @click="printPage"
          aria-label="طباعة الجدول"
        >طباعة</DsButton>
        <DsButton
          size="sm"
          variant="outline"
          icon="solar:refresh-bold-duotone"
          :loading="loading"
          @click="loadData"
          aria-label="تحديث البيانات"
        >تحديث</DsButton>
      </div>
    </div>

    <div class="auto-card p-3 d-flex align-items-center gap-2 flex-wrap toolbar-card d-none">
      <span class="vr mx-2 d-none d-sm-block"></span>

      <div class="d-flex align-items-center gap-2 flex-wrap ms-auto toolbar-controls">
        <div class="d-flex align-items-center gap-2">
          <Icon icon="solar:home-2-bold-duotone" />
          <label class="visually-hidden" for="wingSelect">اختر الجناح</label>
          <select
            id="wingSelect"
            aria-label="اختيار الجناح"
            class="form-select form-select-sm"
            v-model.number="wingId"
            @change="loadData"
          >
            <option :value="null" disabled>اختر الجناح</option>
            <option v-for="(name, id) in wingOptions" :key="id" :value="Number(id)">
              {{ name }}
            </option>
          </select>
        </div>
        <div class="d-flex align-items-center gap-2">
          <Icon icon="solar:calendar-bold-duotone" />
          <label class="visually-hidden" for="tt-date-2">التاريخ</label>
          <DatePickerDMY
            :id="'tt-date-2'"
            :aria-label="'اختيار التاريخ'"
            inputClass="form-control form-control-sm"
            wrapperClass="m-0"
            v-model="dateStr"
            @change="loadData"
          />
        </div>
        <div class="btn-group btn-group-sm" role="group" aria-label="وضع العرض" style="display:none">
          <button type="button" class="btn" :class="mode === 'daily' ? 'btn-primary' : 'btn-outline-secondary'" @click="setMode('daily')">اليوم</button>
          <button type="button" class="btn" :class="mode === 'weekly' ? 'btn-primary' : 'btn-outline-secondary'" @click="setMode('weekly')">أسبوع</button>
        </div>
        <DsButton size="sm" variant="outline" icon="solar:printer-bold-duotone" @click="printPage" aria-label="طباعة الجدول">طباعة</DsButton>
        <DsButton size="sm" variant="outline" icon="solar:refresh-bold-duotone" :loading="loading" @click="loadData" aria-label="تحديث البيانات">تحديث</DsButton>
        <div class="vr d-none d-sm-block"></div>
      </div>
    </div>

    <!-- Print-only header -->
    <div class="auto-card p-2 print-header" aria-hidden="true">
      <div class="d-flex align-items-center gap-2">
        <Icon icon="solar:printer-bold-duotone" />
        <div class="fw-bold">
          {{
            mode === "daily"
              ? "الجدول اليومي — " + formattedDate + " — " + dayNameAr(dateStr)
              : "الجدول الأسبوعي"
          }}
          <span v-if="wingLabel"> — {{ wingLabel }}</span>
        </div>
      </div>
    </div>

    <div v-if="loading" class="auto-card p-4 text-center">
      <Icon icon="solar:refresh-bold-duotone" class="animate-spin text-4xl" />
      <div class="text-muted mt-2 small">جاري تحميل الجدول...</div>
    </div>

    <div v-else-if="error" class="alert alert-danger">حدث خطأ أثناء التحميل: {{ error }}</div>

    <!-- Empty state -->
    <div v-else-if="isEmpty" class="auto-card p-4 text-center">
      <Icon icon="solar:inbox-line-bold-duotone" class="text-5xl mb-2" style="opacity: 0.4" />
      <div class="h6 mb-1">لا توجد بيانات للعرض</div>
      <div class="text-muted small" v-if="meta.reason === 'no_wing'">
        لا يوجد جناح مخصص لحسابك. عيّن نفسك كمشرف لجناح في لوحة الإدارة (Wing.supervisor).
      </div>
      <div class="text-muted small" v-else-if="meta.reason === 'no_term'">
        لا يوجد فصل دراسي حالي (is_current=True). أنشئ فصلًا وحدده كحالي.
      </div>
      <div class="text-muted small" v-else-if="meta.reason === 'no_classes'">
        لا توجد صفوف مرتبطة بهذا الجناح. اربط بعض الصفوف بالجناح.
      </div>
      <div class="text-muted small" v-else-if="meta.reason === 'no_entries_today'">
        لا توجد حصص مجدولة لهذا اليوم ضمن الجناح/الفصل الدراسي الحالي.
      </div>
      <div class="text-muted small" v-else>تحقق من اختيار الجناح والتاريخ</div>
    </div>

    <!-- Daily view (updated): الصفوف = الفصول، الأعمدة = الحصص مع ترويسة مدمجة -->
    <div v-else-if="mode === 'daily'" class="auto-card p-0 overflow-auto">
      <div class="p-3 d-flex align-items-center gap-2 border-bottom">
        <Icon icon="solar:calendar-date-bold-duotone" />
        <div class="fw-bold">جدول اليوم — {{ formattedDate }} — {{ dayNameAr(dateStr) }}</div>
        <span class="ms-auto small text-muted">{{ groupedDaily.total }} عنصر</span>
      </div>
      <div class="in-card-98">
        <div class="tt-daily-scroller">
          <table class="tt-daily-table" dir="rtl" aria-label="جدول يومي: الفصول صفوف والحصص أعمدة">
            <colgroup>
              <col style="min-width: 160px" />
              <col v-for="p in PERIODS" :key="'cg-p-'+p" style="min-width: 140px" />
            </colgroup>
            <thead>
              <tr>
                <th class="tt-daily-th tt-daily-th-sticky">الفصل</th>
                <th v-for="p in PERIODS" :key="'hd-p-'+p" class="tt-daily-th">
                  <div class="fw-bold">حصة {{ p }}</div>
                  <div v-if="timeRange(p)" class="small text-muted one-line">{{ timeRange(p) }}</div>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(cls, idx) in dailyClassList" :key="'row-cls-'+cls.id">
                <th scope="row" class="tt-daily-th tt-daily-th-sticky">
                  <span class="badge text-bg-secondary no-wrap class-name-badge">{{ cls.name || ('صف #'+cls.id) }}</span>
                </th>
                <td v-for="p in PERIODS" :key="'cell-'+cls.id+'-'+p" class="tt-daily-td">
                  <template v-if="dailyItemFor(cls.id, p)">
                    <div
                      class="period-cell"
                      :style="{ backgroundColor: dailyItemFor(cls.id, p)?.color || '#f5f7fb' }"
                      :title="
                        (dailyItemFor(cls.id, p)?.subject_name || 'مادة') +
                        ' — ' + (dailyItemFor(cls.id, p)?.teacher_name || '—') +
                        (periodTimes[p] ? (' — ' + timeRange(p)) : '')
                      "
                    >
                      <div class="cell-subject one-line">
                        <Icon :icon="subjectIcon(dailyItemFor(cls.id, p)?.subject_name)" class="subject-icon" />
                        <span class="subject-name truncate-1">{{ dailyItemFor(cls.id, p)?.subject_name || 'مادة' }}</span>
                      </div>
                      <div class="cell-teacher one-line truncate-1">{{ dailyItemFor(cls.id, p)?.teacher_name || '—' }}</div>
                    </div>
                  </template>
                  <span v-else class="text-muted">—</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Weekly view: الأيام صفوف والحصص أعمدة -->
    <div v-else class="auto-card p-0 overflow-hidden">
      <div class="p-3 d-flex align-items-center gap-2 border-bottom">
        <Icon icon="solar:calendar-bold-duotone" />
        <div class="fw-bold">الجدول الأسبوعي للفصل</div>
        <span class="ms-auto small text-muted">فصول × أيام (الأحد → الخميس)</span>
      </div>
      <div class="in-card-98">
        <div class="tt7-wrapper">
          <div class="tt7-scroller">
            <table class="tt7-table" dir="rtl" aria-label="جدول أسبوعي: الأيام صفوف والحصص أعمدة">
              <colgroup>
                <col :style="{ minWidth: weeklyColPx(0) }" />
                <col :style="{ minWidth: weeklyColPx(1) }" />
                <col v-for="(p, i) in PERIODS" :key="'cg-p-' + p" :style="{ minWidth: weeklyColPx(i + 2) }" />
              </colgroup>
              <thead>
                <tr>
                  <th class="tt7-th tt7-th-sticky tt7-th-period resizable-th">الفصل</th>
                  <th class="tt7-th resizable-th">اليوم</th>
                  <th v-for="p in PERIODS" :key="'ph-' + p" class="tt7-th resizable-th">حصة {{ p }}</th>
                </tr>
              </thead>
              <tbody>
                <template v-for="(cls, ci) in classList" :key="'grp-' + cls.id">
                  <tr v-for="(d, idx) in DAYS5" :key="'row-c-' + cls.id + '-d-' + d[0]" :class="{ 'class-separator': ci > 0 && idx === 0 }">
                    <th v-if="idx === 0" class="tt7-th tt7-th-period tt7-th-sticky" :rowspan="DAYS5.length">
                      <div class="hdr-line">
                        <span class="badge text-bg-secondary no-wrap class-name-badge">{{ cls.name }}</span>
                      </div>
                    </th>
                    <th class="tt7-th">{{ d[1] }}</th>
                    <td v-for="p in PERIODS" :key="'cell-' + cls.id + '-' + d[0] + '-' + p" class="tt7-td">
                      <div class="tt7-cell">
                        <template v-if="classDayPeriodItem(cls.id, d[0], p)">
                          <div
                            class="mini-cell"
                            :style="{ backgroundColor: classDayPeriodItem(cls.id, d[0], p)?.color || '#f5f7fb' }"
                            :title="
                              (classDayPeriodItem(cls.id, d[0], p)?.subject_name || 'مادة') +
                              ' — ' +
                              (classDayPeriodItem(cls.id, d[0], p)?.teacher_name || '—') +
                              ' — حصة ' + (p || '')
                            "
                          >
                            <div class="mini-subj one-line">
                              <Icon :icon="subjectIcon(classDayPeriodItem(cls.id, d[0], p)?.subject_name)" class="subject-icon" />
                              <span class="subject-name truncate-1">{{ classDayPeriodItem(cls.id, d[0], p)?.subject_name || 'مادة' }}</span>
                            </div>
                            <div class="mini-teacher one-line truncate-1">
                              {{ classDayPeriodItem(cls.id, d[0], p)?.teacher_name || '—' }}
                            </div>
                          </div>
                        </template>
                        <span v-else class="text-muted">—</span>
                      </div>
                    </td>
                  </tr>
                </template>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, reactive, watch, nextTick } from 'vue';
import { tiles } from '../../../home/icon-tiles.config';
import { useRoute } from 'vue-router';
const route = useRoute();
const tileMeta = computed(() => {
  const name = route.name as string | undefined;
  if (name === 'wing-timetable-weekly') {
    return tiles.find(t => t.to === '/wing/timetable/weekly') || { title: 'الجدول الأسبوعي', icon: 'solar:calendar-bold-duotone', color: '#5dade2' };
  }
  return tiles.find(t => t.to === '/wing/timetable/daily') || { title: 'جدول اليوم', icon: 'solar:clock-circle-bold-duotone', color: '#5dade2' };
});
import { onBeforeUnmount } from "vue";
import DsButton from "../../../components/ui/DsButton.vue";
import { getWingMe, getWingTimetable } from "../../../shared/api/client";
import { formatDateDMY } from "../../../shared/utils/date";
import DatePickerDMY from "../../../components/ui/DatePickerDMY.vue";
// Wing context: ensure dynamic subtitle like other Wing pages
import { useWingContext } from '../../../shared/composables/useWingContext';
const { ensureLoaded, wingLabelFull } = useWingContext();
onMounted(() => { try { ensureLoaded(); } catch {} });

const today = new Date();
const iso = (d: Date) => d.toISOString().slice(0, 10);
const dateStr = ref<string>(iso(today));
const mode = ref<"daily" | "weekly">("daily");
// Lock mode based on route (two separate pages)
if ((route.name as string | undefined) === 'wing-timetable-weekly') {
  mode.value = 'weekly';
} else {
  mode.value = 'daily';
}
watch(
  () => route.name,
  (nv) => {
    if (nv === 'wing-timetable-weekly') mode.value = 'weekly';
    else mode.value = 'daily';
  }
);
const loading = ref(false);
const error = ref<string | null>(null);
const wingId = ref<number | null>(null);
const wingOptions = ref<Record<number, string>>({});

const DAYS = [
  [1, "الأحد"],
  [2, "الاثنين"],
  [3, "الثلاثاء"],
  [4, "الأربعاء"],
  [5, "الخميس"],
] as const;
// أيام الدراسة: الأحد إلى الخميس فقط (إزالة الجمعة والسبت لطلبك)
const DAYS5 = [
  [1, "الأحد"],
  [2, "الاثنين"],
  [3, "الثلاثاء"],
  [4, "الأربعاء"],
  [5, "الخميس"],
] as const;
const PERIODS = [1, 2, 3, 4, 5, 6, 7];
const activeDay = ref<number>(1);
const activeDayStr = computed(() => String(activeDay.value));

const weekly = ref<Record<string, any[]>>({});
const dailyItems = ref<any[]>([]);
const meta = ref<Record<string, any>>({});
const periodTimes = ref<Record<number, { start: string; end: string }>>({});

// Weekly column resize state (period + 7 days)
const enableResize = ref(false);
const WEEKLY_COLS = 9; // 0 = الفصل (sticky), 1 = اليوم، 2..8 = الحصص 1..7
const weeklyWidths = ref<number[]>([]);
const defaultWeeklyWidths = () => {
  // Reduce class/day to half width and distribute extra space to periods equally
  const arr = new Array(WEEKLY_COLS).fill(140);
  // Halved sticky columns to free space for periods
  arr[0] = 50; // الفصل (sticky)
  arr[1] = 48; // اليوم
  // Make all period columns equal and wider to avoid inner horizontal scrollbars
  for (let i = 2; i < WEEKLY_COLS; i++) arr[i] = 240;
  return arr;
};
const LS_KEY = "wing_tt_weekly_col_widths";
const hasCustomWidths = computed(() => {
  const def = defaultWeeklyWidths();
  if (weeklyWidths.value.length !== WEEKLY_COLS) return false;
  return weeklyWidths.value.some((v, i) => v !== def[i]);
});
function weeklyColPx(i: number): string {
  const w = weeklyWidths.value[i];
  return typeof w === "number" && !isNaN(w) ? `${w}px` : "";
}
function loadWeeklyWidths() {
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (!raw) {
      weeklyWidths.value = defaultWeeklyWidths();
      return;
    }
    const arr = JSON.parse(raw);
    if (Array.isArray(arr) && arr.length === WEEKLY_COLS) {
      weeklyWidths.value = arr.map((n: any, idx: number) =>
        Number.isFinite(n)
          ? Math.max(idx === 0 ? 50 : 45, Math.min(Number(n), 600))
          : defaultWeeklyWidths()[idx]
      );
    } else {
      weeklyWidths.value = defaultWeeklyWidths();
    }
  } catch {
    weeklyWidths.value = defaultWeeklyWidths();
  }
}
function saveWeeklyWidths() {
  try {
    localStorage.setItem(LS_KEY, JSON.stringify(weeklyWidths.value));
  } catch {}
}
function resetWeeklyWidths() {
  weeklyWidths.value = defaultWeeklyWidths();
  saveWeeklyWidths();
}
// Drag-to-resize logic
let dragState: null | { col: number; startX: number; startW: number } = null;
function onResizeStart(colIndex: number, e: MouseEvent) {
  // In RTL, moving mouse left increases width visually; but since we use clientX delta, we invert sign
  dragState = { col: colIndex, startX: e.clientX, startW: weeklyWidths.value[colIndex] || 140 };
  document.addEventListener("mousemove", onResizeMove);
  document.addEventListener("mouseup", onResizeEnd, { once: true });
  // prevent text selection
  document.body.classList.add("resizing");
}
function onResizeMove(e: MouseEvent) {
  if (!dragState) return;
  const idx = dragState.col;
  const delta =
    document.dir === "rtl" || document.documentElement.getAttribute("dir") === "rtl"
      ? dragState.startX - e.clientX
      : e.clientX - dragState.startX;
  // Allow narrower sticky class/day columns to maximize period widths
  const minW = idx === 0 ? 100 : 90;
  const maxW = 600;
  const next = Math.max(minW, Math.min(dragState.startW + delta, maxW));
  // apply
  const arr = weeklyWidths.value.slice();
  arr[idx] = next;
  weeklyWidths.value = arr;
}
function onResizeEnd() {
  document.removeEventListener("mousemove", onResizeMove);
  document.body.classList.remove("resizing");
  dragState = null;
  saveWeeklyWidths();
}

const isEmpty = computed(() =>
  mode.value === "daily"
    ? dailyItems.value.length === 0
    : Object.values(weekly.value).every((a) => (a as any[]).length === 0)
);
const formattedDate = computed(() => formatDateDMY(dateStr.value));

const groupedDaily = computed(() => {
  const groups: Record<number, any[]> = {};
  for (const p of PERIODS) groups[p] = [];
  for (const it of dailyItems.value) {
    if (groups[it.period_number]) groups[it.period_number].push(it);
  }
  return { groups, total: dailyItems.value.length };
});

// Build class list for daily header row (unique classes appearing today)
const dailyClassList = computed(() => {
  const map = new Map<number, { id: number; name?: string | null }>();
  for (const it of dailyItems.value) {
    const id = Number(it.class_id);
    if (Number.isFinite(id) && !map.has(id)) {
      map.set(id, { id, name: it.class_name || null });
    }
  }
  return Array.from(map.values()).sort((a, b) => (a.name || '').localeCompare(b.name || '') || a.id - b.id);
});

// Derive current wing label for print header and context
const wingLabel = computed(() => {
  const id = wingId.value as number | null;
  if (!id) return "";
  const name = (wingOptions.value as any)[id];
  return name || `جناح #${id}`;
});

function printPage() {
  try {
    window.print();
  } catch {}
}

function dayNameAr(d: string): string {
  const N = ["الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت"];
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(d));
  let dt: Date = m ? new Date(parseInt(m[1]), parseInt(m[2]) - 1, parseInt(m[3])) : new Date(d);
  if (isNaN(dt.getTime())) return "—";
  return N[dt.getDay()] || "—";
}

import { subjectIcon } from "../../../shared/icons/subjectIcons";

function setMode(m: "daily" | "weekly") {
  if (mode.value !== m) {
    mode.value = m;
    loadData();
    if (m === "daily") {
      nextTick().then(() => updateUnifiedCellWidth());
    }
  }
}

function timeToHM(t: string | undefined | null): string {
  if (!t) return "";
  // Expecting 'HH:MM[:SS]' — keep HH:MM
  const m = /^(\d{2}:\d{2})/.exec(String(t));
  return m ? m[1] : String(t);
}
function timeRange(p: number): string {
  const rec = periodTimes.value[p as keyof typeof periodTimes.value] as any;
  if (!rec) return "";
  const s = timeToHM(rec.start);
  const e = timeToHM(rec.end);
  return s && e ? `${s} — ${e}` : s || e || "";
}

// إرجاع عناصر الخلية لليوم d (1..7) والحصة p (1..7)
function cellItems(d: number, p: number) {
  const arr = weekly.value[String(d)] || [];
  return arr.filter((i: any) => Number(i.period_number) === p);
}

// New: Build list of classes (unique across the week) for the weekly class×day grid
const classList = computed<{ id: number; name: string }[]>(() => {
  const seen = new Map<number, string>();
  const days = [1, 2, 3, 4, 5];
  for (const d of days) {
    const arr = (weekly.value[String(d)] || []) as any[];
    for (const it of arr) {
      const cid = Number(it.class_id);
      if (!Number.isFinite(cid)) continue;
      if (!seen.has(cid)) seen.set(cid, it.class_name || `صف #${cid}`);
    }
  }
  // Return sorted by name (locale-aware Arabic if available)
  return Array.from(seen.entries())
    .map(([id, name]) => ({ id, name }))
    .sort((a, b) => String(a.name).localeCompare(String(b.name), "ar"));
});

// New: items for a given class and day (all periods), sorted by period_number
function classDayItems(classId: number, d: number) {
  const arr = weekly.value[String(d)] || [];
  return (arr as any[])
    .filter((it) => Number(it.class_id) === Number(classId))
    .sort((a, b) => Number(a.period_number) - Number(b.period_number));
}

// Helper: find the daily item for a given class and period (used by daily integrated table)
function dailyItemFor(classId: number, p: number) {
  const g = groupedDaily.value.groups?.[p] as any[] | undefined;
  if (!Array.isArray(g)) return null;
  return g.find((it) => Number(it.class_id) === Number(classId)) || null;
}

// Helper: weekly single item for class + day + period
function classDayPeriodItem(classId: number, d: number, p: number) {
  const arr = weekly.value[String(d)] || [];
  return (arr as any[]).find(
    (it) => Number(it.class_id) === Number(classId) && Number(it.period_number) === Number(p)
  ) || null;
}

function ensureWeeklyShape() {
  // ضَمَن وجود مفاتيح 1..7 حتى إن لم يرجعها الـ API
  for (let d = 1; d <= 7; d++) {
    if (!weekly.value[String(d)]) weekly.value[String(d)] = [];
  }
}

// ==== Countdown logic ====
const countdownMap = ref<Record<number, string>>({});
let timerHandle: number | null = null;

function parseDateTime(dIso: string, hm: string | undefined): Date | null {
  if (!dIso || !hm) return null;
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(dIso));
  const t = /^(\d{2}):(\d{2})(?::(\d{2}))?/.exec(String(hm));
  if (!m || !t) return null;
  const y = parseInt(m[1], 10);
  const mo = parseInt(m[2], 10) - 1;
  const dd = parseInt(m[3], 10);
  const hh = parseInt(t[1], 10);
  const mi = parseInt(t[2], 10);
  const ss = t[3] ? parseInt(t[3], 10) : 0;
  return new Date(y, mo, dd, hh, mi, ss);
}

function fmtHMS(totalSeconds: number): string {
  if (totalSeconds < 0) totalSeconds = 0;
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = Math.floor(totalSeconds % 60);
  const pad = (n: number) => String(n).padStart(2, "0");
  return h > 0 ? `${pad(h)}:${pad(m)}:${pad(s)}` : `${pad(m)}:${pad(s)}`;
}

function updateCountdowns() {
  const map: Record<number, string> = {};
  const now = new Date();
  for (const p of PERIODS) {
    const rec = periodTimes.value[p as keyof typeof periodTimes.value] as any;
    if (!rec) {
      map[p] = "";
      continue;
    }
    const start = parseDateTime(dateStr.value, rec.start);
    const end = parseDateTime(dateStr.value, rec.end);
    if (!start || !end) {
      map[p] = "";
      continue;
    }
    if (now >= start && now <= end) {
      const remain = Math.floor((end.getTime() - now.getTime()) / 1000);
      map[p] = fmtHMS(remain);
    } else {
      map[p] = "";
    }
  }
  countdownMap.value = map;
}

function startTimer() {
  stopTimer();
  updateCountdowns();
  timerHandle = window.setInterval(updateCountdowns, 1000);
}
function stopTimer() {
  if (timerHandle != null) {
    window.clearInterval(timerHandle);
    timerHandle = null;
  }
}

async function loadMe() {
  try {
    const me = await getWingMe();
    const map: Record<number, string> = {};
    (me.wings?.ids || []).forEach((id: number, idx: number) => {
      map[id] = me.wings?.names?.[idx] || "جناح #" + id;
    });
    wingOptions.value = map;
    if (!wingId.value) {
      const keys = Object.keys(map);
      if (keys.length) wingId.value = Number(keys[0]);
    }
  } catch {
    wingOptions.value = {} as any;
  }
}

async function loadData() {
  if (!wingId.value) {
    await loadMe();
    if (!wingId.value) return;
  }
  loading.value = true;
  error.value = null;
  try {
    const res = await getWingTimetable({
      wing_id: wingId.value || undefined,
      date: dateStr.value,
      mode: mode.value,
    });
    // Extract period_times (prefer per-day if available)
    const metaRes = (res as any).meta || {};
    const byDay = (metaRes as any).period_times_by_day || null;
    const generic = (metaRes as any).period_times || {};
    const pt: Record<number, { start: string; end: string }> = {};
    let rawMap: any = generic;
    if ((res as any).mode === "daily" && byDay && typeof (res as any).dow === "number") {
      rawMap = byDay[String((res as any).dow)] || generic;
    }
    Object.keys(rawMap || {}).forEach((k) => {
      const v = (rawMap as any)[k];
      if (Array.isArray(v) && v.length >= 2) {
        pt[Number(k)] = { start: String(v[0]), end: String(v[1]) };
      } else if (v && typeof v === "object") {
        const s = (v as any).start || (v as any).start_time;
        const e = (v as any).end || (v as any).end_time;
        if (s || e) pt[Number(k)] = { start: String(s || ""), end: String(e || "") } as any;
      }
    });
    periodTimes.value = pt;

    if ((res as any).mode === "weekly") {
      weekly.value = (res as any).days || {};
      ensureWeeklyShape();
      if (!weekly.value[activeDayStr.value]) activeDay.value = 1;
    } else {
      dailyItems.value = (res as any).items || [];
    }
    // After data load, (re)start countdown timer for daily mode
    if (mode.value === "daily") startTimer();
    else stopTimer();
    // Measure and unify cell widths for daily view after DOM updates
    await nextTick();
    if (mode.value === "daily") {
      updateUnifiedCellWidth();
    }
  } catch (e: any) {
    error.value = e?.response?.data?.detail || e?.message || String(e);
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  loadWeeklyWidths();
  await loadMe();
  await loadData();
  startTimer();
  setupResizeObserver();
});

onBeforeUnmount(() => {
  stopTimer();
  teardownResizeObserver();
});

// === Equalize daily cell width across items (based on longest content) ===
let _resizeHandler: any = null;

// Measure intrinsic width of a given element's text by cloning its computed text styles (safe with Vue scoped CSS)
function _measureElementText(el: HTMLElement | null): number {
  if (!el) return 0;
  const cs = window.getComputedStyle(el);
  const ruler = document.createElement("div");
  ruler.style.position = "absolute";
  ruler.style.visibility = "hidden";
  ruler.style.whiteSpace = "nowrap";
  ruler.style.pointerEvents = "none";
  ruler.style.zIndex = "-1";
  // Copy key text styles so measurement matches the real rendering even under scoped CSS
  ruler.style.font = cs.font; // shorthand includes weight/size/family when available
  ruler.style.fontSize = cs.fontSize;
  ruler.style.fontFamily = cs.fontFamily;
  ruler.style.fontWeight = cs.fontWeight as any;
  ruler.style.letterSpacing = cs.letterSpacing;
  ruler.style.textTransform = cs.textTransform as any;
  ruler.style.lineHeight = cs.lineHeight;
  ruler.textContent = el.textContent || "";
  document.body.appendChild(ruler);
  const rect = ruler.getBoundingClientRect();
  const w = Math.ceil(rect.width);
  ruler.remove();
  return w;
}

function updateUnifiedCellWidth() {
  if (mode.value !== "daily") {
    document.documentElement.style.removeProperty("--wing-cell-w");
    return;
  }
  try {
    const nodes = Array.from(document.querySelectorAll(".period-cell")) as HTMLElement[];
    if (!nodes.length) {
      document.documentElement.style.setProperty("--wing-cell-w", "160px");
      return;
    }
    let max = 0;
    for (const el of nodes) {
      const subjTextEl = el.querySelector(".cell-subject .subject-name") as HTMLElement | null;
      const teacherEl = el.querySelector(".cell-teacher") as HTMLElement | null;
      const iconWidth = 18; // approx icon + gap
      const gap = 8; // subject/teacher internal gap
      const subjW = (subjTextEl ? _measureElementText(subjTextEl) : 0) + iconWidth + gap;
      const teachW = teacherEl ? _measureElementText(teacherEl) : 0;
      const inner = Math.max(subjW, teachW);
      const paddings = 16; // .period-cell has 0.5rem left + 0.5rem right ≈ 16px total
      max = Math.max(max, inner + paddings);
    }
    // Double the measured width and clamp
    const increased = max * 2.0;
    const clamped = Math.max(160, Math.min(increased, 900));
    document.documentElement.style.setProperty("--wing-cell-w", clamped + "px");
  } catch {}
}
function setupResizeObserver() {
  if (_resizeHandler) return;
  _resizeHandler = () => {
    if (mode.value === "daily") {
      updateUnifiedCellWidth();
    }
  };
  window.addEventListener("resize", _resizeHandler);
}
function teardownResizeObserver() {
  if (_resizeHandler) {
    window.removeEventListener("resize", _resizeHandler);
    _resizeHandler = null;
  }
}
</script>

<style scoped>
.toolbar-controls .btn {
  white-space: nowrap;
}

/* Ensure inner content is centered at 95% of the card width (same pattern as TeacherTimetable) */
.in-card-95 {
  width: 95%;
  max-width: 100%;
  margin-inline: auto;
  display: block;
}

.slot-card {
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}
.slot-card .icon-wrap {
  width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  color: #8a1538;
  background: rgba(0, 0, 0, 0.04);
  border-radius: 8px;
}
.tiny {
  font-size: 0.8rem;
}

.days-tabs {
  background: linear-gradient(135deg, #f8f9fa 0%, #edf1f5 100%);
  border-bottom: 1px solid #e9ecef;
}
.no-wrap {
  white-space: nowrap;
}
.one-line {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
/* Multi-line truncation helpers */
.truncate-1 {
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
}
.truncate-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
}
/* Prevent content from forcing wrap: allow text to shrink within flex container */
.slot-card .flex-fill {
  min-width: 0;
}
.slot-card .icon-wrap,
.slot-card .badge {
  flex-shrink: 0;
}
/* Strong single-line header utility for period headers */
.hdr-line {
  display: flex;
  align-items: center;
  justify-content: center; /* center horizontally in weekly class header cell */
  gap: 0.5rem;
  white-space: nowrap;
  flex-wrap: nowrap;
}
.hdr-line > * {
  flex-shrink: 0;
}
.hdr-line .badge {
  white-space: nowrap;
}

/* 7×7 weekly grid styles */
.tt7-wrapper {
  display: block;
  width: 100%;
  padding: 12px;
}
.tt7-scroller {
  width: 100%;
  max-width: 100%;
  margin-inline: auto;
  overflow: auto;
}
.tt7-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 8px 6px;
  background: #fff;
  table-layout: fixed;
}
.tt7-th {
  background: linear-gradient(135deg, #f8f9fa 0%, #edf1f5 100%);
  color: #333;
  font-weight: 700;
  text-align: center;
  vertical-align: middle;
  padding: 0.75rem;
  border-bottom: 2px solid #e0e6ef;
  white-space: nowrap;
}
.tt7-th-period {
  text-align: center;
  position: sticky;
  inset-inline-start: 0;
  background: #fafbfc;
  border-inline-end: 1px solid #eef2f7;
  min-width: 180px;
  z-index: 2;
}
.tt7-th-sticky {
  position: sticky;
  inset-inline-start: 0;
  z-index: 3;
  background: #f8f9fb;
}
.tt7-td {
  vertical-align: middle;
  padding: 0.5rem;
  border-bottom: 1px solid #f0f2f5;
  border-inline-start: 1px solid #f6f7f9;
  height: 72px; /* contained height to reduce excessive tall rows */
  max-height: 72px;
  text-align: center;
}
.tt7-table tr:hover td {
  background: #fafbff;
}
.tt7-cell {
  display: flex;
  flex-direction: column;
  align-items: center; /* center horizontally */
  justify-content: center; /* center vertically within td height */
  gap: 6px;
  max-height: 100%;
  overflow: hidden; /* prevent inner scrollbars; let content wrap/truncate */
  padding: 2px;
}
.mini-cell {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 2px;
  padding: 0.35rem 0.5rem;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 10px;
  background: #f5f7fb;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
}
.mini-subj {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.3rem;
  font-weight: 700;
  color: #1f2937;
  line-height: 1.1;
  max-width: 100%;
  overflow: hidden;
}
.mini-subj .subject-icon {
  font-size: 16px;
  color: var(--maron-primary, #8a1538);
  flex-shrink: 0;
}
.mini-teacher {
  font-size: 0.82rem;
  color: #6b7280;
  line-height: 1.1;
  text-align: center;
}
@media (max-width: 768px) {
  .tt7-th-period {
    position: static;
  }
  .mini-cell {
    flex-basis: 140px;
  }
}

/* New single-row daily layout */
.period-line {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  white-space: nowrap;
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid #f0f0f0;
}
/* Make the items container fill the remaining row width and distribute cells across available space */
.period-line .items-inline {
  flex: 1;
  width: 100%;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  align-items: stretch;
  gap: 0.5rem;
}
.period-line .countdown {
  font-weight: 600;
}
/* Professional inline cells for each class in the period */
.period-cell {
  display: inline-flex;
  flex-direction: column;
  justify-content: center;
  align-items: center; /* center content horizontally within the cell */
  text-align: center; /* center text inside lines */
  width: 100%;
  min-width: 0; /* allow grid to control width via minmax */
  height: 64px;
  padding: 0.35rem 0.5rem;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 10px;
  background: #f5f7fb;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
}
.cell-subject {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.35rem;
  font-weight: 700;
  color: #1f2937; /* dark slate */
  line-height: 1.1;
  max-width: 100%;
  overflow: hidden;
}
.cell-subject .subject-icon {
  font-size: 16px;
  color: var(--maron-primary, #8a1538);
  flex-shrink: 0;
}
.cell-teacher {
  font-size: 0.82rem;
  color: #6b7280; /* muted */
  line-height: 1.1;
  text-align: center;
}
/* Ensure subject text can ellipsize within flex containers */
.subject-name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  overflow-wrap: anywhere;
  word-break: break-word;
}
.mini-teacher,
.cell-teacher {
  overflow-wrap: anywhere;
  word-break: break-word;
}
@media (max-width: 576px) {
  .period-cell {
    min-width: 120px;
    max-width: 180px;
  }
}
/* Column resizer (weekly 7×7) */
.resizable-th {
  position: relative;
}
.col-resizer {
  position: absolute;
  top: 0;
  bottom: 0;
  inset-inline-start: 0; /* works in RTL/LTR */
  width: 8px;
  cursor: col-resize;
  opacity: 0;
  transition: opacity 0.15s ease;
}
.resizable-th:hover .col-resizer {
  opacity: 0.6;
}
.resizable-th .col-resizer::after {
  content: "";
  position: absolute;
  top: 0;
  bottom: 0;
  inset-inline-start: 3px;
  width: 2px;
  background: rgba(0, 0, 0, 0.1);
}
body.resizing {
  cursor: col-resize !important;
  user-select: none !important;
}

/* Print: ensure readable high-contrast */
@media print {
  .period-cell {
    background: #fff !important;
    border-color: #ccc !important;
    box-shadow: none !important;
  }
  .cell-subject {
    color: #000 !important;
  }
  .cell-teacher {
    color: #333 !important;
  }
  .col-resizer {
    display: none !important;
  }
}
</style>

<style>
@media print {
  @page {
    size: A4 portrait;
    margin: 10mm;
  }
  body {
    background: #fff !important;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }
  .navbar-maronia,
  .page-footer {
    display: none !important;
  }
  .toolbar-card,
  .days-tabs {
    display: none !important;
  }
  .print-header {
    display: block !important;
  }
  .auto-card {
    box-shadow: none !important;
    border: none !important;
  }
  .slot-card {
    box-shadow: none !important;
    break-inside: avoid;
    page-break-inside: avoid;
  }
  .full-bleed,
  section.full-bleed > * {
    width: 100% !important;
    margin: 0 !important;
  }
}
/* Hide print header on screen */
.print-header {
  display: none;
}
</style>

<style scoped>
/* Daily view cell spacing and readability */
.period-line { gap: 10px; padding-block: 6px; }
.period-line .items-inline { display: flex; flex-wrap: wrap; gap: 8px; }
.period-cell { padding: 8px 10px; border-radius: 8px; min-height: 56px; line-height: 1.3; display: flex; flex-direction: column; justify-content: center; }
.cell-subject { font-weight: 600; margin-bottom: 4px; display: flex; align-items: center; gap: 6px; }
.cell-teacher { color: #333; font-size: 0.95rem; }
.subject-icon { font-size: 16px; }

/* Weekly view: periods column styling */
.tt7-td-periods { vertical-align: top; }
.tt7-td-periods .periods-col { display: flex; flex-direction: column; gap: 6px; align-items: center; padding: 6px 4px; }

/* Weekly mini cells spacing between subject and teacher */
.mini-cell { padding: 4px 6px; border-radius: 8px; line-height: 1.2; }
.mini-cell .mini-subj { margin-bottom: 4px; display: flex; align-items: center; gap: 6px; font-weight: 600; }

/* Integrated daily table styles */
.tt-daily-scroller { overflow: auto; }
.tt-daily-table { width: 100%; border-collapse: separate; border-spacing: 0; }
.tt-daily-table thead th { position: sticky; top: 0; background: linear-gradient(135deg, #fff7ed 0%, #ffefd9 100%); z-index: 1; text-align: center; vertical-align: middle; padding: 8px; border-bottom: 1px solid #f3d2a9; }
/* Ensure the sticky first-column header cell also uses the same header tone */
.tt-daily-table thead .tt-daily-th-sticky { background: linear-gradient(135deg, #fff7ed 0%, #ffefd9 100%); }
/* Weekly header row tone */
.tt7-table thead .tt7-th { background: linear-gradient(135deg, #fff7ed 0%, #ffefd9 100%); }
.tt-daily-th-sticky { position: sticky; right: 0; background: #fff; z-index: 2; box-shadow: -1px 0 0 #e5e7eb inset; }
.tt-daily-td, .tt-daily-th { padding: 8px; vertical-align: middle; border-bottom: 1px solid #f0f2f5; text-align: center; }
/* Ensure the first sticky header cell (الحصة) content is centered horizontally */
.tt-daily-th-sticky .d-flex { justify-content: center; }
.tt-daily-td { min-width: 180px; }
.tt-daily-td .period-cell { display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 64px; }

/* Maroon separator between classes (applies to daily and weekly) */
tr.class-separator > th,
tr.class-separator > td { border-top: 3px solid #8a1538 !important; }

/* Enlarge class name to 3x current size */
.tt7-table .class-name-badge {
  font-size: 2.4rem; /* approx 3x default badge size */
  line-height: 1.1;
  padding: 8px 12px;
}
/* Daily: enlarge class name to 2x default size */
.tt-daily-table .class-name-badge {
  font-size: 1.6rem; /* approx 2x default badge size */
  line-height: 1.15;
  padding: 6px 10px;
}

/* Header row for classes in daily view (old strip) no longer used */
.classes-header { display: none; }
</style>