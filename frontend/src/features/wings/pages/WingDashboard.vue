<template>
  <section>
    <div class="table-hero my-2 d-flex align-items-center gap-2">
      <img :src="expHead" alt="" style="height:40px" />
      <Icon icon="solar:shield-star-bold-duotone" class="text-3xl" style="color: var(--maron-primary)" />
      <div>
        <div class="title">لوحة مشرف الجناح</div>
        <div class="muted">نظرة عامة على الحضور والانضباط لصفوف الجناح</div>
      </div>
      <span class="ms-auto"></span>
      <button class="btn btn-light me-2" @click="loadData"><Icon icon="solar:refresh-bold-duotone" class="me-1" />تحديث</button>
      <a class="btn btn-outline-secondary" :href="backendUrl('/wing/dashboard/')" target="_blank" rel="noopener noreferrer">
        <Icon icon="solar:box-minimalistic-open-bold-duotone" class="me-1" /> فتح اللوحة القديمة
      </a>
    </div>

    <div v-if="loading" class="alert alert-light border d-flex align-items-center gap-2">
      <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
      <span>جاري تحميل مؤشرات الجناح...</span>
    </div>
    <div v-else-if="error" class="alert alert-danger">حدث خطأ أثناء تحميل البيانات: {{ error }}</div>

    <!-- شبكة اختصارات سريعة حتى لا تبدو الصفحة فارغة -->
    <div class="row g-2 mb-3">
      <div class="col-6 col-md-3" v-for="s in shortcuts" :key="s.key">
        <a class="card p-3 text-center text-decoration-none h-100" :href="s.href">
          <Icon :icon="s.icon" class="text-2xl mb-2" />
          <div class="small fw-bold">{{ s.label }}</div>
        </a>
      </div>
    </div>

    <!-- بانر تشخيصي يظهر إن لم يكن للمستخدم أي أجنحة مُعيّنة -->
    <div v-if="!loading && !error && meInfo && meInfo.wings && (!meInfo.wings.ids || meInfo.wings.ids.length === 0)" class="alert alert-info d-flex align-items-center gap-2">
      <Icon icon="solar:info-circle-bold-duotone" />
      <div>
        لا توجد أجنحة معيّنة لحسابك حاليًا. تأكد من تعيينك كمشرف لجناح واحد على الأقل في قاعدة البيانات (Wing.supervisor).
        <div class="small text-muted">الأدوار: {{ meInfo.roles?.join(', ') || '—' }}</div>
      </div>
    </div>

    <div v-if="!loading && !error && kpis.total === 0" class="alert alert-warning d-flex align-items-center gap-2">
      <Icon icon="solar:info-circle-bold-duotone" />
      <div>
        لا توجد بيانات حضور لهذا اليوم ضمن جناحك. إن لم تُعيَّن لك أجنحة بعد، راسل الإدارة لتعيينك كمشرف لجناحك.
      </div>
    </div>

    <div v-else class="row g-3">
      <div class="col-12 col-md-4">
        <div class="card p-3 text-center">
          <Icon icon="solar:chart-2-bold-duotone" class="text-3xl mb-2" style="color: var(--color-success)" />
          <div class="fw-bold">نسبة الحضور اليوم</div>
          <div class="display-6" :style="{ color: 'var(--color-success)' }">{{ kpis.present_pct?.toFixed(1) ?? '--' }}%</div>
          <div class="small text-muted">الإجمالي: {{ kpis.total }} | حاضر: {{ kpis.present }}</div>
        </div>
      </div>
      <div class="col-12 col-md-4">
        <div class="card p-3 text-center">
          <Icon icon="solar:user-cross-bold-duotone" class="text-3xl mb-2" style="color: var(--color-danger)" />
          <div class="fw-bold">غياب وتأخر اليوم</div>
          <div class="display-6" :style="{ color: 'var(--color-danger)' }">{{ kpis.absent + kpis.late }}</div>
          <div class="small text-muted">غائب: {{ kpis.absent }} | متأخر: {{ kpis.late }}</div>
        </div>
      </div>
      <div class="col-12 col-md-4">
        <div class="card p-3 text-center">
          <Icon icon="solar:logout-3-bold-duotone" class="text-3xl mb-2" style="color: var(--maron-accent)" />
          <div class="fw-bold">إذونات خروج (مفتوحة)</div>
          <div class="display-6" :style="{ color: 'var(--maron-accent)' }">{{ kpis.exit_events_open }}</div>
          <div class="small text-muted">الإجمالي: {{ kpis.exit_events_total }}</div>
        </div>
      </div>

      <div class="col-12">
        <div class="card p-0 overflow-hidden">
          <div class="p-3 d-flex align-items-center gap-2 border-bottom">
            <Icon icon="solar:warning-bold-duotone" style="color: var(--color-warning)" />
            <div class="fw-bold">حصص اليوم بلا إدخال</div>
            <span class="badge text-bg-secondary">{{ missing.count }}</span>
            <span class="ms-auto"></span>
          </div>
          <div v-if="missing.count === 0" class="p-3 text-muted">لا توجد حصص بلا إدخال اليوم في جناحك.</div>
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
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, idx) in missing.items" :key="idx">
                  <td>{{ row.class_name || ('#' + row.class_id) }}</td>
                  <td>حصة {{ row.period_number }}</td>
                  <td>{{ row.subject_name || ('#' + row.subject_id) }}</td>
                  <td>{{ row.teacher_name || ('#' + row.teacher_id) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
<script setup lang="ts">
import { onMounted, ref, computed } from 'vue';
import { backendUrl } from '../../../shared/config';

const expHead = '/assets/img/school_name.png';

const kpis = ref<any>({ present_pct: 0, present: 0, absent: 0, late: 0, excused: 0, runaway: 0, total: 0, exit_events_total: 0, exit_events_open: 0 });
const missing = ref<{ count: number; items: any[] }>({ count: 0, items: [] });
const loading = ref(true);
const error = ref<string | null>(null);

const meInfo = ref<any | null>(null);

const shortcuts = computed(() => [
  { key: 'attendance_today', label: 'غياب اليوم', icon: 'solar:calendar-bold-duotone', href: '#/attendance/wing/monitor' },
  { key: 'missing_entries', label: 'حصص بلا إدخال', icon: 'solar:warning-bold-duotone', href: '#/attendance/wing/monitor' },
  { key: 'discipline', label: 'الانضباط', icon: 'solar:shield-plus-bold-duotone', href: '#/supervisor/discipline' },
  { key: 'reports', label: 'تقارير الجناح', icon: 'solar:chart-2-bold-duotone', href: '#/supervisor/reports' },
]);

async function loadData() {
  loading.value = true; error.value = null;
  try {
    const qs = new URLSearchParams({ date: new Date().toISOString().slice(0,10) }).toString();
    const [meRes, ovRes, msRes] = await Promise.all([
      fetch(backendUrl(`/api/wing/me`), { credentials: 'include' }),
      fetch(backendUrl(`/api/wing/overview?${qs}`), { credentials: 'include' }),
      fetch(backendUrl(`/api/wing/missing?${qs}`), { credentials: 'include' }),
    ]);
    if (meRes.ok) { meInfo.value = await meRes.json(); }
    if (!ovRes.ok) throw new Error(`overview ${ovRes.status}`);
    if (!msRes.ok) throw new Error(`missing ${msRes.status}`);
    const ov = await ovRes.json();
    const ms = await msRes.json();
    kpis.value = ov?.kpis || kpis.value;
    missing.value = { count: ms?.count || (ms?.items?.length || 0), items: ms?.items || [] };
  } catch (e: any) {
    error.value = e?.message || String(e);
  } finally {
    loading.value = false;
  }
}

onMounted(loadData);
</script>
<style scoped>
.card { box-shadow: 0 6px 24px rgba(0,0,0,.06); border-radius: .75rem; }
.table-responsive { max-height: 420px; }
</style>