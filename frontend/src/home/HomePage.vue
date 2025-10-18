<template>
  <section class="d-grid gap-3">
    <header class="auto-card p-3 d-flex align-items-center gap-3">
      <img :src="logoSrc" alt="" style="height:54px" />
      <div>
        <div class="fw-bold">مرحبًا، {{ name }}</div>
        <div class="text-muted small">لوحتك الشخصية — مؤشرات اليوم وروابط سريعة حسب الدور</div>
      </div>
      <span class="ms-auto"></span>
      <div class="d-flex gap-2">
        <RouterLink v-if="isTeacher || isSuper" class="btn btn-sm btn-maron" to="/attendance/teacher">غياب اليوم</RouterLink>
        <RouterLink v-if="isTeacher || isSuper" class="btn btn-sm btn-maron-outline" to="/attendance/teacher/history">سجل الغياب</RouterLink>
        <RouterLink v-if="(hasRole('wing_supervisor') && !isTeacher) || isSuper" class="btn btn-sm btn-maron-outline" to="/wing/dashboard">لوحة الجناح</RouterLink>
      </div>
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
            <KpiCard :loading="loading" title="المعذور" :value="kpis.excused" icon="bi bi-shield-check" variant="secondary" />
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
                  <li v-for="t in summary?.top_classes || []" :key="'t'+t.class_id">صف #{{ t.class_id }} — {{ t.present_pct }}%</li>
                  <li v-if="(summary?.top_classes || []).length === 0" class="text-muted">لا بيانات</li>
                </ul>
              </div>
            </div>
            <div class="col-12 col-md-6">
              <div class="p-2 border rounded-3">
                <div class="fw-bold mb-1">بحاجة متابعة</div>
                <ul class="small mb-0">
                  <li v-for="w in summary?.worst_classes || []" :key="'w'+w.class_id">صف #{{ w.class_id }} — {{ w.present_pct }}%</li>
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
          <div class="fw-bold mb-2">روابط سريعة</div>
          <ul class="mb-0 small">
            <li v-if="isSuper"><a :href="backendUrl('/admin/')" target="_blank" rel="noopener noreferrer">لوحة Django Admin</a></li>
            <li><a :href="backendUrl('/docs/')" target="_blank" rel="noopener noreferrer">مستندات المشروع</a></li>
            <li><a :href="backendUrl('/django-rq/')" target="_blank" rel="noopener noreferrer">قائمة المهام الخلفية (RQ)</a></li>
            <li><a :href="backendUrl('/healthz')" target="_blank" rel="noopener noreferrer">فحص الصحة (healthz)</a></li>
          </ul>
        </div>
      </div>
    </div>
  </section>
</template>
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useAuthStore } from '../app/stores/auth';
import { getAttendanceSummary } from '../shared/api/client';
import KpiCard from '../widgets/KpiCard.vue';
import { backendUrl } from '../shared/config';

const auth = useAuthStore();
const name = computed(() => auth.profile?.full_name || auth.profile?.username || '');
const roles = computed(() => auth.profile?.roles || []);
const hasRole = (r: string) => roles.value.includes(r);
const isSuper = computed(() => !!auth.profile?.is_superuser);
const isTeacher = computed(() => hasRole('teacher'));
const logoSrc = '/assets/img/logo.png';

const today = new Date().toISOString().slice(0,10);
const loading = ref(false);
const error = ref('');
const summary = ref<{ date: string; scope: string; kpis: any; top_classes: any[]; worst_classes: any[] } | null>(null);
const kpis = computed(() => summary.value?.kpis || { present_pct: null, absent: null, late: null, excused: null });

async function loadSummary() {
  loading.value = true; error.value='';
  try {
    const res = await getAttendanceSummary({ scope: 'school', date: today });
    summary.value = res;
  } catch (e: any) {
    error.value = e?.response?.data?.detail || 'تعذر تحميل المؤشرات';
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  if (!auth.profile && !auth.loading) {
    try { await auth.loadProfile(); } catch { /* ignore */ }
  }
  await loadSummary();
});
</script>
<style scoped>
</style>