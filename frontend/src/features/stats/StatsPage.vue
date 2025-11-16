<template>
  <section class="d-grid gap-3">
    <WingPageHeader icon="solar:chart-2-bold-duotone" title="لوحة الإحصائيات" :subtitle="'نسب وملخصات الحضور لليوم المحدد'">
      <template #actions>
        <div class="toolbar-actions d-flex align-items-center gap-2 flex-wrap">
          <DatePickerDMY
            :id="'stats-date'"
            v-model="dateStr"
            :aria-label="'اختيار التاريخ'"
            inputClass="form-control toolbar-date"
            wrapperClass="m-0"
            @change="loadSummary"
          />
          <!-- Mode selector -->
          <select
            v-model="mode"
            class="form-select form-select-sm toolbar-mode"
            @change="onModeChange"
          >
            <option value="school">كل المدرسة</option>
            <option v-if="isTeacher" value="teacher_all">صفوفي (كل المواد)</option>
            <option v-if="isTeacher" value="teacher_subject">صفوفي (لمادة محددة)</option>
            <option v-if="isTeacher" value="class">صف محدد</option>
          </select>
          <!-- Subject selector -->
          <select
            v-if="mode === 'teacher_subject'"
            v-model.number="selectedSubjectId"
            class="form-select form-select-sm toolbar-subject"
            @change="loadSummary"
          >
            <option :value="0" disabled>اختر المادة</option>
            <option v-for="s in teacherSubjects" :key="s.id" :value="s.id">
              {{ s.name || "مادة #" + s.id }}
            </option>
          </select>
          <!-- Class selector -->
          <select
            v-if="mode === 'class'"
            v-model.number="selectedClassId"
            class="form-select form-select-sm toolbar-class"
            @change="loadSummary"
          >
            <option :value="0" disabled>اختر الصف</option>
            <option v-for="c in teacherClasses" :key="c.id" :value="c.id">
              {{ c.name || "صف #" + c.id }}
            </option>
          </select>
        </div>
      </template>
    </WingPageHeader>

    <div class="row g-3">
      <div class="col-12">
        <div class="row g-3">
          <div class="col-6 col-md-4 col-lg-3">
            <KpiCard
              :loading="loading"
              title="الحضور اليوم"
              :value="kpis.present_pct"
              suffix="%"
              icon="bi bi-people"
            />
          </div>
          <div class="col-6 col-md-4 col-lg-3">
            <KpiCard
              :loading="loading"
              title="الغياب"
              :value="kpis.absent"
              icon="bi bi-person-x"
              variant="danger"
            />
          </div>
          <div class="col-6 col-md-4 col-lg-3">
            <KpiCard
              :loading="loading"
              title="التأخر"
              :value="kpis.late"
              icon="bi bi-alarm"
              variant="warning"
            />
          </div>
          <div class="col-6 col-md-4 col-lg-3">
            <KpiCard
              :loading="loading"
              title="إذن خروج"
              :value="kpis.exit_events_open ?? kpis.excused"
              icon="bi bi-shield-check"
              variant="secondary"
            />
          </div>
          <div class="col-6 col-md-4 col-lg-3">
            <KpiCard
              :loading="loading"
              title="هروب"
              :value="kpis.runaway"
              icon="bi bi-person-dash"
              variant="danger"
            />
          </div>
          <div class="col-6 col-md-4 col-lg-3">
            <KpiCard
              :loading="loading"
              title="انصراف مبكر"
              :value="kpis.left_early"
              icon="bi bi-box-arrow-left"
              variant="warning"
            />
          </div>
        </div>

        <div class="row g-3 mt-2">
          <div class="col-12 col-md-6">
            <DsCard title="توزيع حالات الحضور">
              <div ref="pieChartRef" style="width: 100%; height: 300px"></div>
            </DsCard>
          </div>
          <div class="col-12 col-md-6">
            <DsCard title="مقارنة أفضل وأسوأ الصفوف">
              <div ref="barChartRef" style="width: 100%; height: 300px"></div>
            </DsCard>
          </div>
        </div>

        <div class="auto-card p-3 mt-3">
          <div class="d-flex align-items-center mb-2">
            <div class="fw-bold">صفوف اليوم المميزة</div>
            <span class="ms-auto small text-muted">{{ formatDateDMY(summary?.date) }}</span>
          </div>
          <div class="row g-2">
            <div class="col-12 col-md-6">
              <div class="p-2 border rounded-3">
                <div class="fw-bold mb-1">Top</div>
                <ul class="small mb-0">
                  <li v-for="t in summary?.top_classes || []" :key="'t' + t.class_id">
                    صف {{ t.class_name || "#" + t.class_id }} — {{ t.present_pct }}%
                  </li>
                  <li v-if="(summary?.top_classes || []).length === 0" class="text-muted">
                    لا بيانات
                  </li>
                </ul>
              </div>
            </div>
            <div class="col-12 col-md-6">
              <div class="p-2 border rounded-3">
                <div class="fw-bold mb-1">بحاجة متابعة</div>
                <ul class="small mb-0">
                  <li v-for="w in summary?.worst_classes || []" :key="'w' + w.class_id">
                    صف {{ w.class_name || "#" + w.class_id }} — {{ w.present_pct }}%
                  </li>
                  <li v-if="(summary?.worst_classes || []).length === 0" class="text-muted">
                    لا بيانات
                  </li>
                </ul>
              </div>
            </div>
          </div>
          <div v-if="error" class="alert alert-danger mt-2 mb-0">{{ error }}</div>
        </div>

        <!-- Exit analytics -->
        <div class="row g-3 mt-2">
          <div class="col-12">
            <DsCard>
              <template #title>
                <div class="d-flex align-items-center gap-2">
                  <Icon icon="solar:exit-bold-duotone" />
                  <span>إحصائيات خروج الطلاب من الفصل</span>
                </div>
              </template>
              <div class="row g-3">
                <div class="col-6 col-md-3">
                  <KpiCard
                    :loading="exitLoading"
                    title="عدد حالات الخروج"
                    :value="exitKpis.total"
                    icon="bi bi-box-arrow-up-right"
                    variant="secondary"
                  />
                </div>
                <div class="col-6 col-md-3">
                  <KpiCard
                    :loading="exitLoading"
                    title="متوسط الوقت خارج الفصل"
                    :value="exitKpis.avg_minutes"
                    suffix="دقيقة"
                    icon="bi bi-clock"
                    variant="info"
                  />
                </div>
                <div class="col-6 col-md-3">
                  <KpiCard
                    :loading="exitLoading"
                    title="أطول مدة"
                    :value="exitKpis.max_minutes"
                    suffix="دقيقة"
                    icon="bi bi-stopwatch"
                    variant="warning"
                  />
                </div>
                <div class="col-6 col-md-3">
                  <KpiCard
                    :loading="exitLoading"
                    title="جارية الآن"
                    :value="exitKpis.open"
                    icon="bi bi-play-circle"
                    variant="success"
                  />
                </div>
                <div class="col-12 mt-2">
                  <div ref="exitDurationChartRef" style="width: 100%; height: 320px"></div>
                </div>
                <div class="col-12">
                  <div class="table-responsive small">
                    <table class="table table-sm align-middle mb-0" dir="rtl">
                      <thead>
                        <tr>
                          <th>الطالب</th>
                          <th>عدد الخروج</th>
                          <th>إجمالي الدقائق خارج الفصل</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="row in topStudentsByExits" :key="row.student_id">
                          <td>
                            {{ row.student_name ? row.student_name : "طالب #" + row.student_id }}
                          </td>
                          <td>{{ row.count }}</td>
                          <td>{{ row.totalMinutes }}</td>
                        </tr>
                        <tr v-if="topStudentsByExits.length === 0">
                          <td colspan="3" class="text-center text-muted">
                            لا توجد بيانات خروج لهذا اليوم
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
              <div v-if="exitError" class="alert alert-danger mt-3 mb-0">{{ exitError }}</div>
            </DsCard>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch, nextTick } from "vue";
import { useAuthStore } from "../../app/stores/auth";
import {
  getAttendanceSummary,
  getTeacherClasses,
  getExitEvents,
  getTeacherTimetableWeekly,
} from "../../shared/api/client";
import KpiCard from "../../widgets/KpiCard.vue";
import DsButton from "../../components/ui/DsButton.vue";
import DsCard from "../../components/ui/DsCard.vue";
import * as echarts from "echarts/core";
import { PieChart, BarChart } from "echarts/charts";
import { formatDateDMY } from "../../shared/utils/date";
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import DatePickerDMY from "../../components/ui/DatePickerDMY.vue";
import WingPageHeader from "../../components/ui/WingPageHeader.vue";

echarts.use([
  PieChart,
  BarChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  CanvasRenderer,
]);

const auth = useAuthStore();
const isSuper = computed(() => !!auth.profile?.is_superuser);
const isTeacher = computed(() => {
  const roles = auth.profile?.roles || [];
  return (
    roles.includes("teacher") ||
    roles.includes("subject_coordinator") ||
    !!auth.profile?.hasTeachingAssignments
  );
});

const dateStr = ref(new Date().toISOString().slice(0, 10));
const loading = ref(false);
const error = ref("");
const summary = ref<{
  date: string;
  scope: string;
  kpis: any;
  top_classes: any[];
  worst_classes: any[];
} | null>(null);
const kpis = computed(
  () =>
    summary.value?.kpis || {
      present_pct: null,
      absent: null,
      late: null,
      excused: null,
      runaway: null,
      left_early: null,
    }
);

// New filtering state for exit analytics and summary
const mode = ref<"school" | "teacher_all" | "teacher_subject" | "class">("school");
const teacherClasses = ref<{ id: number; name?: string }[]>([]);
const teacherSubjects = ref<{ id: number; name?: string }[]>([]);
const subjectToClasses = ref<Record<number, number[]>>({});
const selectedSubjectId = ref(0);
const selectedClassId = ref(0);

const pieChartRef = ref<HTMLDivElement>();
const barChartRef = ref<HTMLDivElement>();
const exitDurationChartRef = ref<HTMLDivElement>();
let pieChartInstance: echarts.ECharts | null = null;
let barChartInstance: echarts.ECharts | null = null;
let exitDurationChartInstance: echarts.ECharts | null = null;

// Exit analytics state
const exitLoading = ref(false);
const exitError = ref("");
const exitEvents = ref<
  {
    id: number;
    student_id: number;
    student_name?: string | null;
    started_at: string;
    returned_at?: string | null;
    duration_seconds?: number | null;
    reason?: string | null;
  }[]
>([]);

const exitKpis = computed(() => {
  const total = exitEvents.value.length;
  const open = exitEvents.value.filter((e) => !e.returned_at).length;
  const durations = exitEvents.value.map((e) => e.duration_seconds ?? 0);
  const sum = durations.reduce((a, b) => a + b, 0);
  const maxSec = durations.reduce((m, v) => Math.max(m, v), 0);
  const avg_minutes = total ? Math.round(sum / total / 60) : 0;
  const max_minutes = Math.round(maxSec / 60);
  return { total, open, avg_minutes, max_minutes };
});

const topStudentsByExits = computed(() => {
  const map: Record<
    string,
    { student_id: number; student_name?: string | null; count: number; totalMinutes: number }
  > = {};
  for (const e of exitEvents.value) {
    const key = String(e.student_id);
    const durMin = Math.round((e.duration_seconds ?? 0) / 60);
    if (!map[key]) {
      map[key] = {
        student_id: e.student_id,
        student_name: e.student_name,
        count: 0,
        totalMinutes: 0,
      };
    }
    if (e.student_name && !map[key].student_name) {
      map[key].student_name = e.student_name;
    }
    map[key].count += 1;
    map[key].totalMinutes += durMin;
  }
  return Object.values(map)
    .sort((a, b) => b.count - a.count || b.totalMinutes - a.totalMinutes)
    .slice(0, 10);
});

function onModeChange() {
  // Reset dependent selections when mode changes
  if (mode.value !== "teacher_subject") {
    selectedSubjectId.value = 0;
  }
  if (mode.value !== "class") {
    selectedClassId.value = 0;
  }
  loadSummary();
}

async function loadTeacherMeta() {
  if (!isTeacher.value || isSuper.value) return;
  try {
    const [clsRes, weekly] = await Promise.allSettled([
      getTeacherClasses(),
      getTeacherTimetableWeekly(),
    ]);
    if (clsRes.status === "fulfilled") {
      teacherClasses.value = clsRes.value.classes || [];
    }
    if (weekly.status === "fulfilled") {
      const days =
        weekly.value.days ||
        ({} as Record<
          string,
          {
            classroom_id: number;
            subject_id: number;
            classroom_name?: string;
            subject_name?: string;
          }[]
        >);
      const subjMap: Record<number, { id: number; name?: string }> = {};
      const s2c: Record<number, Set<number>> = {};
      for (const d of Object.keys(days)) {
        for (const p of days[d] || []) {
          if (!p?.subject_id || !p?.classroom_id) continue;
          subjMap[p.subject_id] = subjMap[p.subject_id] || {
            id: p.subject_id,
            name: p.subject_name,
          };
          if (!s2c[p.subject_id]) s2c[p.subject_id] = new Set<number>();
          s2c[p.subject_id].add(p.classroom_id);
        }
      }
      teacherSubjects.value = Object.values(subjMap);
      const obj: Record<number, number[]> = {};
      for (const sid of Object.keys(s2c)) {
        obj[Number(sid)] = Array.from(s2c[Number(sid)]);
      }
      subjectToClasses.value = obj;
    }
  } catch {}
}

async function loadSummary() {
  loading.value = true;
  error.value = "";
  try {
    if (mode.value === "school" || !isTeacher.value || isSuper.value) {
      const res = await getAttendanceSummary({ scope: "school", date: dateStr.value });
      summary.value = res;
    } else if (mode.value === "class") {
      if (!selectedClassId.value) {
        summary.value = null as any;
        return;
      }
      const s = await getAttendanceSummary({
        class_id: selectedClassId.value,
        date: dateStr.value,
      });
      // s already contains top/worst for that class not meaningful; build simple summary
      summary.value = {
        date: dateStr.value,
        scope: "class",
        kpis: s.kpis,
        top_classes: [],
        worst_classes: [],
      } as any;
    } else {
      // teacher_all or teacher_subject aggregated
      let classIds: number[] = [];
      if (mode.value === "teacher_all") {
        classIds = teacherClasses.value.map((c) => c.id).filter(Boolean) as number[];
      } else if (mode.value === "teacher_subject") {
        if (!selectedSubjectId.value) {
          summary.value = null as any;
          return;
        }
        classIds = (subjectToClasses.value[selectedSubjectId.value] || []).slice();
      }
      let total = 0,
        present = 0,
        absent = 0,
        late = 0,
        excused = 0,
        runaway = 0,
        left_early = 0;
      const perClass: { class_id: number; class_name?: string; present_pct: number }[] = [];
      for (const cid of classIds) {
        const s = await getAttendanceSummary({ class_id: cid, date: dateStr.value });
        const k = s.kpis || ({} as any);
        total += Number(k.total || 0);
        present += Number(k.present || 0);
        absent += Number(k.absent || 0);
        late += Number(k.late || 0);
        excused += Number(k.excused || 0);
        runaway += Number(k.runaway || 0);
        left_early += Number(k.left_early || 0);
        const pct = typeof k.present_pct === "number" ? k.present_pct : 0;
        const name = teacherClasses.value.find((c) => c.id === cid)?.name;
        perClass.push({ class_id: cid, class_name: name, present_pct: pct });
      }
      const present_pct = total ? Math.round((present / total) * 1000) / 10 : 0;
      const top_classes = [...perClass].sort((a, b) => b.present_pct - a.present_pct).slice(0, 4);
      const worst_classes = [...perClass].sort((a, b) => a.present_pct - b.present_pct).slice(0, 4);
      summary.value = {
        date: dateStr.value,
        scope: mode.value,
        kpis: { present_pct, absent, late, excused, runaway, left_early },
        top_classes,
        worst_classes,
      } as any;
    }
  } catch (e: any) {
    error.value = e?.response?.data?.detail || "تعذر تحميل المؤشرات";
  } finally {
    loading.value = false;
  }
  // Always refresh exit stats together
  await loadExitStats();
}

async function loadExitStats() {
  exitLoading.value = true;
  exitError.value = "";
  try {
    if (mode.value === "school" || !isTeacher.value || isSuper.value) {
      exitEvents.value = await getExitEvents({ date: dateStr.value });
    } else if (mode.value === "class") {
      if (!selectedClassId.value) {
        exitEvents.value = [];
        return;
      }
      exitEvents.value = await getExitEvents({
        date: dateStr.value,
        class_id: selectedClassId.value,
      });
    } else {
      // teacher_all or teacher_subject
      let classIds: number[] = [];
      if (mode.value === "teacher_all") {
        classIds = teacherClasses.value.map((c) => c.id).filter(Boolean) as number[];
      } else if (mode.value === "teacher_subject") {
        if (!selectedSubjectId.value) {
          exitEvents.value = [];
          return;
        }
        classIds = (subjectToClasses.value[selectedSubjectId.value] || []).slice();
      }
      const all: typeof exitEvents.value = [] as any;
      for (const cid of classIds) {
        const part = await getExitEvents({ date: dateStr.value, class_id: cid });
        all.push(...part);
      }
      exitEvents.value = all;
    }
  } catch (e: any) {
    exitError.value = e?.response?.data?.detail || "تعذر تحميل إحصائيات الخروج";
    exitEvents.value = [];
  } finally {
    exitLoading.value = false;
  }
}

function initCharts() {
  if (pieChartRef.value && !pieChartInstance) {
    pieChartInstance = echarts.init(pieChartRef.value);
  }
  if (barChartRef.value && !barChartInstance) {
    barChartInstance = echarts.init(barChartRef.value);
  }
  if (exitDurationChartRef.value && !exitDurationChartInstance) {
    exitDurationChartInstance = echarts.init(exitDurationChartRef.value);
  }
}

function updatePieChart() {
  if (!pieChartInstance) return;

  const k = kpis.value;
  const data = [
    { value: k.absent || 0, name: "غياب", itemStyle: { color: "#dc3545" } },
    { value: k.late || 0, name: "تأخر", itemStyle: { color: "#ffc107" } },
    { value: k.excused || 0, name: "إذن", itemStyle: { color: "#6c757d" } },
    { value: k.runaway || 0, name: "هروب", itemStyle: { color: "#d32f2f" } },
    { value: k.left_early || 0, name: "انصراف مبكر", itemStyle: { color: "#ff9800" } },
  ].filter((item) => item.value > 0);

  pieChartInstance.setOption({
    tooltip: {
      trigger: "item",
      formatter: "{b}: {c} ({d}%)",
    },
    legend: {
      orient: "horizontal",
      bottom: "0",
      textStyle: { fontFamily: "Cairo, sans-serif" },
    },
    series: [
      {
        type: "pie",
        radius: ["40%", "70%"],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 8,
          borderColor: "#fff",
          borderWidth: 2,
        },
        label: {
          show: false,
          position: "center",
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 20,
            fontWeight: "bold",
            fontFamily: "Cairo, sans-serif",
          },
        },
        labelLine: {
          show: false,
        },
        data: data,
      },
    ],
  });
}

function updateBarChart() {
  if (!barChartInstance) return;

  const top = summary.value?.top_classes || [];
  const worst = summary.value?.worst_classes || [];

  const topNames = top.map((c) => c.class_name || `#${c.class_id}`);
  const topValues = top.map((c) => c.present_pct);
  const worstNames = worst.map((c) => c.class_name || `#${c.class_id}`);
  const worstValues = worst.map((c) => c.present_pct);

  barChartInstance.setOption({
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
    },
    legend: {
      data: ["أفضل الصفوف", "بحاجة متابعة"],
      textStyle: { fontFamily: "Cairo, sans-serif" },
    },
    grid: {
      left: "3%",
      right: "4%",
      bottom: "3%",
      containLabel: true,
    },
    xAxis: {
      type: "value",
      max: 100,
      axisLabel: {
        formatter: "{value}%",
      },
    },
    yAxis: {
      type: "category",
      data: [...topNames, ...worstNames],
      axisLabel: {
        fontFamily: "Cairo, sans-serif",
      },
    },
    series: [
      {
        name: "أفضل الصفوف",
        type: "bar",
        data: topValues.concat(Array(worstNames.length).fill(null)),
        itemStyle: { color: "#10b981", borderRadius: [0, 4, 4, 0] },
      },
      {
        name: "بحاجة متابعة",
        type: "bar",
        data: Array(topNames.length).fill(null).concat(worstValues),
        itemStyle: { color: "#ef4444", borderRadius: [0, 4, 4, 0] },
      },
    ],
  });
}

function updateExitDurationChart() {
  if (!exitDurationChartInstance) return;
  const rows = [...topStudentsByExits.value]
    .sort((a, b) => b.totalMinutes - a.totalMinutes)
    .slice(0, 10);
  const names = rows.map((r) => `طالب #${r.student_id}`);
  const values = rows.map((r) => r.totalMinutes);
  exitDurationChartInstance.setOption({
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    grid: { left: "3%", right: "4%", bottom: "3%", containLabel: true },
    xAxis: { type: "value", axisLabel: { formatter: "{value} دقيقة" } },
    yAxis: { type: "category", data: names, axisLabel: { fontFamily: "Cairo, sans-serif" } },
    series: [
      {
        name: "إجمالي الوقت خارج الفصل (دقائق)",
        type: "bar",
        data: values,
        itemStyle: { color: "#8a1538", borderRadius: [0, 4, 4, 0] },
      },
    ],
  });
}

watch(kpis, () => {
  nextTick(() => {
    updatePieChart();
    updateBarChart();
  });
});

watch(exitEvents, () => {
  nextTick(() => {
    updateExitDurationChart();
  });
});

watch(dateStr, async () => {
  await loadSummary();
});

watch(mode, async () => {
  await loadSummary();
});

watch(selectedSubjectId, async () => {
  if (mode.value === "teacher_subject") {
    await loadSummary();
  }
});

watch(selectedClassId, async () => {
  if (mode.value === "class") {
    await loadSummary();
  }
});

onMounted(async () => {
  if (!auth.profile && !auth.loading) {
    try {
      await auth.loadProfile();
    } catch {}
  }
  // Load teacher metadata (classes/subjects) if applicable
  await loadTeacherMeta();
  // Default mode for teachers: use all classes; otherwise school
  if (isTeacher.value && !isSuper.value) {
    mode.value = "teacher_all";
  } else {
    mode.value = "school";
  }
  await loadSummary();
  await nextTick();
  initCharts();
  updatePieChart();
  updateBarChart();
  updateExitDurationChart();

  window.addEventListener("resize", () => {
    pieChartInstance?.resize();
    barChartInstance?.resize();
    exitDurationChartInstance?.resize();
  });
});
</script>

<style scoped>
.page-toolbar {
  row-gap: 0.25rem;
}
.toolbar-actions {
  gap: 0.5rem;
}
.toolbar-date {
  max-width: 200px;
  min-width: 180px;
}
.toolbar-mode {
  min-width: 180px;
}
.toolbar-subject {
  min-width: 180px;
}
.toolbar-class {
  min-width: 180px;
}
.segmented {
  display: inline-flex;
  gap: 6px;
}
.segmented-btn {
  white-space: nowrap;
}

/* Ensure charts keep consistent heights within their cards */
:deep(.ds-card) {
  overflow: hidden;
}

@media (max-width: 576px) {
  .toolbar-actions {
    width: 100%;
  }
  .toolbar-date {
    flex: 1 1 160px;
    min-width: 0;
  }
}

@media print {
  /* Hide controls in print */
  .page-toolbar,
  .toolbar-actions,
  .toolbar-date,
  .segmented {
    display: none !important;
  }
  /* Simplify cards for print */
  :deep(.ds-card) {
    box-shadow: none !important;
  }
}
</style>
