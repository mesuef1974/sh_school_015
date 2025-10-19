<template>
  <section class="d-grid gap-3">
    <header class="auto-card p-3 d-flex align-items-center gap-3">
      <Icon name="fa6-solid:chart-simple" style="font-size:28px;color:#b23a48"/>
      <div>
        <div class="fw-bold">لوحة الإحصائيات</div>
        <div class="text-muted small">نسب وملخصات الحضور لليوم المحدد</div>
      </div>
      <span class="ms-auto"></span>
      <input type="date" v-model="dateStr" class="form-control" style="max-width: 180px" @change="loadSummary" />
    </header>

    <div class="row g-3">
      <div class="col-12 col-lg-8">
        <div class="row g-3">
          <div class="col-6 col-md-3">
            <KpiCard :loading="loading" title="الحضور اليوم" :value="kpis.present_pct" suffix="%" icon="bi bi-people" />
          </div>
          <div class="col-6 col-md-3">
            <KpiCard :loading="loading" title="الغياب" :value="kpis.absent" icon="bi bi-person-x" variant="danger" />
          </div>
          <div class="col-6 col-md-3">
            <KpiCard :loading="loading" title="التأخر" :value="kpis.late" icon="bi bi-alarm" variant="warning" />
          </div>
          <div class="col-6 col-md-3">
            <KpiCard :loading="loading" title="إذن خروج" :value="kpis.excused" icon="bi bi-shield-check" variant="secondary" />
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
            <button class="btn" :class="scope==='teacher' ? 'btn-maron' : 'btn-outline-secondary'" @click="setScope('teacher')">صفوفي (للمعلم)</button>
            <button class="btn" :class="scope==='school' ? 'btn-maron' : 'btn-outline-secondary'" @click="setScope('school')">كل المدرسة</button>
          </div>
          <div class="small text-muted mt-2">يتم تقييد النطاق إلى صفوف المعلم عند اختيار "صفوفي".</div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useAuthStore } from '../../app/stores/auth';
import { getAttendanceSummary, getTeacherClasses } from '../../shared/api/client';
import KpiCard from '../../widgets/KpiCard.vue';

const auth = useAuthStore();
const isSuper = computed(() => !!auth.profile?.is_superuser);
const isTeacher = computed(() => (auth.profile?.roles || []).includes('teacher'));

const dateStr = ref(new Date().toISOString().slice(0,10));
const loading = ref(false);
const error = ref('');
const summary = ref<{ date: string; scope: string; kpis: any; top_classes: any[]; worst_classes: any[] } | null>(null);
const kpis = computed(() => summary.value?.kpis || { present_pct: null, absent: null, late: null, excused: null });
const scope = ref<'teacher'|'school'>('school');

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
      let total = 0, present = 0, absent = 0, late = 0, excused = 0;
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
        const pct = typeof k.present_pct === 'number' ? k.present_pct : 0;
        perClass.push({ class_id: c.id, class_name: c.name, present_pct: pct });
      }
      const present_pct = total ? Math.round((present / total) * 1000) / 10 : 0;
      const top_classes = [...perClass].sort((a,b) => b.present_pct - a.present_pct).slice(0,4);
      const worst_classes = [...perClass].sort((a,b) => a.present_pct - b.present_pct).slice(0,4);
      summary.value = { date: dateStr.value, scope: 'teacher', kpis: { present_pct, absent, late, excused }, top_classes, worst_classes } as any;
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

onMounted(async () => {
  if (!auth.profile && !auth.loading) {
    try { await auth.loadProfile(); } catch {}
  }
  await loadSummary();
});
</script>

<style scoped>
</style>