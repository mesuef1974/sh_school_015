<template>
  <section class="d-grid gap-3 page-grid page-grid-wide" dir="rtl">
    <WingPageHeader :icon="tileMeta.icon" :title="tileMeta.title" :color="tileMeta.color">
          <template #actions>
            <WingWingPicker id="pick-alerts-wing" />
          </template>
        </WingPageHeader>

    <div v-if="!canAct" class="alert alert-warning" role="alert">لا تملك صلاحية مشرف جناح لهذه الصفحة.</div>

    <div class="visually-hidden" aria-live="polite">{{ liveMsg }}</div>

    <!-- Print-only context header for paper output -->
    <PrintPageHeader
      :title="`تنبيهات الغياب — جناح ${selectedWingId || '-'}`"
      :meta-lines="[
        `الطالب: ${selectedStudentLabel || 'غير محدد'}`,
        `الفترة: ${form.from} → ${form.to}`
      ]"
    />

    <div class="card mb-3 no-print">
      <div class="card-body">
        <div class="d-flex align-items-center gap-2 mb-2">
          <Icon :icon="'mdi:bell-alert'" />
          <h5 class="m-0 card-title-maroon">حساب O/X وإصدار تنبيه الغياب</h5>
        </div>
        <div class="row g-3 align-items-end">
          <div class="col-sm-4">
            <label class="form-label">الطالب</label>
            <div class="input-group">
              <input
                v-model.trim="studentQuery"
                @input="onStudentQuery"
                type="search"
                class="form-control"
                placeholder="ابحث بالاسم أو الرقم الشخصي"
                list="wing-students"
              />
              <button class="btn btn-outline-secondary" type="button" @click="loadStudents" :disabled="busy">
                <Icon :icon="'mdi:magnify'" />
              </button>
            </div>
            <datalist id="wing-students">
              <option
                v-for="s in students"
                :key="s.id"
                :value="displayStudentOption(s)"
              ></option>
            </datalist>
            <small v-if="selectedStudentLabel" class="text-muted">المحدد: {{ selectedStudentLabel }}</small>
          </div>
          <div class="col-sm-3">
            <label class="form-label" for="fromDate">من تاريخ</label>
            <DatePickerDMY
              :id="'fromDate'"
              v-model="form.from"
              inputClass="form-control"
              wrapperClass="m-0"
              :aria-label="'من تاريخ'"
              @change="autoCompute"
              :helperPrefix="'التاريخ المختار:'"
            />
          </div>
          <div class="col-sm-3">
            <label class="form-label" for="toDate">إلى تاريخ</label>
            <DatePickerDMY
              :id="'toDate'"
              v-model="form.to"
              inputClass="form-control"
              wrapperClass="m-0"
              :aria-label="'إلى تاريخ'"
              @change="autoCompute"
              :helperPrefix="'التاريخ المختار:'"
            />
          </div>
          <div class="col-sm-2 d-flex gap-2">
            <button class="btn btn-primary flex-fill" :disabled="busy || !canCompute || !canAct" @click="onCompute">
              <Icon :icon="'mdi:calculator'" class="me-1" /> احسب
            </button>
            <button class="btn btn-success flex-fill" :disabled="busy || !canIssue || !canAct" @click="onIssue">
              <Icon :icon="'mdi:file-document'" class="me-1" /> إصدار تنبيه
            </button>
          </div>
        </div>
        <div v-if="error" class="alert alert-danger mt-3">{{ error }}</div>
        <div v-if="result" class="mt-3">
          <div class="d-flex align-items-center gap-2 flex-wrap mb-1">
            <span class="att-chip day-state excused">بعذر: {{ result.excused_days }}</span>
            <span class="att-chip day-state unexcused">بدون عذر: {{ result.unexcused_days }}</span>
          </div>
          <StatusLegend />
          <small class="text-muted d-block mt-1">تُحسب الأيام الكاملة إذا كانت الحصتان الأولى والثانية غيابًا. تُستثنى العطل الرسمية.</small>
        </div>
      </div>
    </div>

    <div v-if="priorAlerts.length" class="card mb-3">
      <div class="card-body">
        <div class="d-flex align-items-center gap-2 mb-2">
          <Icon :icon="'mdi:bell-alert'" />
          <h5 class="m-0 card-title-maroon">تنبيهات سابقة للطالب</h5>
        </div>
        <div class="table-responsive">
          <table class="table table-sm align-middle print-table">
            <thead>
              <tr>
                <th>رقم</th>
                <th>العام</th>
                <th>الفترة</th>
                <th>O/X</th>
                <th>الحالة</th>
                <th>ملف</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="a in priorAlerts" :key="a.id">
                <td>{{ a.number }}</td>
                <td>{{ a.academic_year }}</td>
                <td>من {{ formatDateDMY(a.period_start) }} إلى {{ formatDateDMY(a.period_end) }}</td>
                <td>O {{ a.excused_days }} / X {{ a.unexcused_days }}</td>
                <td>{{ a.status }}</td>
                <td class="d-flex gap-1">
                  <a class="btn btn-xs btn-outline-primary" :href="getAbsenceAlertDocxHref(a.id)" target="_blank" rel="noopener" title="تنزيل Word (فوري)">
                    <Icon :icon="'mdi:download'" /> Word
                  </a>
                  <a class="btn btn-xs btn-outline-success" :href="getAbsenceAlertDocxPersistHref(a.id)" target="_blank" rel="noopener" title="توليد وحفظ نسخة في الأرشيف ثم تنزيل">
                    <Icon :icon="'mdi:content-save'" /> حفظ
                  </a>
                  <a class="btn btn-xs btn-outline-secondary" :href="getAbsenceAlertDocxLatestHref(a.id)" target="_blank" rel="noopener" title="تنزيل آخر نسخة محفوظة">
                    <Icon :icon="'mdi:history'" /> آخر محفوظ
                  </a>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div v-if="alert" class="card">
      <div class="card-body">
        <h5 class="mb-2">تم إصدار التنبيه رقم ({{ alert.number }}) للعام {{ alert.academic_year }}</h5>
        <ul class="mb-2">
          <li>الطالب: {{ alert.student_name || alert.student }}</li>
          <li>الفترة: من {{ formatDateDMY(alert.period_start) }} إلى {{ formatDateDMY(alert.period_end) }}</li>
          <li>بعذر: {{ alert.excused_days }} | بدون عذر: {{ alert.unexcused_days }}</li>
          <li>الحالة: {{ alert.status }}</li>
        </ul>
        <a class="btn btn-outline-primary" :href="docxHref" target="_blank" rel="noopener">
          <Icon :icon="'mdi:download'" class="me-1" /> تنزيل ملف Word
        </a>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import { useWingContext } from '../../../shared/composables/useWingContext';
const { ensureLoaded, hasWingRole, isSuper, selectedWingId } = useWingContext();
onMounted(() => { ensureLoaded(); });
import { ref, computed, watch } from "vue";
import { Icon } from "@iconify/vue";
import { tiles } from "../../../home/icon-tiles.config";
const tileMeta = computed(() => tiles.find(t => t.to === "/wing/absences") || { title: "الغيابات والتنبيهات", icon: "solar:bell-bing-bold-duotone", color: "#8a1538" });
import WingPageHeader from "../../../components/ui/WingPageHeader.vue";
import WingWingPicker from "../../../components/ui/WingWingPicker.vue";
import PrintPageHeader from "../../../components/ui/PrintPageHeader.vue";
// RBAC: allow actions only for wing supervisor or super admin
const canAct = computed(() => !!(hasWingRole?.value || isSuper?.value));
// Live region for accessibility
const liveMsg = ref<string>("");
import StatusLegend from "../../../components/ui/StatusLegend.vue";
import DatePickerDMY from "../../../components/ui/DatePickerDMY.vue";
import {
  computeAbsenceDays,
  createAbsenceAlert,
  getAbsenceAlertDocxHref,
  getAbsenceAlertDocxPersistHref,
  getAbsenceAlertDocxLatestHref,
  type AbsenceAlert,
  getWingStudents,
  listAbsenceAlerts,
} from "../../../shared/api/client";
import { formatDateDMY } from "../../../shared/utils/date";

const today = new Date().toISOString().slice(0, 10);
const form = ref<{ student: number | null; from: string; to: string }>({ student: null, from: today, to: today });

const busy = ref(false);
const error = ref<string | null>(null);
const result = ref<{ excused_days: number; unexcused_days: number } | null>(null);
const alert = ref<AbsenceAlert | null>(null);
const priorAlerts = ref<AbsenceAlert[]>([]);
const docxHref = computed(() => (alert.value ? getAbsenceAlertDocxHref(alert.value.id) : "#"));

// Student picker state
type StudentOption = { id: number; sid?: string | null; full_name?: string | null; class_id?: number | null; class_name?: string | null };
const students = ref<StudentOption[]>([]);
const studentQuery = ref("");
const selectedStudentLabel = computed(() => {
  const s = students.value.find((x) => x.id === form.value.student);
  return s ? displayStudentOption(s) : "";
});

function displayStudentOption(s: StudentOption) {
  const name = s.full_name || `#${s.id}`;
  const sid = s.sid ? ` (${s.sid})` : "";
  const cls = s.class_name ? ` – ${s.class_name}` : s.class_id ? ` – صف #${s.class_id}` : "";
  return `${name}${sid}${cls}`;
}

async function loadStudents() {
  try {
    const params: any = { q: studentQuery.value || undefined };
    if (selectedWingId?.value) params.wing_id = selectedWingId.value;
    const res = await getWingStudents(params);
    students.value = res.items || [];
    // If user typed an exact SID or name match with one result, auto-select
    if (!form.value.student && students.value.length === 1) {
      form.value.student = students.value[0].id;
    }
  } catch (e: any) {
    // swallow; show inline error only when computing/issuing
  }
}

function onStudentQuery() {
  // Try to match typed query to one of the options; if matches pattern '#ID' extract numeric
  const m = studentQuery.value.match(/#?(\d{1,9})$/);
  if (m) {
    const idNum = parseInt(m[1]);
    const found = students.value.find((s) => s.id === idNum || (s.sid ? String(s.sid) === String(idNum) : false));
    if (found) {
      form.value.student = found.id;
      return;
    }
  }
  // Otherwise clear selection until user chooses
  form.value.student = null;
}

function autoCompute() {
  if (canCompute.value) onCompute();
}

watch(
  () => form.value.student,
  async (nv) => {
    result.value = null;
    alert.value = null;
    error.value = null;
    priorAlerts.value = [];
    if (nv) {
      try {
        const res = await listAbsenceAlerts({ student: nv });
        // DRF list returns {results, count} or array depending on pagination settings; normalize
        const items: AbsenceAlert[] = Array.isArray(res) ? res : Array.isArray(res.results) ? res.results : res as any;
        priorAlerts.value = (items || []).slice(0, 10);
      } catch {}
    }
  }
);

const isRangeValid = computed(() => !form.value.from || !form.value.to || form.value.from <= form.value.to);
const canCompute = computed(() => !!form.value.student && !!form.value.from && !!form.value.to && isRangeValid.value);
const canIssue = computed(() => canCompute.value && !!result.value);

async function onCompute() {
  if (!canCompute.value) {
    if (!isRangeValid.value) error.value = 'نطاق التاريخ غير صالح: تاريخ البداية أكبر من النهاية';
    return;
  }
  busy.value = true;
  error.value = null;
  result.value = null;
  try {
    const res = await computeAbsenceDays({
      student: form.value.student as number,
      from: form.value.from,
      to: form.value.to,
    });
    result.value = { excused_days: res.excused_days, unexcused_days: res.unexcused_days };
    liveMsg.value = `نتيجة الحساب — بعذر: ${res.excused_days}, بدون عذر: ${res.unexcused_days}`;
  } catch (e: any) {
    error.value = e?.response?.data?.detail || e?.message || "حدث خطأ أثناء الحساب";
    liveMsg.value = `خطأ: ${error.value}`;
  } finally {
    busy.value = false;
  }
}

async function onIssue() {
  if (!canIssue.value) return;
  busy.value = true;
  error.value = null;
  alert.value = null;
  try {
    const created = await createAbsenceAlert({
      student: form.value.student as number,
      period_start: form.value.from,
      period_end: form.value.to,
    });
    alert.value = created;
    // Announce and update prior alerts list immediately
    liveMsg.value = `تم إصدار التنبيه رقم ${created.number} بنجاح`;
    // Prepend newly created alert, avoid duplicates, keep up to 10
    priorAlerts.value = [created, ...priorAlerts.value.filter((a) => a.id !== created.id)].slice(0, 10);
    // Best-effort refresh from server to sync any computed fields/status
    try {
      const res = await listAbsenceAlerts({ student: created.student });
      const items: AbsenceAlert[] = Array.isArray(res)
        ? res
        : Array.isArray((res as any).results)
        ? (res as any).results
        : (res as any);
      if (Array.isArray(items)) priorAlerts.value = items.slice(0, 10);
    } catch {}
  } catch (e: any) {
    error.value = e?.response?.data?.detail || e?.message || "تعذر إصدار التنبيه";
    liveMsg.value = `خطأ: ${error.value}`;
  } finally {
    busy.value = false;
  }
}

// Initial load: fetch some students for convenience
loadStudents();
</script>

<style scoped>
.header-icon { font-size: 22px; }
</style>