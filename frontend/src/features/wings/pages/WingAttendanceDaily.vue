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
      <DatePickerDMY
        :id="'wing-att-daily-date'"
        :aria-label="'اختيار التاريخ'"
        wrapperClass="m-0"
        inputClass="form-control w-auto"
        v-model="dateStr"
        @change="loadAll"
      />
      <button class="btn btn-outline-secondary" type="button" @click="loadAll">
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
              <a class="btn btn-sm btn-outline-danger" :href="missingCsvHref" target="_blank" rel="noopener">تنزيل مفقودة CSV</a>
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
import { onMounted } from 'vue';
import { useWingContext } from '../../../shared/composables/useWingContext';
const { ensureLoaded, wingLabelFull } = useWingContext();
onMounted(() => { ensureLoaded(); });
import { ref, computed } from "vue";
import DatePickerDMY from "../../../components/ui/DatePickerDMY.vue";
import { Icon } from "@iconify/vue";
import { tiles } from "../../../home/icon-tiles.config";
import StatusLegend from "../../../components/ui/StatusLegend.vue";
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
} from "../../../shared/api/client";
import { useToast } from "vue-toastification";

const toast = useToast();
const today = new Date().toISOString().slice(0, 10);
const dateStr = ref<string>(today);
const loadingAll = ref(false);
const error = ref<string | null>(null);

// CSV export hrefs (direct links proxied via Vite to backend)
const apiBase = "/api/v1";
const dailyCsvHref = computed(() => `${apiBase}/wing/daily-absences/export/?date=${encodeURIComponent(dateStr.value)}`);
const enteredCsvHref = computed(() => `${apiBase}/wing/entered/export/?date=${encodeURIComponent(dateStr.value)}`);
const missingCsvHref = computed(() => `${apiBase}/wing/missing/export/?date=${encodeURIComponent(dateStr.value)}`);

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
    const [ov, daily, pend, entered, missing, exits] = await Promise.all([
      getWingOverview(paramsDate),
      getWingDailyAbsences(paramsDate),
      getWingPending(paramsDate),
      getWingEntered(paramsDate),
      getWingMissing(paramsDate),
      getOpenExitEvents({ date: dateStr.value }),
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

loadAll();
</script>

<style scoped>
.header-bar { align-items: center; }
.header-icon { font-size: 22px; }
.card h5 { font-weight: 700; }
</style>
