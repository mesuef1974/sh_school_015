<template>
  <section class="d-grid gap-3 page-grid page-grid-wide" dir="rtl">
    <WingPageHeader :icon="tileMeta.icon" :title="tileMeta.title" :color="tileMeta.color">
          <template #actions>
            <WingWingPicker id="pick-daily-wing" />
          </template>
        </WingPageHeader>

    <div class="auto-card p-2 d-flex align-items-center gap-2 flex-wrap">
      <DatePickerDMY
        :id="'wing-att-daily-date'"
        :aria-label="'اختيار التاريخ'"
        wrapperClass="m-0"
        inputClass="form-control w-auto"
        v-model="dateStr"
        @change="loadAll"
      />
      <label class="visually-hidden" for="wing-class-filter">تصفية حسب الصف</label>
      <select
        id="wing-class-filter"
        class="form-select form-select-sm w-auto ms-2"
        v-model.number="classId"
        @change="loadAll"
        :aria-label="'تصفية حسب الصف'"
      >
        <option :value="0">كل الصفوف</option>
        <option v-for="c in classes" :key="c.id" :value="c.id">{{ c.name }}</option>
      </select>
      <button class="btn btn-outline-secondary" type="button" @click="loadAll" aria-label="تحديث البيانات">
        <Icon icon="solar:refresh-bold-duotone" /> تحديث
      </button>
    </div>

    <div v-if="loadingAll" class="alert alert-info py-2">جاري التحميل ...</div>
    <div v-if="error" class="alert alert-danger">{{ error }}</div>

    <div class="row g-3">
      <!-- KPI: Today’s attendance overview -->
      <div class="col-12 col-lg-6">
        <div class="card h-100">
          <div class="card-body">
            <div class="d-flex align-items-center gap-2 mb-2">
              <Icon icon="solar:calendar-bold-duotone" class="text-primary" width="22" height="22" />
              <h5 class="m-0 card-title-maroon">ملخص الحضور اليومي</h5>
              <span class="small text-muted ms-auto">نسبة الحضور مبنية على السجلات المدخلة</span>
            </div>
            <div v-if="overview">
              <div class="d-flex flex-wrap gap-2 mb-2">
                <span class="badge text-bg-success">حضور % {{ overview.kpis.present_pct?.toFixed?.(1) ?? overview.kpis.present_pct }}</span>
                <span class="badge text-bg-secondary">إجمالي: {{ overview.kpis.total }}</span>
                <span class="badge text-bg-primary">حاضر: {{ overview.kpis.present }}</span>
                <span class="badge text-bg-warning text-dark">متأخر: {{ overview.kpis.late }}</span>
                <span class="badge text-bg-info text-dark">إذن خروج: {{ overview.kpis.excused }}</span>
                <span class="badge text-bg-danger">غائب: {{ overview.kpis.absent }}</span>
                <span class="badge text-bg-dark">هروب: {{ overview.kpis.runaway }}</span>
              </div>
              <div class="small text-muted">تاريخ: {{ formatDateDMY(dateStr) }}</div>
            </div>
            <div v-else class="text-muted">لا تتوفر بيانات</div>
          </div>
        </div>
      </div>

      <!-- KPI: Daily general absence classification O/X -->
      <div class="col-12 col-lg-6">
        <div class="card h-100">
          <div class="card-body">
            <div class="d-flex align-items-center gap-2 mb-2">
              <Icon icon="solar:alarm-bold-duotone" class="text-danger" width="22" height="22" />
              <h5 class="m-0 card-title-maroon">الحالة العامة اليومية (حسب الحصتين الأولى والثانية)</h5>
            </div>
            <div class="d-flex flex-wrap gap-2 mb-2">
              <span class="att-chip day-state unexcused">بدون عذر: {{ dailyCounts.unexcused }}</span>
              <span class="att-chip day-state excused">بعذر: {{ dailyCounts.excused }}</span>
              <span class="att-chip day-state none">غير محسوب: {{ dailyCounts.none }}</span>
            </div>
            <StatusLegend class="mb-2" />
            <div class="d-flex align-items-center gap-2 flex-wrap">
              <router-link class="btn btn-sm btn-outline-primary" :to="{ name: 'wing-approvals' }">
                فتح تفاصيل الطلاب
              </router-link>
              <a class="btn btn-sm btn-outline-success" :href="dailyCsvHref" target="_blank" rel="noopener">
                تنزيل CSV
              </a>
              <a class="btn btn-sm btn-outline-primary" :href="dailyWordHref" target="_blank" rel="noopener">
                تنزيل Word
              </a>
            </div>
            <div class="form-text">يُحسب اليوم كاملًا إذا كانت الحصتان 1 و2 غيابًا. العطل مستثناة.</div>
          </div>
        </div>
      </div>

      <!-- Approvals queue -->
      <div class="col-12 col-md-6 col-lg-4">
        <div class="card h-100">
          <div class="card-body">
            <div class="d-flex align-items-center gap-2 mb-2">
              <Icon icon="solar:checklist-minimalistic-bold-duotone" class="text-warning" width="22" height="22" />
              <h5 class="m-0 card-title-maroon">طلبات الاعتماد</h5>
            </div>
            <div class="display-6">{{ pendingCount }}</div>
            <div class="text-muted">سجلات بانتظار اعتماد مشرف الجناح</div>
            <router-link class="btn btn-sm btn-primary mt-2" :to="{ name: 'wing-approvals' }">انتقال إلى الاعتماد</router-link>
          </div>
        </div>
      </div>

      <!-- Entered vs Missing coverage -->
      <div class="col-12 col-md-6 col-lg-4">
        <div class="card h-100">
          <div class="card-body">
            <div class="d-flex align-items-center gap-2 mb-2">
              <Icon icon="solar:target-bold-duotone" class="text-success" width="22" height="22" />
              <h5 class="m-0">التغطية اليوم</h5>
            </div>
            <div class="d-flex align-items-center gap-3">
              <div class="text-center flex-fill">
                <div class="h3 m-0">{{ enteredCount }}</div>
                <div class="small text-muted">حصص مُدخلة</div>
              </div>
              <div class="text-center flex-fill">
                <div class="h3 m-0">{{ missingCount }}</div>
                <div class="small text-muted">حصص مفقودة</div>
              </div>
            </div>
            <div class="d-flex align-items-center gap-2 mt-2 flex-wrap">
              <router-link class="btn btn-sm btn-outline-secondary" :to="{ name: 'wing-attendance-monitor' }">
                مراقبة الحضور
              </router-link>
              <a class="btn btn-sm btn-outline-success" :href="enteredCsvHref" target="_blank" rel="noopener">تنزيل مُدخلة CSV</a>
              <a class="btn btn-sm btn-outline-primary" :href="enteredWordHref" target="_blank" rel="noopener">تنزيل مُدخلة Word</a>
              <a class="btn btn-sm btn-outline-danger" :href="missingCsvHref" target="_blank" rel="noopener">تنزيل مفقودة CSV</a>
              <a class="btn btn-sm btn-outline-primary" :href="missingWordHref" target="_blank" rel="noopener">تنزيل مفقودة Word</a>
            </div>
          </div>
        </div>
      </div>

      <!-- Open exit events -->
      <div class="col-12 col-md-6 col-lg-4">
        <div class="card h-100">
          <div class="card-body">
            <div class="d-flex align-items-center gap-2 mb-2">
              <Icon icon="solar:door-bold-duotone" class="text-info" width="22" height="22" />
              <h5 class="m-0 card-title-maroon">أذونات الخروج المفتوحة الآن</h5>
            </div>
            <div class="h4">{{ openExitEvents.length }}</div>
            <ul class="list-unstyled small m-0" v-if="openExitEvents.length">
              <li v-for="ev in openExitEvents.slice(0,5)" :key="ev.id">
                {{ ev.student_name || ('#'+ev.student_id) }} — منذ {{ prettyTime(ev.started_at) }}
              </li>
            </ul>
            <div v-else class="text-muted">لا توجد أذونات مفتوحة</div>
          </div>
        </div>
      </div>

      <!-- Alerts issued today -->
      <div class="col-12">
        <div class="card">
          <div class="card-body">
            <div class="d-flex align-items-center gap-2 mb-2">
              <Icon icon="solar:document-text-bold-duotone" class="text-danger" width="22" height="22" />
              <h5 class="m-0">تنبيهات الغياب الصادرة اليوم</h5>
              <span class="badge bg-danger-subtle text-danger ms-2">{{ alertsToday.length }}</span>
              <span class="ms-auto"></span>
              <router-link class="btn btn-sm btn-outline-primary" :to="{ name: 'wing-absences-alerts' }">
                إدارة الغيابات والتنبيهات
              </router-link>
            </div>
            <div class="table-responsive">
              <table class="table table-sm align-middle">
                <thead>
                  <tr>
                    <th>رقم</th>
                    <th>الطالب</th>
                    <th>الفترة</th>
                    <th>O/X</th>
                    <th>ملف</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="a in alertsToday.slice(0,5)" :key="a.id">
                    <td>{{ a.number }}</td>
                    <td>{{ a.student_name || ('#'+a.student) }}</td>
                    <td>من {{ formatDateDMY(a.period_start) }} إلى {{ formatDateDMY(a.period_end) }}</td>
                    <td>O {{ a.excused_days }} / X {{ a.unexcused_days }}</td>
                    <td>
                      <a class="btn btn-xs btn-outline-primary" :href="getAbsenceAlertDocxHref(a.id)" target="_blank" rel="noopener">
                        تنزيل
                      </a>
                    </td>
                  </tr>
                  <tr v-if="!alertsToday.length">
                    <td colspan="5" class="text-center text-muted">لا توجد تنبيهات اليوم</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { useWingPrefs } from "../../../shared/composables/useWingPrefs";
import { onMounted, watch } from 'vue';
import { useWingContext } from '../../../shared/composables/useWingContext';
const { ensureLoaded, wingLabelFull, selectedWingId } = useWingContext();
onMounted(async () => {
  await ensureLoaded();
  // Apply Wing Settings defaults
  if (apply_on_load.value.daily) {
    // Date init
    if (default_date_mode.value === 'today') {
      dateStr.value = today;
    } else if (default_date_mode.value === 'remember') {
      const prev = localStorage.getItem('wing_daily.last_date');
      dateStr.value = prev || today;
    }
    // Class init
    if (daily_class_filter_behavior.value === 'default_class' && default_class_id.value) {
      classId.value = default_class_id.value;
    } else if (daily_class_filter_behavior.value === 'remember') {
      const prevClass = Number(localStorage.getItem('wing_daily.last_class') || '0');
      if (prevClass) classId.value = prevClass;
    }
  }
  try {
    const params: any = {};
    if (selectedWingId?.value) params.wing_id = selectedWingId.value;
    const res = await getWingClasses(params);
    classes.value = res.items?.map((c: any) => ({ id: c.id, name: c.name || `#${c.id}` })) || [];
  } catch { classes.value = []; }
  await loadAll();
});
import { ref, computed, watch } from "vue";
import DatePickerDMY from "../../../components/ui/DatePickerDMY.vue";
import { Icon } from "@iconify/vue";
import { tiles } from "../../../home/icon-tiles.config";
import StatusLegend from "../../../components/ui/StatusLegend.vue";
import WingPageHeader from "../../../components/ui/WingPageHeader.vue";
import WingWingPicker from "../../../components/ui/WingWingPicker.vue";
import { formatDateDMY } from "../../../shared/utils/date";
const tileMeta = computed(() => tiles.find(t => t.to === "/wing/attendance/daily") || { title: "الغياب اليومي", icon: "solar:calendar-bold-duotone", color: "#1565c0" });
import {
  getWingOverview,
  getWingDailyAbsences,
  getWingPending,
  getWingEntered,
  getWingMissing,
  getOpenExitEvents,
  listAbsenceAlerts,
  getAbsenceAlertDocxHref,
  getWingClasses,
} from "../../../shared/api/client";
import { useToast } from "vue-toastification";

const toast = useToast();
const { default_date_mode, apply_on_load, daily_class_filter_behavior, default_class_id } = useWingPrefs();
const today = new Date().toISOString().slice(0, 10);
const dateStr = ref<string>(today);
const loadingAll = ref(false);
const error = ref<string | null>(null);

// Filters
const classId = ref<number>(0);
const classes = ref<{ id: number; name?: string | null }[]>([]);

// CSV export hrefs (direct links proxied via Vite to backend)
const apiBase = "/api/v1";
const dailyCsvHref = computed(() => {
  const params = new URLSearchParams({ date: dateStr.value });
  if (classId.value && classId.value > 0) params.append("class_id", String(classId.value));
  if (selectedWingId?.value) params.append("wing_id", String(selectedWingId.value));
  return `${apiBase}/wing/daily-absences/export/?${params.toString()}`;
});
const dailyWordHref = computed(() => {
  const params = new URLSearchParams({ date: dateStr.value });
  if (classId.value && classId.value > 0) params.append("class_id", String(classId.value));
  if (selectedWingId?.value) params.append("wing_id", String(selectedWingId.value));
  return `${apiBase}/wing/daily-absences/export.docx/?${params.toString()}`;
});
const enteredCsvHref = computed(() => {
  const params = new URLSearchParams({ date: dateStr.value });
  if (selectedWingId?.value) params.append("wing_id", String(selectedWingId.value));
  return `${apiBase}/wing/entered/export/?${params.toString()}`;
});
const enteredWordHref = computed(() => {
  const params = new URLSearchParams({ date: dateStr.value });
  if (selectedWingId?.value) params.append("wing_id", String(selectedWingId.value));
  return `${apiBase}/wing/entered/export.docx/?${params.toString()}`;
});
const missingCsvHref = computed(() => {
  const params = new URLSearchParams({ date: dateStr.value });
  if (selectedWingId?.value) params.append("wing_id", String(selectedWingId.value));
  return `${apiBase}/wing/missing/export/?${params.toString()}`;
});
const missingWordHref = computed(() => {
  const params = new URLSearchParams({ date: dateStr.value });
  if (selectedWingId?.value) params.append("wing_id", String(selectedWingId.value));
  return `${apiBase}/wing/missing/export.docx/?${params.toString()}`;
});

// Data buckets
const overview = ref<any | null>(null);
const dailyCounts = ref<{ excused: number; unexcused: number; none: number }>({ excused: 0, unexcused: 0, none: 0 });
const pendingCount = ref<number>(0);
const enteredCount = ref<number>(0);
const missingCount = ref<number>(0);
const openExitEvents = ref<{ id: number; student_id: number; student_name?: string | null; started_at: string; reason: string }[]>([]);
const alertsToday = ref<any[]>([]);

function prettyTime(iso: string) {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString("ar-EG", { hour: "2-digit", minute: "2-digit" });
  } catch {
    return iso;
  }
}

async function loadAll() {
  loadingAll.value = true;
  error.value = null;
  try {
    const paramsDate = { date: dateStr.value } as any;
    if (classId.value && classId.value > 0) {
      paramsDate.class_id = classId.value;
    }
    if (selectedWingId?.value) paramsDate.wing_id = selectedWingId.value;
    const [ov, daily, pend, entered, missing, exits] = await Promise.all([
      getWingOverview(paramsDate),
      getWingDailyAbsences(paramsDate),
      getWingPending(paramsDate),
      getWingEntered(paramsDate),
      getWingMissing(paramsDate),
      getOpenExitEvents(selectedWingId?.value ? { date: dateStr.value, wing_id: selectedWingId.value } : { date: dateStr.value }),
    ]);
    overview.value = ov;
    dailyCounts.value = daily?.counts || { excused: 0, unexcused: 0, none: 0 };
    pendingCount.value = pend?.count || 0;
    enteredCount.value = (entered?.count ?? entered?.items?.length) || 0;
    missingCount.value = (missing?.count ?? missing?.items?.length) || 0;
    openExitEvents.value = exits || [];

    // Alerts issued today
    try {
      const res = await listAbsenceAlerts({ from: dateStr.value, to: dateStr.value });
      const items: any[] = Array.isArray(res) ? res : Array.isArray(res.results) ? res.results : (res?.items || []);
      alertsToday.value = items || [];
    } catch {}
  } catch (e: any) {
    try { toast.error(e?.response?.data?.detail || "تعذر تحميل البيانات"); } catch {}
    error.value = e?.response?.data?.detail || e?.message || "تعذر تحميل البيانات";
  } finally {
    loadingAll.value = false;
  }
}

// refetch when wing selection changes (super admin)
watch(selectedWingId, async () => {
  try {
    const params: any = {};
    if (selectedWingId?.value) params.wing_id = selectedWingId.value;
    const res = await getWingClasses(params);
    classes.value = res.items?.map((c: any) => ({ id: c.id, name: c.name || `#${c.id}` })) || [];
  } catch { classes.value = []; }
  await loadAll();
});

// initial load happens after ensureLoaded and classes fetched
</script>

<style scoped>
.header-bar { align-items: center; }
.card h5 { font-weight: 700; }
</style>