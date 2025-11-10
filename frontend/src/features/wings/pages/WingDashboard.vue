<template>
  <section class="wing-dashboard d-grid gap-3 page-grid page-grid-wide">
    <WingPageHeader :icon="tileMeta.icon" :title="tileMeta.title" :color="tileMeta.color">
          <template #actions>
            <span class="d-inline-flex align-items-center gap-2 flex-wrap align-items-center">
              <span class="small text-muted" aria-live="polite">
                <template v-if="isToday">اليوم: {{ liveDate }} • {{ liveTime }}</template>
                <template v-else>التاريخ: {{ selectedDateDMY }}</template>
              </span>
              <span v-if="dayStateBadge.text" class="att-chip day-state" :class="dayStateBadge.variant" aria-live="polite">
                {{ dayStateBadge.text }}
              </span>
            </span>
          </template>
        </WingPageHeader>

    <div class="auto-card p-2 d-flex align-items-center gap-2 flex-wrap" aria-live="polite">
      <DatePickerDMY
        :id="'wing-dash-date'"
        :aria-label="'اختيار التاريخ'"
        wrapperClass="m-0"
        inputClass="form-control w-auto"
        v-model="dateStr"
        @change="onDateChanged"
      />


      <!-- زر إيقاف/استئناف التحديث الحي بأسلوب صفحة المراقبة (أخضر) -->
      <button class="btn btn-sm" :class="paused ? 'btn-outline-secondary' : 'btn-outline-success'" @click="toggleLive" :aria-pressed="!paused" :aria-label="paused ? 'تشغيل التحديث الحي' : 'إيقاف التحديث الحي'">
        <Icon :icon="paused ? 'solar:play-bold-duotone' : 'solar:pause-bold-duotone'" />
        <span class="ms-1">تحديث حي</span>
      </button>

      <button class="btn btn-sm btn-outline-primary" @click="loadData">
        <Icon icon="solar:refresh-bold-duotone" class="me-1" />
        تحديث
      </button>
      <span class="small text-muted ms-auto" aria-live="polite">آخر تحديث: {{ lastUpdated }}</span>
    </div>

    <div v-if="loading" class="alert alert-light border d-flex align-items-center gap-2">
      <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
      <span>جاري تحميل مؤشرات الجناح...</span>
    </div>
    <div v-if="error" class="alert alert-danger">حدث خطأ أثناء تحميل البيانات: {{ error }}</div>

    <!-- شبكة اختصارات سريعة حتى لا تبدو الصفحة فارغة -->
    <div class="row g-2 mb-3">
      <div class="col-6 col-md-3" v-for="s in shortcuts" :key="s.key">
        <RouterLink class="auto-card p-3 text-center text-decoration-none h-100 d-block" :to="s.to" :aria-label="s.label">
          <Icon :icon="s.icon" class="text-2xl mb-2" />
          <div class="small fw-bold">{{ s.label }}</div>
        </RouterLink>
      </div>
    </div>

    <!-- بانر تشخيصي يظهر إن لم يكن للمستخدم أي أجنحة مُعيّنة -->
    <div
      v-if="
        !loading &&
        !error &&
        meInfo &&
        meInfo.wings &&
        (!meInfo.wings.ids || meInfo.wings.ids.length === 0)
      "
      class="alert alert-info d-flex align-items-center gap-2"
    >
      <Icon icon="solar:info-circle-bold-duotone" />
      <div>
        لا توجد أجنحة معيّنة لحسابك حاليًا. تأكد من تعيينك كمشرف لجناح واحد على الأقل في قاعدة
        البيانات (Wing.supervisor).
        <div class="small text-muted">الأدوار: {{ meInfo.roles?.join(", ") || "—" }}</div>
      </div>
    </div>

    <div
      v-if="!loading && kpis.total === 0"
      class="alert alert-warning d-flex align-items-center gap-2"
    >
      <Icon icon="solar:info-circle-bold-duotone" />
      <div>
        لا توجد بيانات حضور لهذا اليوم ضمن جناحك. إن لم تُعيَّن لك أجنحة بعد، راسل الإدارة لتعيينك
        كمشرف لجناحك.
      </div>
    </div>

    <div class="row g-3">
      <!-- أدوات تحديد الصفوف للجناح -->
      <div class="col-12">
        <div
          class="auto-card p-2 px-3 mb-1 d-flex flex-wrap align-items-center gap-2 class-toolbar"
        >
          <Icon icon="solar:home-2-bold-duotone" />
          <span class="small fw-bold">تحديد الصفوف</span>
          <div class="vr mx-1 d-none d-sm-block"></div>

          <!-- قائمة منسدلة متعددة الاختيار -->
          <div class="dropdown">
            <button
              class="btn btn-sm btn-outline-secondary dropdown-toggle"
              data-bs-toggle="dropdown"
              data-bs-display="static"
              type="button"
            >
              {{ selectedLabel }}
            </button>
            <ul
              class="dropdown-menu dropdown-menu-end p-2 small"
              style="min-width: 260px; max-height: 300px; overflow: auto"
            >
              <li class="px-2 pb-2 d-flex gap-1 flex-wrap">
                <button class="btn btn-light btn-sm" @click="selectAll">الكل</button>
                <button class="btn btn-light btn-sm" @click="clearAll">إلغاء</button>
                <button class="btn btn-light btn-sm" @click="invertSelection">عكس</button>
              </li>
              <li
                v-for="opt in classOptions"
                :key="opt.id"
                class="dropdown-item d-flex align-items-center gap-2"
              >
                <input
                  class="form-check-input m-0"
                  type="checkbox"
                  :id="'cls-' + opt.id"
                  :checked="selectedSet.has(opt.id)"
                  @change="toggleClass(opt.id)"
                />
                <label class="form-check-label flex-fill" :for="'cls-' + opt.id">{{
                  opt.name || "صف #" + opt.id
                }}</label>
              </li>
              <li v-if="classOptions.length === 0" class="dropdown-item text-muted">
                لا توجد صفوف متاحة
              </li>
            </ul>
          </div>

          <span class="ms-auto small text-muted">
            <Icon icon="solar:filter-bold-duotone" class="me-1" />
            {{ selectionHint }}
          </span>
        </div>
      </div>
      <!-- شبكة بطاقات مؤشرات احترافية تغطي جميع الحالات المطلوبة (تصغير لأقصى حد ممكن) -->
      <div class="col-6 col-sm-4 col-md-3 col-lg-2 col-xl-1" v-for="c in kpiCards" :key="c.key">
        <div class="auto-card stat-card p-3 text-center h-100" aria-live="polite">
          <Icon :icon="c.icon" class="mb-1" :style="{ color: c.color }" />
          <div class="label small fw-bold text-muted">{{ c.label }}</div>
          <div class="value" :style="{ color: c.color }">{{ c.value }}</div>
          <div class="sub small text-muted" v-if="c.sub">{{ c.sub }}</div>
        </div>
      </div>

      <!-- بطاقة ملخّص أسبوعي قابلة للطباعة -->
      <div class="col-12">
        <div class="card print-focus-target" ref="weeklyCard">
          <div class="card-body">
            <!-- ترويسة للطباعة فقط -->
            <PrintPageHeader class="print-only"
              :title="`ملخّص أسبوعي — جناح ${wingLabelFull || '-'}`"
              :meta-lines="[
                `الفترة: ${weekFrom} → ${weekTo}`,
                `نطاق الأسبوع: الأحد → الخميس`
              ]"
            />
            <div class="d-flex align-items-center gap-2 mb-2">
              <Icon icon="solar:graph-new-bold-duotone" />
              <h5 class="m-0 card-title-maroon">ملخّص أسبوعي</h5>
              <span class="small text-muted">الفترة: {{ weekFrom }} → {{ weekTo }}</span>
              <a class="btn btn-sm btn-outline-success ms-auto no-print" :href="weeklyWordHref" target="_blank" rel="noopener">
                <Icon icon="mdi:download" class="me-1" /> تنزيل Word
              </a>
              <button class="btn btn-sm btn-outline-primary no-print" @click="printWeekly">
                <Icon icon="mdi:printer" class="me-1" /> طباعة الملخّص
              </button>
            </div>

            <div class="row g-3 mb-2">
              <div class="col-6 col-md-3">
                <label class="form-label">من</label>
                <input type="date" class="form-control" v-model="weekFrom" @change="reloadWeekly" />
              </div>
              <div class="col-6 col-md-3">
                <label class="form-label">إلى</label>
                <input type="date" class="form-control" v-model="weekTo" @change="reloadWeekly" />
              </div>
              <div class="col-12 col-md-6 d-flex align-items-end gap-2">
                <button class="btn btn-outline-secondary" @click="resetWeekRange"><Icon icon="mdi:calendar-range" class="me-1"/> أسبوع Sun→Thu تلقائي</button>
                <span class="small text-muted ms-auto" aria-live="polite">{{ weeklyHint }}</span>
              </div>
            </div>

            <div v-if="weeklyLoading" class="text-muted">جاري احتساب الملخّص الأسبوعي…</div>
            <div v-else>
              <div class="row g-2 mb-3">
                <div class="col-6 col-md-3">
                  <div class="auto-card stat-card p-2 text-center">
                    <div class="small text-muted">نسبة الحضور (متوسط مرجّح)</div>
                    <div class="fw-bold" style="color:#16a085">{{ weeklyKPIs.present_pct.toFixed(1) }}%</div>
                  </div>
                </div>
                <div class="col-6 col-md-3">
                  <div class="auto-card stat-card p-2 text-center">
                    <div class="small text-muted">الغياب (إجمالي)</div>
                    <div class="fw-bold" style="color:#c0392b">{{ weeklyKPIs.absent }}</div>
                  </div>
                </div>
                <div class="col-6 col-md-3">
                  <div class="auto-card stat-card p-2 text-center">
                    <div class="small text-muted">التأخر (إجمالي)</div>
                    <div class="fw-bold" style="color:#e67e22">{{ weeklyKPIs.late }}</div>
                  </div>
                </div>
                <div class="col-6 col-md-3">
                  <div class="auto-card stat-card p-2 text-center">
                    <div class="small text-muted">أذونات الخروج (إجمالي)</div>
                    <div class="fw-bold" style="color:#8e44ad">{{ weeklyKPIs.exit_events_total }}</div>
                  </div>
                </div>
              </div>

              <div class="table-responsive">
                <table class="table table-sm align-middle print-table">
                  <thead>
                    <tr>
                      <th>اليوم</th>
                      <th class="text-center">التاريخ</th>
                      <th class="text-center">% حضور</th>
                      <th class="text-center">حاضر</th>
                      <th class="text-center">غياب</th>
                      <th class="text-center">تأخر</th>
                      <th class="text-center">مُعذّر</th>
                      <th class="text-center">هروب</th>
                      <th class="text-center">أذونات</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="d in weeklyDays" :key="d.iso">
                      <td>{{ d.label }}</td>
                      <td class="text-center">{{ d.iso }}</td>
                      <td class="text-center">{{ (d.kpis?.present_pct ?? 0).toFixed(1) }}%</td>
                      <td class="text-center">{{ d.kpis?.present ?? '—' }}</td>
                      <td class="text-center">{{ d.kpis?.absent ?? '—' }}</td>
                      <td class="text-center">{{ d.kpis?.late ?? '—' }}</td>
                      <td class="text-center">{{ d.kpis?.excused ?? '—' }}</td>
                      <td class="text-center">{{ d.kpis?.runaway ?? '—' }}</td>
                      <td class="text-center">{{ d.kpis?.exit_events_total ?? '—' }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Legend موحّد للألوان/الحالات -->

      <div class="col-12" v-if="false">
        <div class="row g-3">
          <!-- حصص اليوم بلا إدخال -->
          <div class="col-12">
            <div class="auto-card p-0 overflow-hidden h-100">
              <div class="p-3 d-flex align-items-center gap-2 border-bottom">
                <Icon icon="solar:warning-bold-duotone" style="color: var(--color-warning)" />
                <div class="fw-bold">حصص اليوم بلا إدخال</div>
                <span class="badge text-bg-secondary">{{ filteredMissing.count }}</span>
                <span class="ms-auto"></span>
              </div>
              <div v-if="filteredMissing.count === 0" class="p-3 text-muted">
                لا توجد حصص بلا إدخال اليوم في نطاق الترشيح.
              </div>
              <div v-else class="table-responsive overflow-visible">
                <table class="table table-hover align-middle mb-0">
                  <thead>
                    <tr>
                      <th>
                        <Icon icon="solar:home-2-bold-duotone" class="me-1" />
                        الصف
                      </th>
                      <th>
                        <Icon icon="solar:calendar-bold-duotone" class="me-1" />
                        الحصة
                      </th>
                      <th>
                        <Icon icon="solar:book-2-bold-duotone" class="me-1" />
                        المادة
                      </th>
                      <th>
                        <Icon icon="solar:user-bold-duotone" class="me-1" />
                        المعلم
                      </th>
                      <th class="text-center">
                        <Icon icon="solar:pen-new-round-bold-duotone" class="me-1" />
                        إجراء
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(row, idx) in filteredMissing.items" :key="'m-' + idx">
                      <td>{{ row.class_name || "#" + row.class_id }}</td>
                      <td>حصة {{ row.period_number }}</td>
                      <td>
                        <span
                          v-if="subjectTitle(row)"
                          class="d-inline-flex align-items-center gap-1"
                        >
                          <Icon v-if="subjectIcon(subjectTitle(row))" :icon="subjectIcon(subjectTitle(row))" class="me-1" />
                          <span>{{ subjectTitle(row) }}</span>
                        </span>
                        <span v-else>-</span>
                      </td>
                      <td>{{ row.teacher_name || "#" + row.teacher_id }}</td>
                      <td class="text-center">
                        <RouterLink
                          class="btn btn-sm btn-outline-primary"
                          :to="{
                            path: '/attendance/teacher',
                            query: {
                              class_id: row.class_id,
                              period: row.period_number,
                              date: currentDate,
                            },
                          }"
                        >
                          إدخال
                        </RouterLink>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
<script setup lang="ts">
import { subjectIcon } from "../../../shared/icons/subjectIcons";
function subjectTitle(row: any): string {
  try {
    const name = row?.subject_name
      ?? row?.subjectName
      ?? row?.subject__name
      ?? row?.tt_subject_name
      ?? row?.subject?.name
      ?? row?.subject_title
      ?? row?.subject_label
      ?? row?.course_name
      ?? row?.course
      ?? row?.subject;
    const s = (name ?? '').toString().trim();
    return s || '';
  } catch {
    return '';
  }
}
import { onMounted, onBeforeUnmount, ref, computed, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { getWingMe, getWingOverview, getMe, getWingMissing, getWingTimetable } from "../../../shared/api/client";
import DsButton from "../../../components/ui/DsButton.vue";
import { tiles } from "../../../home/icon-tiles.config";
import { useWingContext } from "../../../shared/composables/useWingContext";
import WingPageHeader from "../../../components/ui/WingPageHeader.vue";
import PrintPageHeader from "../../../components/ui/PrintPageHeader.vue";
import { Icon } from "@iconify/vue";
import DatePickerDMY from "../../../components/ui/DatePickerDMY.vue";
import { formatDateDMY, parseDMYtoISO, toIsoDate, formatISOtoDMY } from "../../../shared/utils/date";
import { backendUrl } from "../../../shared/config";

// ASCII-only time formatter HH:mm
function timeAscii(d: Date): string {
  const hh = d.getHours().toString().padStart(2, '0');
  const mm = d.getMinutes().toString().padStart(2, '0');
  return `${hh}:${mm}`;
}

const route = useRoute();
const router = useRouter();

// Unified header context and tile meta for Wing Dashboard
const { ensureLoaded, wingLabelFull, selectedWingId } = useWingContext();
const tileMeta = computed(() => tiles.find(t => t.to === '/wing/dashboard') || { title: 'لوحة الجناح', icon: 'solar:layers-minimalistic-bold-duotone', color: '#66aa66' });

const kpis = ref<any>({
  present_pct: 0,
  present: 0,
  absent: 0,
  late: 0,
  excused: 0,
  runaway: 0,
  total: 0,
  exit_events_total: 0,
  exit_events_open: 0,
});
const missing = ref<{ count: number; items: any[] }>({ count: 0, items: [] });
const loading = ref(true);
const error = ref<string | null>(null);

// Live updates control and last-updated time (ASCII)
const paused = ref<boolean>(String(route.query.paused || '') === '1');
const lastUpdated = ref<string>('—');

function syncPausedToUrl() {
  const q = { ...route.query } as any;
  if (paused.value) q.paused = '1'; else delete q.paused;
  router.replace({ query: q }).catch(() => {});
}

function toggleLive() {
  paused.value = !paused.value;
  syncPausedToUrl();
  if (!paused.value && isToday.value) {
    // resume: refresh immediately
    loadData();
  }
}

watch(paused, () => {
  // Timer checks paused flag; also refresh once when resuming with visible tab
  if (!paused.value && !document.hidden && isToday.value) {
    loadData();
  }
});

const meInfo = ref<any | null>(null);
const meProfile = ref<any | null>(null);
const apiStatus = ref<{ me?: number; wingMe?: number; overview?: number; missing?: number }>({});

// خيارات الصفوف واختيارها
const classOptions = ref<{ id: number; name?: string | null }[]>([]);
const selectedSet = ref<Set<number>>(new Set());

const supervisorName = computed(
  () => meInfo.value?.staff?.full_name || meProfile.value?.full_name || ""
);

// Build wing label like: "الوسيل (5)" from names such as "الجناح 5 - الوسيل"
const wingLabel = computed(() => {
  const info: any = meInfo.value || {};
  const names: string[] | undefined = info?.wings?.names;
  const ids: number[] | undefined = info?.wings?.ids;
  let label = "";
  if (names && names.length) {
    const raw = (names[0] || "").toString().trim();
    // Pattern 1: "الجناح 5 - الوسيل"
    let m = raw.match(/الجناح\s*(\d+)\s*[-–]?\s*(.+)/);
    if (m) {
      const num = m[1];
      const name = (m[2] || "").trim();
      label = `${name} (${num})`;
    } else {
      // Pattern 2: "الوسيل - الجناح 5" أو "الوسيل — الجناح 5"
      m = raw.match(/(.+)\s*[-–]\s*الجناح\s*(\d+)/);
      if (m) {
        const name = (m[1] || "").trim();
        const num = m[2];
        label = `${name} (${num})`;
      } else {
        // Pattern 3: "الجناح 5"
        m = raw.match(/الجناح\s*(\d+)/);
        if (m) {
          label = `(${m[1]})`;
        } else {
          // Fallback to raw name
          label = raw;
        }
      }
    }
  } else if (ids && ids.length) {
    label = `(${ids[0]})`;
  }
  return label;
});

const getTileByTo = (path: string) => tiles.find(t => t.to === path);
const shortcuts = computed(() => {
  const tMonitor = getTileByTo("/attendance/wing/monitor");
  const tMissing = getTileByTo("/wing/attendance/missing");
  const tIncidents = getTileByTo("/wing/incidents");
  const tReports = getTileByTo("/wing/reports");
  return [
    {
      key: "attendance_today",
      label: tMonitor?.title || "مراقبة حضور الجناح",
      icon: tMonitor?.icon || "solar:radar-2-bold-duotone",
      to: { name: "wing-attendance-monitor", query: { date: dateISO.value } },
    },
    {
      key: "missing_entries",
      label: tMissing?.title || "حصص بلا إدخال",
      icon: tMissing?.icon || "solar:playlist-remove-bold-duotone",
      to: { name: "wing-attendance-missing", query: { date: dateISO.value } },
    },
    {
      key: "incidents",
      label: tIncidents?.title || "البلاغات",
      icon: tIncidents?.icon || "solar:shield-warning-bold-duotone",
      to: { name: "wing-incidents" },
    },
    {
      key: "reports",
      label: tReports?.title || "تقارير",
      icon: tReports?.icon || "solar:chart-2-bold-duotone",
      to: { name: "wing-reports" },
    },
  ];
});

async function safeCall<T>(
  fn: () => Promise<T>,
  key: keyof typeof apiStatus.value
): Promise<T | null> {
  try {
    const res = await fn();
    // Mark success with 200
    apiStatus.value[key] = 200;
    return res;
  } catch (e: any) {
    const status = e?.response?.status ?? 0;
    apiStatus.value[key] = status || -1;
    // Do not throw to allow page content to render; top banner will show diagnostics
    return null;
  }
}

const currentDate = ref<string>("");
const dateStr = ref<string>(""); // DD/MM/YYYY
const selectedDateDMY = computed(() => dateStr.value || formatDateDMY(new Date()));
const dateISO = computed(() => parseDMYtoISO(dateStr.value) || toIsoDate(new Date()));
const isToday = computed(() => dateISO.value === toIsoDate(new Date()));

// === Weekly summary (Sun→Thu) ===
const weeklyLoading = ref<boolean>(false);
const weeklyHint = ref<string>("");
const weekFrom = ref<string>(""); // ISO YYYY-MM-DD
const weekTo = ref<string>("");   // ISO YYYY-MM-DD

// Day labels in Arabic aligned with JS getDay(): 0=Sunday..6=Saturday
const AR_DAYS = ["الأحد","الاثنين","الثلاثاء","الأربعاء","الخميس","الجمعة","السبت"];

type DayKPIs = {
  date: string;
  present_pct: number; present: number; total: number;
  absent: number; late: number; excused: number; runaway: number;
  exit_events_total: number;
};

const weeklyDays = ref<{ iso: string; label: string; kpis?: DayKPIs | null }[]>([]);
const weeklyKPIs = ref<{ present_pct: number; present: number; total: number; absent: number; late: number; excused: number; runaway: number; exit_events_total: number }>({
  present_pct: 0, present: 0, total: 0, absent: 0, late: 0, excused: 0, runaway: 0, exit_events_total: 0,
});

function toISO(d: Date): string { const y=d.getFullYear(); const m=String(d.getMonth()+1).padStart(2,'0'); const dd=String(d.getDate()).padStart(2,'0'); return `${y}-${m}-${dd}`; }
function fromISO(s: string): Date { const [y,m,d]=s.split('-').map(Number); return new Date(y, (m||1)-1, d||1); }

function computeWeekRange(anchorISO: string) {
  const d = fromISO(anchorISO);
  const dow = d.getDay(); // 0=Sun
  // Start = Sunday, End = Thursday
  const start = new Date(d); start.setDate(d.getDate() - dow);
  const end = new Date(start); end.setDate(start.getDate() + 4);
  weekFrom.value = toISO(start);
  weekTo.value = toISO(end);
}

function buildWeekDays() {
  const start = fromISO(weekFrom.value);
  const end = fromISO(weekTo.value);
  const days: { iso: string; label: string; kpis?: DayKPIs | null }[] = [];
  const cur = new Date(start);
  while (cur <= end) {
    const iso = toISO(cur);
    const label = AR_DAYS[cur.getDay()] || iso;
    days.push({ iso, label, kpis: null });
    cur.setDate(cur.getDate() + 1);
  }
  weeklyDays.value = days;
}

async function loadWeekly() {
  weeklyLoading.value = true; weeklyHint.value = "";
  try {
    buildWeekDays();
    const calls = weeklyDays.value.map((d) => getWingOverview({ date: d.iso }));
    const results = await Promise.allSettled(calls);
    // Aggregate
    let totalPresent = 0, totalTotal = 0, totalAbsent = 0, totalLate = 0, totalExcused = 0, totalRunaway = 0, totalExits = 0;
    let daysOk = 0;
    results.forEach((res, idx) => {
      if (res.status === 'fulfilled' && (res.value as any)?.kpis) {
        const k: any = (res.value as any).kpis;
        const day: DayKPIs = {
          date: weeklyDays.value[idx].iso,
          present_pct: Number(k.present_pct || 0),
          present: Number(k.present || 0),
          total: Number(k.total || 0),
          absent: Number(k.absent || 0),
          late: Number(k.late || 0),
          excused: Number(k.excused || 0),
          runaway: Number(k.runaway || 0),
          exit_events_total: Number(k.exit_events_total || 0),
        };
        weeklyDays.value[idx].kpis = day as any;
        totalPresent += day.present;
        totalTotal += day.total;
        totalAbsent += day.absent;
        totalLate += day.late;
        totalExcused += day.excused;
        totalRunaway += day.runaway;
        totalExits += day.exit_events_total;
        daysOk += 1;
      } else {
        weeklyDays.value[idx].kpis = null;
      }
    });
    weeklyKPIs.value = {
      present_pct: totalTotal > 0 ? (totalPresent / totalTotal) * 100 : 0,
      present: totalPresent,
      total: totalTotal,
      absent: totalAbsent,
      late: totalLate,
      excused: totalExcused,
      runaway: totalRunaway,
      exit_events_total: totalExits,
    };
    weeklyHint.value = daysOk ? `تم احتساب ${daysOk} يومًا بنجاح` : 'لا بيانات متاحة لنطاق التواريخ';
  } catch (e) {
    weeklyHint.value = 'تعذر احتساب الملخّص الأسبوعي';
  } finally {
    weeklyLoading.value = false;
  }
}

function resetWeekRange() { computeWeekRange(dateISO.value); reloadWeekly(); }
function reloadWeekly() { if (weekFrom.value && weekTo.value) loadWeekly(); }

// Compose weekly DOCX href
const weeklyWordHref = computed(() => {
  const params = new URLSearchParams();
  if (selectedWingId?.value) params.set('wing_id', String(selectedWingId.value));
  if (weekFrom.value) params.set('from', weekFrom.value);
  if (weekTo.value) params.set('to', weekTo.value);
  return backendUrl(`/api/v1/wing/weekly-summary/export.docx/?${params.toString()}`);
});

// Print: focus mode on the weekly card
function printWeekly() {
  try {
    document.body.classList.add('print-focus-mode');
    // Ensure our card has the focus class (already has print-focus-target)
    window.print();
  } finally {
    setTimeout(() => { document.body.classList.remove('print-focus-mode'); }, 300);
  }
}

async function loadData() {
  loading.value = true;
  error.value = null;
  try {
    const d = dateISO.value;
    currentDate.value = d;
    const [meProf, me, ov, ms] = await Promise.all([
      safeCall(() => getMe(), "me"),
      safeCall(() => getWingMe(), "wingMe"),
      safeCall(() => getWingOverview({ date: d }), "overview"),
      safeCall(() => getWingMissing({ date: d }), "missing"),
    ]);
    if (meProf) meProfile.value = meProf;
    if (me) meInfo.value = me;
    if (ov && (ov as any).kpis) kpis.value = (ov as any).kpis;
    if (ms) {
      const items = (ms as any)?.items || [];
      const count = (ms as any)?.count ?? items.length;
      missing.value = { count, items };
    }
    // If all failed, set a readable error text
    const failedAll = [apiStatus.value.overview, apiStatus.value.missing].every(
      (s) => s && s !== 200
    );
    if (failedAll) {
      error.value =
        "تعذر جلب بيانات الجناح. تحقق من صلاحياتك والربط بالجناح ومن توفر واجهات /api/wing/*";
    }
  } catch (e: any) {
    error.value = e?.message || "تعذر جلب بيانات الجناح (الشبكة أو الصلاحيات)";
  } finally {
    // Log diagnostics to help أثناء الاختبار
    try {
      console.debug("[WingDashboard] apiStatus", apiStatus.value);
    } catch {}
    // بناء قائمة الصفوف المتاحة
    buildClassOptions();
    // تهيئة الاختيار من الاستعلام أو التخزين
    initSelectionFromQueryOrStorage();
    initPeriodsFromQueryOrStorage();
    initTeachersFromQueryOrStorage();
    // Update last updated time (ASCII)
    try { lastUpdated.value = timeAscii(new Date()); } catch {}
    loading.value = false;
  }
}

// تحديث تلقائي دوري لتحريك الصفوف تلقائيًا من "بلا إدخال" إلى "تم الإدخال" بعد حفظ المعلم
const AUTO_REFRESH_MS = 15000; // 15 ثانية مثل صفحة المراقبة
let refreshTimer: any = null;
function startAutoRefresh() {
  stopAutoRefresh();
  refreshTimer = setInterval(() => {
    if (!document.hidden && isToday.value && !paused.value) {
      loadData();
    }
  }, AUTO_REFRESH_MS);
}
function stopAutoRefresh() {
  if (refreshTimer) {
    clearInterval(refreshTimer);
    refreshTimer = null;
  }
}
function handleVisibility() {
  if (!document.hidden && !paused.value) {
    // عند العودة للتبويب، حدّث مباشرةً
    loadData();
  }
}

function onDateChanged() {
  // Sync URL query (?date=YYYY-MM-DD) while keeping existing params (e.g., classes)
  const q = { ...route.query } as any;
  const iso = dateISO.value;
  if (iso) q.date = iso; else delete q.date;
  router.replace({ query: q }).catch(() => {});
  // When date changes, refresh now; auto-refresh will only tick for today
  loadData();
}

onMounted(() => {
  // Initialize date from URL (?date=YYYY-MM-DD) or default to today
  const qDate = String(route.query.date || "").trim();
  if (qDate) {
    const dmy = formatISOtoDMY(qDate);
    if (dmy) dateStr.value = dmy; else dateStr.value = formatDateDMY(new Date());
  } else {
    dateStr.value = formatDateDMY(new Date());
  }
  startAutoRefresh();
  startLiveClock();
  document.addEventListener("visibilitychange", handleVisibility);
});

onBeforeUnmount(() => {
  stopAutoRefresh();
  stopLiveClock();
  document.removeEventListener("visibilitychange", handleVisibility);
});

onMounted(() => loadData());

function buildClassOptions() {
  const map = new Map<number, string | null | undefined>();
  for (const it of missing.value.items || []) {
    if (!map.has(it.class_id)) map.set(it.class_id, it.class_name);
  }
  const opts = Array.from(map.entries()).map(([id, name]) => ({ id, name }));
  // ترتيب أبجدي بحسب الاسم ثم الرقم
  opts.sort((a, b) => (a.name || "").localeCompare(b.name || "") || a.id - b.id);
  classOptions.value = opts;
}

function parseClassesParam(val: string | (string | null)[] | null | undefined): number[] {
  const s = Array.isArray(val) ? val.join(",") : val || "";
  return s
    .split(",")
    .map((x) => parseInt(x.trim(), 10))
    .filter((n) => Number.isFinite(n));
}

function initSelectionFromQueryOrStorage() {
  // من عنوان الصفحة أولاً
  const q = route.query.classes as any;
  let ids = parseClassesParam(q);
  // ثم من التخزين المحلي إذا لم يوجد في الرابط
  if (!ids.length) {
    try {
      const raw = localStorage.getItem("wing_selected_classes");
      if (raw) ids = JSON.parse(raw);
    } catch {}
  }
  if (ids.length) {
    selectedSet.value = new Set(ids);
  }
}

watch(
  selectedSet,
  (set) => {
    // مزامنة مع الرابط
    const ids = Array.from(set.values());
    const query = { ...route.query } as any;
    if (ids.length) query.classes = ids.join(",");
    else delete query.classes;
    router.replace({ query }).catch(() => {});
    // تخزين محلي
    try {
      localStorage.setItem("wing_selected_classes", JSON.stringify(ids));
    } catch {}
  },
  { deep: true }
);

const selectedLabel = computed(() => {
  const total = classOptions.value.length;
  const cnt = selectedSet.value.size;
  if (!total) return "لا صفوف";
  if (!cnt || cnt === total) return "كل الصفوف";
  return `محدد (${cnt}/${total})`;
});

const selectionHint = computed(() => {
  const cnt = selectedSet.value.size;
  if (!cnt) return "لا يوجد ترشيح مفعل";
  return `ترشيح مفعل: ${cnt} صف`;
});

function toggleClass(id: number) {
  const s = new Set(selectedSet.value);
  if (s.has(id)) s.delete(id);
  else s.add(id);
  selectedSet.value = s;
}
function selectAll() {
  const s = new Set<number>();
  for (const o of classOptions.value) s.add(o.id);
  selectedSet.value = s;
}
function clearAll() {
  selectedSet.value = new Set();
}
function invertSelection() {
  const s = new Set<number>();
  for (const o of classOptions.value) {
    if (!selectedSet.value.has(o.id)) s.add(o.id);
  }
  selectedSet.value = s;
}

// ---- Periods filter ----
const periodOptions = computed<number[]>(() => {
  const set = new Set<number>();
  for (const it of missing.value.items || []) {
    const p = Number(it.period_number || it.period || 0);
    if (p > 0) set.add(p);
  }
  return Array.from(set.values()).sort((a, b) => a - b);
});
const selectedPeriodsSet = ref<Set<number>>(new Set());

function parseNumList(val: any): number[] {
  const s = Array.isArray(val) ? val.join(",") : (val || "");
  return s
    .split(",")
    .map((x: string) => parseInt(String(x).trim(), 10))
    .filter((n: number) => Number.isFinite(n));
}

function initPeriodsFromQueryOrStorage() {
  try {
    const q = route.query.periods as any;
    const fromQ = parseNumList(q);
    const fromLs = JSON.parse(localStorage.getItem("wing_selected_periods") || "[]");
    const init = (fromQ.length ? fromQ : Array.isArray(fromLs) ? fromLs : []) as number[];
    if (init.length) selectedPeriodsSet.value = new Set(init);
  } catch {}
}

watch(selectedPeriodsSet, (set) => {
  const ids = Array.from(set.values());
  const query = { ...route.query } as any;
  if (ids.length) query.periods = ids.join(",");
  else delete query.periods;
  router.replace({ query }).catch(() => {});
  try { localStorage.setItem("wing_selected_periods", JSON.stringify(ids)); } catch {}
}, { deep: true });

const periodsLabel = computed(() => {
  const total = periodOptions.value.length;
  const cnt = selectedPeriodsSet.value.size;
  if (!total) return "لا حصص";
  if (!cnt || cnt === total) return "كل الحصص";
  return `حصص (${cnt}/${total})`;
});

function togglePeriod(p: number) {
  const s = new Set(selectedPeriodsSet.value);
  if (s.has(p)) s.delete(p); else s.add(p);
  selectedPeriodsSet.value = s;
}
function selectAllPeriods() { selectedPeriodsSet.value = new Set(periodOptions.value); }
function clearAllPeriods() { selectedPeriodsSet.value = new Set(); }
function invertPeriods() {
  const s = new Set<number>();
  for (const p of periodOptions.value) if (!selectedPeriodsSet.value.has(p)) s.add(p);
  selectedPeriodsSet.value = s;
}

// ---- Teachers filter ----
const teacherOptions = computed<{ id?: number; name?: string }[]>(() => {
  const map = new Map<string, { id?: number; name?: string }>();
  for (const it of missing.value.items || []) {
    const id = Number(it.teacher_id || 0) || undefined;
    const name = (it.teacher_name || "").toString().trim() || undefined;
    const key = id ? `id:${id}` : name ? `name:${name}` : "";
    if (!key) continue;
    if (!map.has(key)) map.set(key, { id, name });
  }
  return Array.from(map.values()).sort((a, b) => (a.name || "").localeCompare(b.name || ""));
});
const selectedTeachersSet = ref<Set<number | string>>(new Set());

function initTeachersFromQueryOrStorage() {
  try {
    const q = route.query.teachers as any;
    const fromQ = parseNumList(q);
    const fromLs = JSON.parse(localStorage.getItem("wing_selected_teachers") || "[]");
    const init = (fromQ.length ? fromQ : Array.isArray(fromLs) ? fromLs : []) as number[];
    if (init.length) selectedTeachersSet.value = new Set(init);
  } catch {}
}

watch(selectedTeachersSet, (set) => {
  const vals = Array.from(set.values());
  const ids = vals.filter((v) => typeof v === 'number') as number[];
  const query = { ...route.query } as any;
  if (ids.length) query.teachers = ids.join(","); else delete query.teachers;
  router.replace({ query }).catch(() => {});
  try { localStorage.setItem("wing_selected_teachers", JSON.stringify(ids)); } catch {}
}, { deep: true });

const teachersLabel = computed(() => {
  const total = teacherOptions.value.length;
  const cnt = selectedTeachersSet.value.size;
  if (!total) return "لا معلمين";
  if (!cnt || cnt === total) return "كل المعلمين";
  return `معلمين (${cnt}/${total})`;
});

function toggleTeacher(idOrName: number | string) {
  const s = new Set(selectedTeachersSet.value);
  if (s.has(idOrName)) s.delete(idOrName); else s.add(idOrName);
  selectedTeachersSet.value = s;
}
function selectAllTeachers() {
  const s = new Set<number | string>();
  for (const t of teacherOptions.value) s.add(t.id ?? t.name ?? "");
  selectedTeachersSet.value = s;
}
function clearAllTeachers() { selectedTeachersSet.value = new Set(); }
function invertTeachers() {
  const s = new Set<number | string>();
  for (const t of teacherOptions.value) {
    const key = t.id ?? t.name ?? "";
    if (!selectedTeachersSet.value.has(key)) s.add(key);
  }
  selectedTeachersSet.value = s;
}

// Limit for rendering large tables (progressive reveal)
const showLimit = ref<number>(200);

const filteredMissing = computed(() => {
  let items = (missing.value.items || []).slice();
  // Filter by classes
  const classIds = selectedSet.value;
  if (classIds.size) items = items.filter((r) => classIds.has(r.class_id));
  // Filter by periods
  const periods = selectedPeriodsSet.value;
  if (periods.size) items = items.filter((r) => periods.has(Number(r.period_number || r.period || 0)));
  // Filter by teachers (by numeric id only to avoid ambiguity)
  const teacherIds = new Set(
    Array.from(selectedTeachersSet.value.values()).filter((v) => typeof v === 'number') as number[]
  );
  if (teacherIds.size) items = items.filter((r) => teacherIds.has(Number(r.teacher_id || 0)));
  return { count: items.length, items };
});

const visibleMissingItems = computed(() => {
  const arr = filteredMissing.value.items || [];
  return arr.slice(0, showLimit.value);
});

const missingScrollEl = ref<HTMLElement | null>(null);
function onMissingScroll() {
  const el = missingScrollEl.value as HTMLElement | null;
  if (!el) return;
  const nearBottom = el.scrollTop + el.clientHeight >= el.scrollHeight - 8;
  if (nearBottom && showLimit.value < filteredMissing.value.count) {
    showLimit.value = Math.min(filteredMissing.value.count, showLimit.value + 200);
  }
}

watch(() => filteredMissing.value.count, () => {
  // Reset window when filter results change
  showLimit.value = 200;
});

const kpiCards = computed(() => {
  const k = kpis.value || {};
  const pct = typeof k.present_pct === "number" ? k.present_pct.toFixed(1) + "%" : "--";
  const total = k.total ?? 0;
  const present = k.present ?? 0;
  const absent = k.absent ?? 0;
  const late = k.late ?? 0;
  const excused = k.excused ?? 0;
  const runaway = k.runaway ?? 0;
  const exitOpen = k.exit_events_open ?? 0;
  const exitTotal = k.exit_events_total ?? 0;
  return [
    {
      key: "att_pct",
      label: "نسبة الحضور",
      value: pct,
      sub: `الإجمالي ${total} | حاضر ${present}`,
      icon: "solar:chart-2-bold-duotone",
      color: "var(--color-success)",
    },
    {
      key: "present",
      label: "حاضر",
      value: present,
      sub: `من أصل ${total}`,
      icon: "solar:check-circle-bold-duotone",
      color: "var(--color-success)",
    },
    {
      key: "absent",
      label: "غائب",
      value: absent,
      sub: "",
      icon: "solar:user-cross-bold-duotone",
      color: "var(--color-danger)",
    },
    {
      key: "late",
      label: "متأخر",
      value: late,
      sub: "",
      icon: "solar:clock-circle-bold-duotone",
      color: "var(--color-warning)",
    },
    {
      key: "excused",
      label: "إعفاء/مُبرر",
      value: excused,
      sub: "",
      icon: "solar:shield-check-bold-duotone",
      color: "var(--color-secondary)",
    },
    {
      key: "runaway",
      label: "هروب",
      value: runaway,
      sub: "",
      icon: "solar:running-bold-duotone",
      color: "var(--color-danger)",
    },
    {
      key: "exit_open",
      label: "إذونات خروج (مفتوحة)",
      value: exitOpen,
      sub: exitTotal ? `الإجمالي ${exitTotal}` : "",
      icon: "solar:logout-3-bold-duotone",
      color: "var(--color-info)",
    },
    {
      key: "total",
      label: "إجمالي الطلاب",
      value: total,
      sub: "",
      icon: "solar:users-group-rounded-bold-duotone",
      color: "var(--color-secondary)",
    },
  ];
});
// --- Day state computation (unexcused ratio policy) ---
const unexcusedEstimate = computed(() => {
  // We don't have explicit unexcused in overview KPIs; approximate as (absent - excused) but never below 0
  const k = kpis.value || {};
  const absent = Number(k.absent || 0);
  const excused = Number(k.excused || 0);
  const val = Math.max(0, absent - excused);
  return val;
});

const dayState = computed(() => {
  const total = Number(kpis.value?.total || 0);
  const unx = Number(unexcusedEstimate.value || 0);
  if (!total) return "none";
  const ratio = unx / total;
  if (ratio >= 0.15) return "danger";
  if (ratio >= 0.07) return "warning";
  return "normal";
});

const dayStateBadge = computed(() => {
  const s = dayState.value as "none" | "normal" | "warning" | "danger";
  switch (s) {
    case "danger":
      return { text: "حالة اليوم: خطر", variant: "unexcused" };
    case "warning":
      return { text: "حالة اليوم: تحذير", variant: "none" };
    case "normal":
      return { text: "حالة اليوم: طبيعي", variant: "excused" };
    default:
      return { text: "", variant: "none" };
  }
});

// --- Live date/time for today's card (header) ---
const liveDate = ref<string>("");
const liveTime = ref<string>("");
let liveTimer: any = null;

function updateNow() {
  const now = new Date();
  liveDate.value = formatDateDMY(now);
  // Always format time as HH:mm with ASCII digits to avoid locale-dependent numerals
  const hh = String(now.getHours()).padStart(2, '0');
  const mm = String(now.getMinutes()).padStart(2, '0');
  liveTime.value = `${hh}:${mm}`;
}

function startLiveClock() {
  stopLiveClock();
  updateNow();
  // Minute precision is sufficient for a dashboard badge
  liveTimer = setInterval(updateNow, 60_000);
}

function stopLiveClock() {
  if (liveTimer) {
    clearInterval(liveTimer);
    liveTimer = null;
  }
}
</script>
<style scoped>
.header-icon {
  font-size: 26px;
  color: var(--maron-primary);
}
.table-responsive {
  max-height: 420px;
}

/* بطاقات KPI مربعة صغيرة جدًا */
.stat-card {
  aspect-ratio: 1 / 1; /* تجعل البطاقة مربعة */
  display: grid;
  grid-template-rows: auto 1fr auto auto; /* أيقونة | الفراغ/القيمة | التحت */
  align-items: center;
  justify-items: center;
  gap: 0.2rem;
  padding: 0.5rem !important; /* تقليل الحشوة لمستوى أدنى */
}
/* تصغير الأيقونة داخل البطاقة */
.stat-card :deep(svg) {
  font-size: clamp(0.95rem, 1.4vw, 1.25rem);
}
/* قيمة المؤشر صغيرة قدر الإمكان مع الحفاظ على الوضوح */
.stat-card .value {
  line-height: 1;
  font-weight: 700;
  font-size: clamp(1rem, 1.6vw, 1.35rem);
}
.stat-card .label {
  white-space: nowrap;
  text-overflow: ellipsis;
  overflow: hidden;
  max-width: 100%;
  font-size: 0.72rem;
}
.stat-card .sub {
  max-width: 100%;
  white-space: nowrap;
  text-overflow: ellipsis;
  overflow: hidden;
  color: #6c757d;
  font-size: 0.7rem;
}

/* تأثير طفيف للاحترافية */
.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.08);
  transition:
    transform 0.15s ease,
    box-shadow 0.15s ease;
}

/* شريط أدوات تحديد الصفوف */
.class-toolbar .btn {
  padding: 0.15rem 0.5rem;
}
</style>
