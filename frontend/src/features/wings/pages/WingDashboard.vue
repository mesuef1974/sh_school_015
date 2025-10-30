<template>
  <section class="wing-dashboard d-grid gap-3 page-grid page-grid-wide">
    <div class="d-flex align-items-center gap-2 mb-2 header-bar frame">
      <Icon :icon="tileMeta.icon" class="header-icon" :style="{ color: tileMeta.color }" />
      <div>
        <div class="fw-bold">{{ tileMeta.title }}</div>
        <div class="text-muted small" v-if="wingLabelFull">{{ wingLabelFull }}</div>
        <div class="text-muted small" v-else>ملخص ومؤشرات اليوم لنطاق جناحك</div>
      </div>
      <span class="ms-auto"></span>
      <DsButton variant="primary" icon="solar:refresh-bold-duotone" @click="loadData">تحديث</DsButton>
    </div>

    <div v-if="loading" class="alert alert-light border d-flex align-items-center gap-2">
      <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
      <span>جاري تحميل مؤشرات الجناح...</span>
    </div>
    <div v-if="error" class="alert alert-danger">حدث خطأ أثناء تحميل البيانات: {{ error }}</div>

    <!-- شبكة اختصارات سريعة حتى لا تبدو الصفحة فارغة -->
    <div class="row g-2 mb-3">
      <div class="col-6 col-md-3" v-for="s in shortcuts" :key="s.key">
        <a class="auto-card p-3 text-center text-decoration-none h-100 d-block" :href="s.href">
          <Icon :icon="s.icon" class="text-2xl mb-2" />
          <div class="small fw-bold">{{ s.label }}</div>
        </a>
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
        <div class="auto-card stat-card p-3 text-center h-100">
          <Icon :icon="c.icon" class="mb-1" :style="{ color: c.color }" />
          <div class="label small fw-bold text-muted">{{ c.label }}</div>
          <div class="value" :style="{ color: c.color }">{{ c.value }}</div>
          <div class="sub small text-muted" v-if="c.sub">{{ c.sub }}</div>
        </div>
      </div>

      <div class="col-12">
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
              <div v-else class="table-responsive">
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
                          v-if="row.subject_name"
                          class="d-inline-flex align-items-center gap-1"
                        >
                          <Icon :icon="subjectIcon(row.subject_name)" class="me-1" />
                          <span>{{ row.subject_name }}</span>
                        </span>
                        <span v-else>—</span>
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
import { onMounted, onBeforeUnmount, ref, computed, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { getWingMe, getWingOverview, getWingMissing, getMe } from "../../../shared/api/client";
import DsButton from "../../../components/ui/DsButton.vue";
import { tiles } from "../../../home/icon-tiles.config";
import { useWingContext } from "../../../shared/composables/useWingContext";
import { Icon } from "@iconify/vue";

const route = useRoute();
const router = useRouter();

// Unified header context and tile meta for Wing Dashboard
const { ensureLoaded, wingLabelFull } = useWingContext();
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

const shortcuts = computed(() => [
  {
    key: "attendance_today",
    label: "غياب اليوم",
    icon: "solar:calendar-bold-duotone",
    href: "#/attendance/wing/monitor",
  },
  {
    key: "missing_entries",
    label: "حصص بلا إدخال",
    icon: "solar:warning-bold-duotone",
    href: "#/attendance/wing/monitor",
  },
  {
    key: "discipline",
    label: "الانضباط",
    icon: "solar:shield-plus-bold-duotone",
    href: "#/supervisor/discipline",
  },
  {
    key: "reports",
    label: "تقارير الجناح",
    icon: "solar:chart-2-bold-duotone",
    href: "#/supervisor/reports",
  },
]);

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

async function loadData() {
  loading.value = true;
  error.value = null;
  try {
    const today = new Date().toISOString().slice(0, 10);
    currentDate.value = today;
    const [meProf, me, ov, ms] = await Promise.all([
      safeCall(() => getMe(), "me"),
      safeCall(() => getWingMe(), "wingMe"),
      safeCall(() => getWingOverview({ date: today }), "overview"),
      safeCall(() => getWingMissing({ date: today }), "missing"),
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
    loading.value = false;
  }
}

// تحديث تلقائي دوري لتحريك الصفوف تلقائيًا من "بلا إدخال" إلى "تم الإدخال" بعد حفظ المعلم
const AUTO_REFRESH_MS = 30000; // 30 ثانية
let refreshTimer: any = null;
function startAutoRefresh() {
  stopAutoRefresh();
  refreshTimer = setInterval(() => {
    if (!document.hidden) {
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
  if (!document.hidden) {
    // عند العودة للتبويب، حدّث مباشرةً
    loadData();
  }
}

onMounted(() => {
  startAutoRefresh();
  document.addEventListener("visibilitychange", handleVisibility);
});

onBeforeUnmount(() => {
  stopAutoRefresh();
  document.removeEventListener("visibilitychange", handleVisibility);
});

onMounted(loadData);

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

const filteredMissing = computed(() => {
  const ids = selectedSet.value;
  if (!ids.size) return { count: missing.value.count, items: missing.value.items };
  const items = (missing.value.items || []).filter((r) => ids.has(r.class_id));
  return { count: items.length, items };
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
