<template>
  <section class="d-grid gap-3">
    <DsCard
      v-motion
      :initial="{ opacity: 0, y: -30 }"
      :enter="{ opacity: 1, y: 0, transition: { duration: 400 } }"
      :animate="false"
    >
      <div class="d-flex align-items-center gap-3 flex-wrap">
        <Icon icon="solar:chart-2-bold-duotone" class="text-4xl" style="color: var(--maron-primary)" />
        <div class="flex-grow-1">
          <div class="text-xl font-bold">لوحة الإحصائيات</div>
          <div class="text-muted text-sm">نسب وملخصات الحضور لليوم المحدد</div>
        </div>
        <input type="date" v-model="dateStr" class="form-control" style="max-width: 200px" @change="loadSummary" />
      </div>
    </DsCard>

    <div class="row g-3">
      <div class="col-12 col-lg-8">
        <div class="row g-3">
          <div class="col-6 col-md-4 col-lg-3">
            <KpiCard :loading="loading" title="الحضور اليوم" :value="kpis.present_pct" suffix="%" icon="bi bi-people" />
          </div>
          <div class="col-6 col-md-4 col-lg-3">
            <KpiCard :loading="loading" title="الغياب" :value="kpis.absent" icon="bi bi-person-x" variant="danger" />
          </div>
          <div class="col-6 col-md-4 col-lg-3">
            <KpiCard :loading="loading" title="التأخر" :value="kpis.late" icon="bi bi-alarm" variant="warning" />
          </div>
          <div class="col-6 col-md-4 col-lg-3">
            <KpiCard :loading="loading" title="إذن خروج" :value="kpis.excused" icon="bi bi-shield-check" variant="secondary" />
          </div>
          <div class="col-6 col-md-4 col-lg-3">
            <KpiCard :loading="loading" title="هروب" :value="kpis.runaway" icon="bi bi-person-dash" variant="danger" />
          </div>
          <div class="col-6 col-md-4 col-lg-3">
            <KpiCard :loading="loading" title="انصراف مبكر" :value="kpis.left_early" icon="bi bi-box-arrow-left" variant="warning" />
          </div>
        </div>

        <div class="row g-3 mt-2">
          <div class="col-12 col-md-6">
            <DsCard title="توزيع حالات الحضور">
              <div ref="pieChartRef" style="width: 100%; height: 300px;"></div>
            </DsCard>
          </div>
          <div class="col-12 col-md-6">
            <DsCard title="مقارنة أفضل وأسوأ الصفوف">
              <div ref="barChartRef" style="width: 100%; height: 300px;"></div>
            </DsCard>
          </div>
        </div>

        <div class="auto-card p-3 mt-3">
          <div class="d-flex align-items-center mb-2">
            <div class="fw-bold">صفوف اليوم المميزة</div>
            <span class="ms-auto small text-muted">{{ summary?.date }}</span>
          </div>
          <div class="row g-2">
            <div class="col-12 col-md-6">
              <div class="p-2 border rounded-3">
                <div class="fw-bold mb-1">Top</div>
                <ul class="small mb-0">
                  <li v-for="t in summary?.top_classes || []" :key="'t'+t.class_id">صف {{ t.class_name || ('#'+t.class_id) }} — {{ t.present_pct }}%</li>
                  <li v-if="(summary?.top_classes || []).length === 0" class="text-muted">لا بيانات</li>
                </ul>
              </div>
            </div>
            <div class="col-12 col-md-6">
              <div class="p-2 border rounded-3">
                <div class="fw-bold mb-1">بحاجة متابعة</div>
                <ul class="small mb-0">
                  <li v-for="w in summary?.worst_classes || []" :key="'w'+w.class_id">صف {{ w.class_name || ('#'+w.class_id) }} — {{ w.present_pct }}%</li>
                  <li v-if="(summary?.worst_classes || []).length === 0" class="text-muted">لا بيانات</li>
                </ul>
              </div>
            </div>
          </div>
          <div v-if="error" class="alert alert-danger mt-2 mb-0">{{ error }}</div>
        </div>
      </div>

      <div class="col-12 col-lg-4">
        <div class="auto-card p-3">
          <div class="fw-bold mb-2">نطاق العرض</div>
          <div class="d-grid gap-2">
            <DsButton
              :variant="scope==='teacher' ? 'primary' : 'outline'"
              icon="solar:user-id-bold-duotone"
              @click="setScope('teacher')"
              class="w-100"
            >
              صفوفي (للمعلم)
            </DsButton>
            <DsButton
              :variant="scope==='school' ? 'primary' : 'outline'"
              icon="solar:buildings-2-bold-duotone"
              @click="setScope('school')"
              class="w-100"
            >
              كل المدرسة
            </DsButton>
          </div>
          <div class="small text-muted mt-2">يتم تقييد النطاق إلى صفوف المعلم عند اختيار "صفوفي".</div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch, nextTick } from 'vue';
import { useAuthStore } from '../../app/stores/auth';
import { getAttendanceSummary, getTeacherClasses } from '../../shared/api/client';
import KpiCard from '../../widgets/KpiCard.vue';
import DsButton from '../../components/ui/DsButton.vue';
import DsCard from '../../components/ui/DsCard.vue';
import * as echarts from 'echarts/core';
import { PieChart, BarChart } from 'echarts/charts';
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent
} from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';

echarts.use([
  PieChart,
  BarChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  CanvasRenderer
]);

const auth = useAuthStore();
const isSuper = computed(() => !!auth.profile?.is_superuser);
const isTeacher = computed(() => (auth.profile?.roles || []).includes('teacher'));

const dateStr = ref(new Date().toISOString().slice(0,10));
const loading = ref(false);
const error = ref('');
const summary = ref<{ date: string; scope: string; kpis: any; top_classes: any[]; worst_classes: any[] } | null>(null);
const kpis = computed(() => summary.value?.kpis || { present_pct: null, absent: null, late: null, excused: null, runaway: null, left_early: null });
const scope = ref<'teacher'|'school'>('school');

const pieChartRef = ref<HTMLDivElement>();
const barChartRef = ref<HTMLDivElement>();
let pieChartInstance: echarts.ECharts | null = null;
let barChartInstance: echarts.ECharts | null = null;

function setScope(s: 'teacher'|'school') {
  scope.value = s;
  loadSummary();
}

async function loadSummary() {
  loading.value = true; error.value='';
  try {
    const teacher = scope.value === 'teacher' && isTeacher.value && !isSuper.value;
    if (teacher) {
      const classesRes = await getTeacherClasses();
      const classes = classesRes.classes || [];
      let total = 0, present = 0, absent = 0, late = 0, excused = 0, runaway = 0, left_early = 0;
      const perClass: { class_id: number; class_name?: string; present_pct: number }[] = [];
      for (const c of classes) {
        if (!c?.id) continue;
        const s = await getAttendanceSummary({ class_id: c.id, date: dateStr.value });
        const k = s.kpis || {} as any;
        total += Number(k.total || 0);
        present += Number(k.present || 0);
        absent += Number(k.absent || 0);
        late += Number(k.late || 0);
        excused += Number(k.excused || 0);
        runaway += Number(k.runaway || 0);
        left_early += Number(k.left_early || 0);
        const pct = typeof k.present_pct === 'number' ? k.present_pct : 0;
        perClass.push({ class_id: c.id, class_name: c.name, present_pct: pct });
      }
      const present_pct = total ? Math.round((present / total) * 1000) / 10 : 0;
      const top_classes = [...perClass].sort((a,b) => b.present_pct - a.present_pct).slice(0,4);
      const worst_classes = [...perClass].sort((a,b) => a.present_pct - b.present_pct).slice(0,4);
      summary.value = { date: dateStr.value, scope: 'teacher', kpis: { present_pct, absent, late, excused, runaway, left_early }, top_classes, worst_classes } as any;
    } else {
      const res = await getAttendanceSummary({ scope: 'school', date: dateStr.value });
      summary.value = res;
    }
  } catch (e: any) {
    error.value = e?.response?.data?.detail || 'تعذر تحميل المؤشرات';
  } finally {
    loading.value = false;
  }
}

function initCharts() {
  if (pieChartRef.value && !pieChartInstance) {
    pieChartInstance = echarts.init(pieChartRef.value);
  }
  if (barChartRef.value && !barChartInstance) {
    barChartInstance = echarts.init(barChartRef.value);
  }
}

function updatePieChart() {
  if (!pieChartInstance) return;

  const k = kpis.value;
  const data = [
    { value: k.absent || 0, name: 'غياب', itemStyle: { color: '#dc3545' } },
    { value: k.late || 0, name: 'تأخر', itemStyle: { color: '#ffc107' } },
    { value: k.excused || 0, name: 'إذن', itemStyle: { color: '#6c757d' } },
    { value: k.runaway || 0, name: 'هروب', itemStyle: { color: '#d32f2f' } },
    { value: k.left_early || 0, name: 'انصراف مبكر', itemStyle: { color: '#ff9800' } }
  ].filter(item => item.value > 0);

  pieChartInstance.setOption({
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)'
    },
    legend: {
      orient: 'horizontal',
      bottom: '0',
      textStyle: { fontFamily: 'Cairo, sans-serif' }
    },
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 8,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: false,
          position: 'center'
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 20,
            fontWeight: 'bold',
            fontFamily: 'Cairo, sans-serif'
          }
        },
        labelLine: {
          show: false
        },
        data: data
      }
    ]
  });
}

function updateBarChart() {
  if (!barChartInstance) return;

  const top = summary.value?.top_classes || [];
  const worst = summary.value?.worst_classes || [];

  const topNames = top.map(c => c.class_name || `#${c.class_id}`);
  const topValues = top.map(c => c.present_pct);
  const worstNames = worst.map(c => c.class_name || `#${c.class_id}`);
  const worstValues = worst.map(c => c.present_pct);

  barChartInstance.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' }
    },
    legend: {
      data: ['أفضل الصفوف', 'بحاجة متابعة'],
      textStyle: { fontFamily: 'Cairo, sans-serif' }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'value',
      max: 100,
      axisLabel: {
        formatter: '{value}%'
      }
    },
    yAxis: {
      type: 'category',
      data: [...topNames, ...worstNames],
      axisLabel: {
        fontFamily: 'Cairo, sans-serif'
      }
    },
    series: [
      {
        name: 'أفضل الصفوف',
        type: 'bar',
        data: topValues.concat(Array(worstNames.length).fill(null)),
        itemStyle: { color: '#10b981', borderRadius: [0, 4, 4, 0] }
      },
      {
        name: 'بحاجة متابعة',
        type: 'bar',
        data: Array(topNames.length).fill(null).concat(worstValues),
        itemStyle: { color: '#ef4444', borderRadius: [0, 4, 4, 0] }
      }
    ]
  });
}

watch(kpis, () => {
  nextTick(() => {
    updatePieChart();
    updateBarChart();
  });
});

onMounted(async () => {
  if (!auth.profile && !auth.loading) {
    try { await auth.loadProfile(); } catch {}
  }
  await loadSummary();
  await nextTick();
  initCharts();
  updatePieChart();
  updateBarChart();

  window.addEventListener('resize', () => {
    pieChartInstance?.resize();
    barChartInstance?.resize();
  });
});
</script>

<style scoped>
</style>