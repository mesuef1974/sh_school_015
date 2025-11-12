<template>
  <section class="d-grid gap-3 page-grid page-grid-wide">
    <!-- شريط عنوان موحّد كما في صفحات مشرف الجناح -->
    <WingPageHeader icon="solar:clipboard-check-bold-duotone" title="تسجيل الغياب" :subtitle="'اختر الصف والتاريخ (اختياري: حصة اليوم)'" />

    <div
      v-motion
      :initial="{ opacity: 0, x: -50 }"
      :enter="{ opacity: 1, x: 0, transition: { duration: 400, delay: 100 } }"
      class="auto-card p-3 mb-3"
    >
      <form @submit.prevent="loadData" class="attendance-form">
        <div class="form-toolbar d-flex align-items-end gap-2 flex-nowrap">
          <!-- Filters: Class, Date, Today's Period -->
          <div class="form-field">
            <label class="form-label">
              <Icon icon="solar:users-group-two-rounded-bold-duotone" width="18" />
              الصف
            </label>
            <select v-model.number="classId" required class="form-select" data-testid="filter-class">
              <option :value="null" disabled>اختر الصف</option>
              <option v-for="c in classes" :key="c.id" :value="c.id">
                {{ c.name || "صف #" + c.id }}
              </option>
            </select>
          </div>

          <div class="form-field">
            <label class="form-label" for="teachDate">
              <Icon icon="solar:calendar-bold-duotone" width="18" />
              التاريخ
            </label>
            <DatePickerDMY :id="'teachDate'" v-model="dateStr" inputClass="form-control" wrapperClass="m-0" :aria-label="'اختيار التاريخ'" @change="onDateChange" :helperPrefix="'التاريخ المختار:'" />
          </div>

          <div class="form-field form-field-wide">
            <label class="form-label">
              <Icon icon="solar:clock-circle-bold-duotone" width="18" />
              حصة اليوم
            </label>
            <select v-model.number="periodNo" class="form-select" @change="onPickPeriod">
              <option :value="null">— لا شيء —</option>
              <option v-for="p in todayPeriods" :key="p.period_number" :value="p.period_number">
                حصة {{ p.period_number }} — {{ p.subject_name || "مادة" }} —
                {{ p.classroom_name || "صف #" + p.classroom_id }}
              </option>
            </select>
          </div>

          <DsButton
            type="submit"
            variant="primary"
            icon="solar:refresh-bold-duotone"
            class="btn-load"
            data-testid="load-attendance"
          >
            تحميل
          </DsButton>

          <!-- Spacer pushes action buttons to the far edge on wide screens -->
          <span class="ms-auto d-none d-sm-inline"></span>

          <!-- Action Buttons: Single-line cluster -->
          <DsButton
            type="button"
            variant="success"
            icon="solar:check-circle-bold-duotone"
            data-testid="set-all-present"
            :disabled="!students.length"
            @click="setAll('present')"
          >
            <span class="btn-text">تعيين الجميع حاضر</span>
            <span class="btn-text-short">حاضر</span>
          </DsButton>
          <DsButton
            type="button"
            variant="danger"
            icon="solar:close-circle-bold-duotone"
            :disabled="!students.length"
            @click="setAll('absent')"
          >
            <span class="btn-text">تعيين الجميع غائب</span>
            <span class="btn-text-short">غائب</span>
          </DsButton>
          <DsButton
            type="button"
            variant="primary"
            icon="solar:diskette-bold-duotone"
            data-testid="save-attendance"
            :disabled="saving || !students.length"
            :loading="saving"
            @click="save"
          >
            <span class="btn-text">حفظ الحضور</span>
            <span class="btn-text-short">حفظ</span>
          </DsButton>
          <DsButton
            type="button"
            variant="warning"
            icon="solar:shield-check-bold-duotone"
            data-testid="submit-for-review"
            :disabled="!students.length || submitting"
            :loading="submitting"
            @click="submitForReview"
          >
            <span class="btn-text">إرسال للمراجعة</span>
            <span class="btn-text-short">إرسال</span>
          </DsButton>
        </div>
      </form>
    </div>

    <div v-if="loading" class="loader-line"></div>
    <div v-else>
      <!-- شبكة البطاقات و شريط الأدوات -->
      <div class="auto-card p-3">
        <div class="grid-toolbar d-flex flex-wrap gap-2 align-items-center mb-2">
                  <StatusLegend />
          <div class="position-relative">
            <input
              v-model="searchQuery"
              type="search"
              class="form-control"
              placeholder="ابحث بالاسم"
              data-testid="student-search"
            />
            <Icon icon="solar:magnifier-bold-duotone" class="search-icon" />
          </div>
          <select v-model="statusFilter" class="form-select w-auto" data-testid="status-filter">
            <option value="">كل الحالات</option>
            <option value="present">حاضر</option>
            <option value="absent">غائب</option>
            <option value="late">متأخر</option>
            <option value="excused">إذن خروج</option>
            <option value="runaway">هروب</option>
            <option value="left_early">انصراف مبكر</option>
          </select>
          <span class="ms-auto"></span>
        </div>

        <div class="student-grid" data-testid="student-grid">
          <article
            v-for="(s, idx) in filteredStudents"
            :key="s.id"
            class="student-card"
            :class="[
              'status-' + (recordMap[s.id]?.status || 'none'),
              { inactive: s.active === false },
            ]"
          >
            <header class="d-flex align-items-center gap-2">
              <div class="avatar" :title="'#' + (idx + 1)">{{ String(idx + 1) }}</div>
              <div class="flex-grow-1 min-w-0">
                <div class="name-row d-flex align-items-center gap-2 text-truncate">
                  <div
                    class="student-name text-truncate clicky"
                    :title="s.full_name"
                    @click="openStudentIncidents(s)"
                  >
                    {{ s.full_name }}
                    <span v-if="s.active === false" class="badge bg-secondary ms-1">غير فعال</span>
                  </div>
                </div>
              </div>
              <div class="quick-actions d-none d-md-flex">
                <button
                  type="button"
                  class="btn btn-sm btn-light"
                  data-testid="mark-present"
                  :disabled="s.active === false"
                  @click="s.active === false ? null : (recordMap[s.id].status = 'present')"
                  :aria-label="'تعيين حاضر ل' + s.full_name"
                >
                  <Icon icon="solar:check-circle-bold-duotone" />
                </button>
                <button
                  type="button"
                  class="btn btn-sm btn-light text-danger"
                  data-testid="mark-absent"
                  :disabled="s.active === false"
                  @click="s.active === false ? null : (recordMap[s.id].status = 'absent')"
                  :aria-label="'تعيين غائب ل' + s.full_name"
                >
                  <Icon icon="solar:close-circle-bold-duotone" />
                </button>
                <!-- أيقونة تسجيل واقعة -->
                <div
                  class="dropdown"
                  :class="{ 'show': dropdownStudentId === s.id }"
                  :data-student-id="s.id"
                  @mouseenter="cancelHideDropdown(s.id)"
                  @mouseleave="scheduleHideDropdown(s.id)"
                >
                  <button
                    type="button"
                    class="btn btn-sm btn-light text-warning ms-1"
                    :disabled="s.active === false"
                    :aria-label="'تسجيل واقعة ل' + s.full_name"
                    @click="toggleViolationsDropdown(s, idx)"
                    title="تسجيل واقعة"
                  >
                    <Icon icon="solar:shield-warning-bold-duotone" />
                  </button>
                  <div
                    class="dropdown-menu p-2"
                    :class="[ dropdownStudentId === s.id ? 'show' : '' ]"
                    @mouseenter="cancelHideDropdown(s.id)"
                    @mouseleave="scheduleHideDropdown(s.id)"
                  >
                    <div class="d-flex align-items-center gap-2 mb-2">
                      <Icon icon="solar:list-bold-duotone" />
                      <strong>اختيار مخالفة</strong>
                      <span class="ms-auto small text-muted" v-if="violationsLoading">جاري التحميل…</span>
                    </div>
                    <input v-model.trim="violationsQuery" type="search" class="form-control form-control-sm mb-2" placeholder="ابحث بالكود/التصنيف" />
                    <div v-if="violationsError" class="alert alert-danger py-1 mb-2">{{ violationsError }}</div>
                    <ul class="list-group list-group-flush" v-if="filteredViolations.length">
                      <li
                        v-for="v in filteredViolations"
                        :key="v.id"
                        class="list-group-item list-group-item-action d-flex align-items-center gap-2 py-2"
                        @click="selectViolationForStudent(s, v)"
                        style="cursor: pointer;"
                      >
                        <span class="badge rounded-pill" :style="{ backgroundColor: sevColor(v.severity) }">{{ v.code }}</span>
                        <span class="text-truncate">{{ v.category }}</span>
                      </li>
                    </ul>
                    <div v-else class="text-muted small">لا نتائج.</div>
                  </div>
                </div>
              </div>
            </header>

            <div class="mt-2">
              <div class="controls-row d-flex align-items-center gap-2 no-wrap">
                <select
                  v-model="recordMap[s.id].status"
                  class="form-select status-select"
                  :class="statusClassChip(recordMap[s.id].status)"
                  @change="onStatusChange(s)"
                  :disabled="s.active === false"
                  :title="s.active === false ? 'الطالب غير فعال — لا يمكن إجراء أي إجراء عليه' : ''"
                >
                  <option value=""></option>
                  <option value="present">حاضر</option>
                  <option value="absent">غائب</option>
                  <option value="late">متأخر</option>
                  <option value="excused">إذن خروج</option>
                  <option value="runaway">هروب</option>
                  <option value="left_early">انصراف مبكر</option>
                </select>
                <input
                  v-if="recordMap[s.id].status !== 'excused'"
                  type="text"
                  v-model="recordMap[s.id].note"
                  class="form-control flex-grow-1 min-w-0"
                  placeholder="ملاحظة (اختياري)"
                  :disabled="s.active === false"
                  :title="s.active === false ? 'الطالب غير فعال — لا يمكن إضافة ملاحظات' : ''"
                />
              </div>
            </div>

            <div v-if="recordMap[s.id].status === 'excused'" class="mt-2">
              <div class="exit-reasons d-flex flex-wrap gap-2">
                <label
                  class="btn btn-outline-secondary btn-sm m-0"
                  :class="{
                    active: recordMap[s.id].exit_reasons === 'admin',
                    disabled: s.active === false,
                  }"
                >
                  <input
                    type="radio"
                    class="visually-hidden"
                    :name="'exit-' + s.id"
                    value="admin"
                    v-model="recordMap[s.id].exit_reasons"
                    @change="onExitReasonChange(s)"
                    :disabled="s.active === false"
                  />
                  إدارة
                </label>
                <label
                  class="btn btn-outline-secondary btn-sm m-0"
                  :class="{
                    active: recordMap[s.id].exit_reasons === 'wing',
                    disabled: s.active === false,
                  }"
                >
                  <input
                    type="radio"
                    class="visually-hidden"
                    :name="'exit-' + s.id"
                    value="wing"
                    v-model="recordMap[s.id].exit_reasons"
                    @change="onExitReasonChange(s)"
                  />
                  مشرف الجناح
                </label>
                <label
                  class="btn btn-outline-secondary btn-sm m-0"
                  :class="{
                    active: recordMap[s.id].exit_reasons === 'nurse',
                    disabled: s.active === false,
                  }"
                >
                  <input
                    type="radio"
                    class="visually-hidden"
                    :name="'exit-' + s.id"
                    value="nurse"
                    v-model="recordMap[s.id].exit_reasons"
                    @change="onExitReasonChange(s)"
                  />
                  الممرض
                </label>
                <label
                  class="btn btn-outline-secondary btn-sm m-0"
                  :class="{
                    active: recordMap[s.id].exit_reasons === 'restroom',
                    disabled: s.active === false,
                  }"
                >
                  <input
                    type="radio"
                    class="visually-hidden"
                    :name="'exit-' + s.id"
                    value="restroom"
                    v-model="recordMap[s.id].exit_reasons"
                    @change="onExitReasonChange(s)"
                  />
                  دورة المياه
                </label>
              </div>
              <div class="mt-2">
                <input
                  type="text"
                  v-model="recordMap[s.id].note"
                  class="form-control"
                  placeholder="ملاحظة إذن الخروج (إلى أين؟)"
                  :disabled="s.active === false"
                  :title="s.active === false ? 'الطالب غير فعال — لا يمكن إضافة ملاحظات' : ''"
                />
              </div>
              <div class="d-flex align-items-center gap-2 mt-2 w-100 exit-controls">
                <template v-if="!exitState[s.id]?.running">
                  <DsButton
                    size="sm"
                    variant="info"
                    icon="solar:play-bold-duotone"
                    @click="startExit(s)"
                    :disabled="s.active === false"
                    :title="s.active === false ? 'الطالب غير فعال — لا يمكن بدء إذن خروج' : ''"
                    >بدء الخروج</DsButton
                  >
                  <span class="text-muted small">لن يبدأ الحساب إلا بعد الضغط على بدء</span>
                </template>
                <template v-else>
                  <DsBadge variant="info" icon="solar:clock-circle-bold-duotone">
                    خارج الفصل: <strong>{{ formatElapsed(exitState[s.id].started_at) }}</strong>
                  </DsBadge>
                  <DsButton
                    size="sm"
                    variant="success"
                    icon="solar:check-circle-bold-duotone"
                    :loading="exitState[s.id].busy"
                    @click="returnNow(s)"
                    :disabled="s.active === false"
                    :title="s.active === false ? 'الطالب غير فعال — لا يمكن إنهاء إذن الخروج' : ''"
                  >
                    عودة الآن
                  </DsButton>
                </template>
              </div>
            </div>
          </article>
        </div>
      </div>
      <div class="sticky-actions d-flex align-items-center gap-3 p-2 border-top">
        <span v-if="saveMsg" class="msg">{{ saveMsg }}</span>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { postSubmit as postAttendanceSubmit } from "../../../api/attendance";
import { onMounted, onBeforeUnmount, reactive, ref, computed } from "vue";
import {
  getAttendanceStudents,
  getAttendanceRecords,
  postAttendanceBulkSave,
  getTeacherClasses,
  getTeacherTimetableToday,
  getAttendanceSummary,
  getOpenExitEvents,
  postExitEvent,
  patchExitReturn,
} from "../../../shared/api/client";
import { createIncident as createDisciplineIncident, listViolations } from "../../discipline/api";
import { useToast } from "vue-toastification";
import { router } from "../../../app/router";
import DsButton from "../../../components/ui/DsButton.vue";
import DsBadge from "../../../components/ui/DsBadge.vue";
import WingPageHeader from "../../../components/ui/WingPageHeader.vue";
import { nextTick } from "vue";

const toast = useToast();
const today = new Date().toISOString().slice(0, 10);
const classId = ref<number | null>(null);
const dateStr = ref<string>(today);
const loading = ref(false);
const saving = ref(false);
const saveMsg = ref("");
const submitting = ref(false);

// Class/day summary KPIs
const classSummary = ref<{ kpis?: any } | null>(null);
const classKpis = computed(
  () =>
    classSummary.value?.kpis || {
      present_pct: null,
      present: 0,
      total: 0,
      absent: 0,
      late: 0,
      excused: 0,
    }
);

// Today periods for the teacher
const todayPeriods = ref<
  {
    period_number: number;
    classroom_id: number;
    classroom_name?: string;
    subject_id: number;
    subject_name?: string;
  }[]
>([]);
const periodNo = ref<number | null>(null);

interface StudentBrief {
  id: number;
  full_name?: string;
  active?: boolean;
}
interface Rec {
  student_id: number;
  status: "" | "present" | "absent" | "late" | "excused" | "runaway" | "left_early";
  note?: string | null;
  exit_reasons?: string;
}

const classes = ref<{ id: number; name?: string }[]>([]);
const students = ref<StudentBrief[]>([]);
const inactiveIds = computed(
  () => new Set(students.value.filter((s) => s.active === false).map((s) => s.id))
);
const recordMap = reactive<Record<number, Rec>>({});

const totalStudents = computed(() => students.value.length);
const presentCount = computed(
  () => Object.values(recordMap).filter((r) => r.status === "present").length
);
const absentCount = computed(
  () => Object.values(recordMap).filter((r) => r.status === "absent").length
);
const lateCount = computed(
  () => Object.values(recordMap).filter((r) => r.status === "late").length
);
const runawayCount = computed(
  () => Object.values(recordMap).filter((r) => r.status === "runaway").length
);
const excusedCount = computed(
  () => Object.values(recordMap).filter((r) => r.status === "excused").length
);

// بحث وفلترة
const searchQuery = ref("");
const statusFilter = ref(""); // '', present, absent, late, excused, runaway, left_early

function statusLabel(value?: string) {
  switch (value) {
    case "present":
      return "حاضر";
    case "absent":
      return "غائب";
    case "late":
      return "متأخر";
    case "excused":
      return "إذن خروج";
    case "runaway":
      return "هروب";
    case "left_early":
      return "انصراف مبكر";
    default:
      return "—";
  }
}

const filteredStudents = computed(() => {
  const q = searchQuery.value.trim();
  const f = statusFilter.value;
  return students.value.filter((s: any) => {
    const matchesText = !q || (s.full_name && String(s.full_name).includes(q));
    const st = recordMap[s.id]?.status || "";
    const matchesStatus = !f || st === f;
    return matchesText && matchesStatus;
  });
});

function statusClassChip(s: string) {
  return (
    {
      present: "present",
      absent: "absent",
      late: "late",
      excused: "excused",
      runaway: "runaway",
      left_early: "left_early",
    }[s] || ""
  );
}

// ------------------------------
// تسجيل واقعة من شاشة الحضور
// ------------------------------
type ViolationItem = { id: number; code: string; category: string; severity: number };
const dropdownStudentId = ref<number | null>(null);
// Side to open the menu toward: 'left' means open inward to the left (Bootstrap dropstart), 'right' means the opposite
const dropdownHideTimers = reactive<Record<number, any>>({});
const violations = ref<ViolationItem[]>([]);
const violationsLoading = ref(false);
const violationsError = ref("");
const violationsQuery = ref("");
const createdIncidentKeys = reactive(new Set<string>()); // لمنع التكرار (student|date|period|violation)

function sevColor(sev?: number) {
  const s = Number(sev || 1);
  return s >= 4 ? "#c62828" : s === 3 ? "#fb8c00" : s === 2 ? "#f9a825" : "#2e7d32";
}

const filteredViolations = computed(() => {
  const q = violationsQuery.value.trim();
  if (!q) return violations.value;
  const ql = q.toLowerCase();
  return violations.value.filter(
    (v) => v.code.toLowerCase().includes(ql) || (v.category || "").toLowerCase().includes(ql)
  );
});

async function ensureViolationsLoaded() {
  if (violations.value.length || violationsLoading.value) return;
  violationsLoading.value = true;
  violationsError.value = "";
  try {
    const data = await listViolations();
    const results = Array.isArray(data) ? data : data?.results || [];
    violations.value = results.map((r: any) => ({
      id: r.id,
      code: r.code,
      category: r.category,
      severity: Number(r.severity || 1),
    }));
  } catch (e: any) {
    violationsError.value = e?.message || "تعذّر تحميل قائمة المخالفات";
  } finally {
    violationsLoading.value = false;
  }
}

function toggleViolationsDropdown(s: any) {
  if (s.active === false) return;
  dropdownStudentId.value = dropdownStudentId.value === s.id ? null : s.id;
  void ensureViolationsLoaded();
}

function scheduleHideDropdown(studentId: number) {
  try { clearTimeout(dropdownHideTimers[studentId]); } catch {}
  dropdownHideTimers[studentId] = setTimeout(() => {
    if (dropdownStudentId.value === studentId) dropdownStudentId.value = null;
  }, 2000);
}

// لم نعد نستخدم تموضع مخصص — نترك Bootstrap/CSS الافتراضي

function cancelHideDropdown(studentId: number) {
  try { clearTimeout(dropdownHideTimers[studentId]); } catch {}
}

function currentPeriodMeta() {
  if (!periodNo.value) return null as null | {
    period_number: number; classroom_id: number; classroom_name?: string; subject_id: number; subject_name?: string;
  };
  return (
    todayPeriods.value.find((pp) => pp.period_number === periodNo.value) || null
  );
}

function buildIncidentNarrative(s: any, v: ViolationItem) {
  const p = currentPeriodMeta();
  const parts: string[] = [];
  if (p?.classroom_name || p?.classroom_id) parts.push(`الصف: ${p?.classroom_name || `#${p?.classroom_id}`}`);
  if (p?.subject_name || p?.subject_id) parts.push(`المادة: ${p?.subject_name || `#${p?.subject_id}`}`);
  if (p?.period_number) parts.push(`الحصة: ${p?.period_number}`);
  parts.push(`المصدر: شاشة تسجيل الحضور`);
  const note = (recordMap[s.id]?.note || "").toString().trim();
  if (note) parts.push(`ملاحظة: ${note}`);
  return `${v.code} — ${v.category} \n${parts.join(" — ")}`;
}

function makeIncidentKey(studentId: number, violationId: number) {
  const p = currentPeriodMeta();
  const pid = p?.period_number || 0;
  return `${studentId}|${dateStr.value}|${pid}|${violationId}`;
}

async function createIncidentFor(studentId: number, violation: ViolationItem, sObj?: any) {
  const key = makeIncidentKey(studentId, violation.id);
  if (createdIncidentKeys.has(key)) return; // منع تكرار الإنشاء على نفس الحصة/اليوم/الطالب/المخالفة
  try {
    const occurredAt = new Date();
    // إن غيّر المعلم التاريخ يدويًا، استخدمه مع وقت الآن
    try {
      const [y, m, d] = (dateStr.value || "").split("-");
      if (y && m && d) {
        occurredAt.setFullYear(Number(y));
        occurredAt.setMonth(Number(m) - 1);
        occurredAt.setDate(Number(d));
      }
    } catch {}
    const payload: any = {
      student: studentId,
      violation: violation.id,
      occurred_at: occurredAt.toISOString(),
      narrative: buildIncidentNarrative(sObj || { id: studentId }, violation),
    };
    await createDisciplineIncident(payload);
    createdIncidentKeys.add(key);
    try { toast.success("تم تسجيل الواقعة بنجاح", { autoClose: 1200 }); } catch {}
    // فتح صفحة وقائع الطالب في تبويب جديد
    try {
      const idStr = String(studentId);
      const href = router.resolve({ name: "discipline-student-incidents", params: { studentId: idStr }, query: { name: sObj?.full_name || undefined } }).href;
      window.open(href, "_blank");
    } catch {}
  } catch (e: any) {
    try {
      toast.error(e?.message || "تعذّر تسجيل الواقعة");
    } catch {}
  }
}

// اختيار مخالفة يدويًا من القائمة
function selectViolationForStudent(s: any, v: ViolationItem) {
  dropdownStudentId.value = null;
  void createIncidentFor(s.id, v, s);
}

// فتح صفحة وقائع الطالب عند الضغط على الاسم
function openStudentIncidents(s: any) {
  try {
    const idStr = String(s?.id ?? "");
    if (!idStr) return;
    const href = router.resolve({ name: "discipline-student-incidents", params: { studentId: idStr }, query: { name: s?.full_name || undefined } }).href;
    window.open(href, "_blank");
  } catch {}
}

// خريطة اختيار تلقائي لمخالفة التأخر/الهروب
const autoViolationMap = computed(() => {
  const out: { late?: ViolationItem; runaway?: ViolationItem } = {};
  for (const v of violations.value) {
    const cat = (v.category || "").toLowerCase();
    const code = (v.code || "").toLowerCase();
    if (!out.late && (code.includes("late") || cat.includes("تأخر") || cat.includes("متأخر"))) out.late = v;
    if (!out.runaway && (code.includes("runaway") || cat.includes("هروب") || cat.includes("هرب"))) out.runaway = v;
    if (out.late && out.runaway) break;
  }
  return out;
});

async function maybeCreateAutoIncident(s: any, st: string) {
  if (s.active === false) return;
  await ensureViolationsLoaded();
  const v = st === "late" ? autoViolationMap.value.late : st === "runaway" ? autoViolationMap.value.runaway : undefined;
  if (!v) return; // لا توجد مخالفة معرفة تلقائيًا
  await createIncidentFor(s.id, v, s);
}

// Split students into two nearly equal columns
const leftCount = computed(() => Math.ceil(students.value.length / 2));
const studentsLeft = computed(() => students.value.slice(0, leftCount.value));
const studentsRight = computed(() => students.value.slice(leftCount.value));

function statusClass(s: string) {
  // Align colors with history page badges (background colors)
  return {
    "text-bg-success": s === "present",
    "text-bg-danger": s === "absent" || s === "runaway",
    "text-bg-warning": s === "late",
    "text-bg-secondary": s === "excused",
    "text-bg-info": s === "left_early",
  } as any;
}

// Text-only color for student name (no background)
function nameClass(s: string) {
  return {
    "text-success": s === "present",
    "text-danger": s === "absent" || s === "runaway",
    "text-warning": s === "late",
    "text-secondary": s === "excused",
    "text-info": s === "left_early",
  } as any;
}

function setAll(st: "" | "present" | "absent" | "late" | "excused" | "runaway" | "left_early") {
  for (const s of students.value) {
    if (s.active === false) continue; // skip inactive students
    if (recordMap[s.id]) recordMap[s.id].status = st;
  }
}

// ----- Exit timer state -----
const exitState = reactive<
  Record<
    number,
    { running: boolean; started_at: string | null; event_id: number | null; busy?: boolean }
  >
>({});
let tickTimer: number | undefined;
const currentTime = ref(Date.now()); // Reactive current time for live timer updates

function ensureExitReason(s: any) {
  if (!recordMap[s.id].exit_reasons) recordMap[s.id].exit_reasons = "admin";
}

function autoNoteForExit(reason?: string) {
  const r = (reason || "").toLowerCase();
  const map: Record<string, string> = {
    admin: "إذن خروج إلى الإدارة",
    wing: "إذن خروج إلى مشرف الجناح",
    nurse: "إذن خروج إلى الممرض",
    restroom: "إذن خروج إلى دورة المياه",
  };
  return map[r] || (r ? `إذن خروج (${r})` : "إذن خروج");
}

function isAutoNote(note?: string) {
  const n = (note || "").trim();
  if (!n) return true;
  // Treat any note that begins with "إذن خروج" (including legacy formats like "إذن خروج — إدارة") as auto-generated
  return n.startsWith("إذن خروج");
}

function onExitReasonChange(s: any) {
  if (s.active === false) return;
  const current = (recordMap[s.id].note || "").trim();
  const reason = recordMap[s.id].exit_reasons as string;
  const auto = autoNoteForExit(reason);
  if (!current || isAutoNote(current)) {
    recordMap[s.id].note = auto;
  }
}

function onStatusChange(s: any) {
  if (s.active === false) {
    // Revert any change and notify
    recordMap[s.id].status = "" as any;
    try {
      toast.warning("الطالب غير فعال — لا يمكن إجراء أي إجراء عليه", { autoClose: 2500 });
    } catch {}
    return;
  }
  const st = recordMap[s.id].status as string;
  if (st === "excused") {
    // عند اختيار إذن خروج: ثبّت ملاحظة إذن الخروج تلقائيًا
    ensureExitReason(s);
    const current = (recordMap[s.id].note || "").trim();
    const auto = autoNoteForExit(recordMap[s.id].exit_reasons as any);
    if (!current || isAutoNote(current)) {
      recordMap[s.id].note = auto;
    }
  } else if (st === "late") {
    // عند اختيار "متأخر": ثبّت وقت العودة في الملاحظات مرة واحدة
    try {
      const now = new Date();
      const hh = now.toLocaleTimeString("ar-SA-u-nu-latn", {
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      });
      const tag = ` — وقت عودة: ${hh}`;
      const base = (recordMap[s.id].note || "").toString().trim();
      if (base.includes("وقت عودة")) {
        // لا تكرّر الوسم
        return;
      }
      if (!base) {
        // إن لم توجد ملاحظة سابقة، اكتب الوسم بدون شرطة بادئة
        recordMap[s.id].note = `وقت عودة: ${hh}`;
      } else {
        // إن وُجدت ملاحظة (بما فيها "إذن خروج — ..") فألحق الوسم
        recordMap[s.id].note = base + tag;
      }
    } catch {}
    // إنشاء واقعة تلقائيًا لمخالفة التأخر
    void maybeCreateAutoIncident(s, "late");
  } else if (st === "runaway") {
    // إنشاء واقعة تلقائيًا لمخالفة الهروب
    void maybeCreateAutoIncident(s, "runaway");
  } else {
    // لباقي الحالات: إن كانت الملاحظة مولّدة تلقائيًا لإذن الخروج فافرغها
    const current = (recordMap[s.id].note || "").trim();
    if (isAutoNote(current)) {
      recordMap[s.id].note = "";
    }
  }
}

async function loadOpenExits() {
  if (!classId.value || !dateStr.value) return;
  try {
    const data = await getOpenExitEvents({ class_id: classId.value, date: dateStr.value });
    for (const e of data) {
      exitState[e.student_id] = {
        running: true,
        started_at: e.started_at as any,
        event_id: e.id,
      } as any;
      if (recordMap[e.student_id]) {
        recordMap[e.student_id].status = "excused";
        if (!recordMap[e.student_id].exit_reasons)
          recordMap[e.student_id].exit_reasons = e.reason as any;
      }
    }
  } catch {}
}

async function startExit(s: any) {
  if (s.active === false) {
    try {
      toast.error("الطالب غير فعال — لا يمكن بدء إذن خروج");
    } catch {}
    return;
  }
  try {
    let note = (recordMap[s.id].note || "").trim();
    ensureExitReason(s);
    if (!note) {
      note = autoNoteForExit(recordMap[s.id].exit_reasons as any);
      recordMap[s.id].note = note;
    }
    exitState[s.id] = { running: true, started_at: null, event_id: null, busy: true } as any;
    const payload = {
      student_id: s.id,
      class_id: classId.value || undefined,
      date: dateStr.value,
      period_number: periodNo.value ?? undefined,
      reason: recordMap[s.id].exit_reasons as any,
      note,
    };
    const res = await postExitEvent(payload as any);
    exitState[s.id] = {
      running: true,
      started_at: res.started_at,
      event_id: res.id,
      busy: false,
    } as any;
    recordMap[s.id].status = "excused";
  } catch (e: any) {
    exitState[s.id] = { running: false, started_at: null, event_id: null } as any;
    const msg = e?.response?.data?.detail || "تعذر بدء جلسة الخروج";
    try {
      toast.error(msg);
    } catch {}
  }
}

async function returnNow(s: any) {
  if (s.active === false) {
    try {
      toast.error("الطالب غير فعال — لا يمكن إنهاء إذن الخروج");
    } catch {}
    return;
  }
  const st = exitState[s.id];
  if (!st?.event_id) return;
  try {
    st.busy = true;
    const res = await patchExitReturn(st.event_id);
    // Append return time to the note after the exit text
    try {
      const now = new Date();
      const hh = now.toLocaleTimeString("ar-SA-u-nu-latn", {
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      });
      const base = (recordMap[s.id].note || "إذن خروج").toString().trim();
      // Avoid duplicating tag
      const tag = ` — وقت عودة: ${hh}`;
      if (!base.includes("وقت عودة")) {
        recordMap[s.id].note = base + tag;
      }
    } catch {}
    // Option: set present automatically
    recordMap[s.id].status = "present";
    st.running = false;
  } catch (e: any) {
    const msg = e?.response?.data?.detail || "تعذر إغلاق جلسة الخروج";
    try {
      toast.error(msg);
    } catch {}
  } finally {
    st.busy = false;
  }
}

function formatElapsed(startIso?: string | null) {
  if (!startIso) return "—";
  const start = new Date(startIso).getTime();
  const now = currentTime.value; // Use reactive current time
  const seconds = Math.max(0, Math.floor((now - start) / 1000));
  return formatSeconds(seconds);
}

function formatSeconds(total: number) {
  const h = Math.floor(total / 3600)
    .toString()
    .padStart(2, "0");
  const m = Math.floor((total % 3600) / 60)
    .toString()
    .padStart(2, "0");
  const s = Math.floor(total % 60)
    .toString()
    .padStart(2, "0");
  return `${h}:${m}:${s}`;
}

const collator = new Intl.Collator("ar");

async function loadData() {
  await loadClassSummary();
  if (periodNo.value) {
    // If period picked, ensure class matches the selected period
    const p = todayPeriods.value.find((pp) => pp.period_number === periodNo.value);
    if (p) {
      classId.value = p.classroom_id;
    }
  }
  if (!classId.value) return;
  loading.value = true;
  saveMsg.value = "";
  try {
    const [sres, rres] = await Promise.all([
      getAttendanceStudents({ class_id: classId.value, date: dateStr.value }),
      getAttendanceRecords({
        class_id: classId.value,
        date: dateStr.value,
        period_number: periodNo.value ?? null,
      }),
    ]);
    // Arabic ascending sort by full_name
    students.value = [...sres.students].sort((a: any, b: any) => {
      return collator.compare(a.full_name || "", b.full_name || "");
    });
    // reset map
    for (const k of Object.keys(recordMap)) delete (recordMap as any)[k];
    for (const st of students.value) {
      (recordMap as any)[st.id] = { student_id: st.id, status: "", note: "", exit_reasons: "" };
    }
    for (const r of rres.records) {
      const eraw: any = (r as any).exit_reasons;
      const ereason = Array.isArray(eraw) ? eraw[0] || "" : typeof eraw === "string" ? eraw : "";
      const prev = (recordMap as any)[r.student_id];
      if (!prev) {
        (recordMap as any)[r.student_id] = {
          student_id: r.student_id,
          status: r.status,
          note: r.note ?? "",
          exit_reasons: ereason,
        };
      } else {
        // Prefer showing 'إذن خروج' if any period for the day has it; else keep existing non-empty status
        const priority = (s: string) =>
          s === "excused" ? 3 : s === "late" || s === "absent" ? 2 : s ? 1 : 0;
        const pickExisting = priority(prev.status) >= priority(r.status);
        if (pickExisting) {
          // Keep previous, but if previous was excused and current carries a reason, merge reason if missing
          if (prev.status === "excused" && !prev.exit_reasons && ereason)
            prev.exit_reasons = ereason;
        } else {
          (recordMap as any)[r.student_id] = {
            student_id: r.student_id,
            status: r.status,
            note: r.note ?? "",
            exit_reasons: ereason,
          };
        }
      }
    }
    // Load any open exit sessions and reflect their timers
    await loadOpenExits();
  } catch (e: any) {
    const msg = e?.response?.data?.detail || "حدث خطأ أثناء التحميل";
    saveMsg.value = msg;
    try {
      toast.error(msg, { autoClose: 3500 });
    } catch {}
  } finally {
    loading.value = false;
  }
}

async function save() {
  if (!classId.value) return;
  // If there are multiple possible periods today for this class/date, require selecting one to avoid backend ambiguity
  const manyPeriods = Array.isArray(todayPeriods.value) && todayPeriods.value.length > 1;
  if (manyPeriods && !periodNo.value) {
    const msg = "يرجى اختيار الحصة قبل الحفظ لتجنب التعارض.";
    saveMsg.value = msg;
    try {
      toast.warning(msg, { autoClose: 3500 });
    } catch {}
    return;
  }
  saving.value = true;
  saveMsg.value = "";
  try {
    const inact = inactiveIds.value;
    const base = Object.values(recordMap).filter((r) => !!r.status && !inact.has(r.student_id));
    // Validation: require one reason when status is 'excused'
    const missing = base.filter(
      (r) => r.status === "excused" && (!r.exit_reasons || String(r.exit_reasons).trim() === "")
    );
    if (missing.length) {
      const msg = 'يجب اختيار سبب واحد لإذن الخروج لكل طالب تم تعيين حالته "إذن خروج"';
      saveMsg.value = msg;
      try {
        toast.error(msg, { autoClose: 3500 });
      } catch {}
      return;
    }
    const records = base.map((r) => ({
      student_id: r.student_id,
      status: r.status,
      note: r.status === "excused" ? null : (r.note ?? ""),
      exit_reasons: r.status === "excused" ? (r.exit_reasons as any) : undefined,
    }));
    const res = await postAttendanceBulkSave({
      class_id: classId.value,
      date: dateStr.value,
      period_number: periodNo.value ?? (undefined as any),
      records,
    });
    const queued = (res as any)?.queued;
    const msg = queued
      ? `تمت جدولة الحفظ (${records.length}) — سيتم المزامنة عند توفر الاتصال`
      : `تم الحفظ (${res.saved})`;
    saveMsg.value = msg;
    try {
      if (queued) toast.info(msg, { autoClose: 3500 });
      else toast.success(msg, { autoClose: 2500 });
    } catch {}
    // Reload to reflect persisted records (and computed counters)
    await loadData();
  } catch (e: any) {
    const msg = e?.response?.data?.detail || "تعذر الحفظ";
    saveMsg.value = msg;
    try {
      toast.error(msg, { autoClose: 3500 });
    } catch {}
  } finally {
    saving.value = false;
  }
}

async function loadClasses() {
  try {
    const res = await getTeacherClasses();
    classes.value = res.classes || [];
    if (!classId.value && classes.value.length) {
      classId.value = classes.value[0].id;
    }
  } catch (e: any) {
    // Non-fatal; user can still enter manually if no classes available (but dropdown requires a value)
    classes.value = [];
  }
}

async function loadTodayPeriods() {
  await loadClassSummary();
  try {
    const res = await getTeacherTimetableToday({ date: dateStr.value });
    todayPeriods.value = res.periods || [];
  } catch {
    todayPeriods.value = [];
  }
}

async function loadClassSummary() {
  try {
    if (!classId.value) {
      classSummary.value = null;
      return;
    }
    const res = await getAttendanceSummary({ class_id: classId.value, date: dateStr.value });
    classSummary.value = res;
  } catch {
    classSummary.value = {
      kpis: { present_pct: null, present: 0, total: 0, absent: 0, late: 0, excused: 0 },
    } as any;
  }
}

async function onPickPeriod() {
  if (!periodNo.value) return;
  const p = todayPeriods.value.find((pp) => pp.period_number === periodNo.value);
  if (p) {
    classId.value = p.classroom_id;
    await loadClassSummary();
  }
}

function onDateChange() {
  loadTodayPeriods();
  loadClassSummary();
}

onMounted(async () => {
  await loadClasses();
  await loadTodayPeriods();
  // Update current time every second to trigger reactive timer updates
  tickTimer = window.setInterval(() => {
    currentTime.value = Date.now();
  }, 1000);
});

async function submitForReview() {
  if (!classId.value) return;
  // If multiple periods exist, require explicit period selection for precision
  const manyPeriods = Array.isArray(todayPeriods.value) && todayPeriods.value.length > 1;
  if (manyPeriods && !periodNo.value) {
    const msg = "يرجى اختيار الحصة قبل الإرسال للمراجعة.";
    saveMsg.value = msg;
    try {
      toast.warning(msg, { autoClose: 3500 });
    } catch {}
    return;
  }
  submitting.value = true;
  try {
    const res = await postAttendanceSubmit({
      class_id: classId.value,
      date: dateStr.value,
      period_number: periodNo.value ?? (undefined as any),
    });
    const msg = `تم إرسال ${res.submitted} سجلًا للمراجعة`;
    try {
      toast.success(msg, { autoClose: 2500 });
    } catch {}
    await loadData();
  } catch (e: any) {
    const msg = e?.response?.data?.detail || e?.message || "تعذر الإرسال للمراجعة";
    try {
      toast.error(msg, { autoClose: 3500 });
    } catch {}
  } finally {
    submitting.value = false;
  }
}

onBeforeUnmount(() => {
  if (tickTimer) clearInterval(tickTimer);
  // تأكد من إزالة مستمعات القائمة المفتوحة إن وُجدت
  try { detachGlobalDropdownListeners(); } catch {}
});
</script>

<style scoped>
.glass-header {
  background: rgba(255, 255, 255, 0.7);
  -webkit-backdrop-filter: blur(8px);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 16px;
}
.header-icon {
  font-size: 26px;
  color: #8a1538;
}

/* Maroon outline cards to match design */
/* Vertically center all cards when there's free space in the viewport */
.auto-card {
  border: 2px solid var(--maron-primary, #8a1538);
  border-radius: 12px;
}

/* Center cards horizontally and reduce width by 5% (scoped to this page) */

.glass-form {
  background: rgba(255, 255, 255, 0.65);
  -webkit-backdrop-filter: blur(8px);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 16px;
}

.chip {
  background: #f4f6f8;
  padding: 3px 8px;
  border-radius: 999px;
}
.chip.muted {
  background: #f7f7fa;
  color: #666;
}
.msg {
  color: #0a7;
}

/* شبكة شرائح مرتبة تلقائيًا لتفادي التراكم */
.chips-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 8px;
  align-items: center;
}

.table-card {
  border: 0;
  border-radius: 0;
  overflow: hidden;
}
.table-card thead th {
  position: sticky;
  top: 0;
  background: #fafbfc;
  z-index: 1;
}
.table-card tbody tr:hover {
  background: #fcfcff;
}
.table-card select.form-select {
  min-width: 150px;
}
/* Student name uses text color only (no background chip) */
.student-name {
  font-weight: 600;
}
.table-responsive {
  overflow-x: auto;
}
.table-toolbar {
  background: rgba(255, 255, 255, 0.65);
}
.sticky-actions {
  position: sticky;
  bottom: 0;
  background: rgba(255, 255, 255, 0.85);
}

/* --- Card grid attendance --- */
.student-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
}
@media (max-width: 1200px) {
  .student-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}
@media (max-width: 992px) {
  .student-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
@media (max-width: 768px) {
  .student-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 480px) {
  .student-grid {
    grid-template-columns: repeat(1, minmax(0, 1fr));
  }
}
.student-card {
  background: #fff;
  border: 2px solid var(--maron-primary, #8a1538);
  border-radius: 12px;
  padding: 12px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.04);
  transition:
    transform 0.15s ease,
    box-shadow 0.15s ease;
}
.student-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.06);
}
.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-weight: 800;
  color: var(--maron-primary, #6f0d0d);
  background: linear-gradient(135deg, #fff 0%, var(--maron-bg, #faf8f7) 100%);
  border: 1px solid rgba(0, 0, 0, 0.08);
  font-variant-numeric: tabular-nums;
}
.status-chip {
  display: inline-block;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 999px;
  background: #f2f4f7;
  color: #555;
  border: 1px solid rgba(0, 0, 0, 0.06);
}

/* Status colors */
.status-select.present,
.status-present .status-select,
.status-present .status-chip,
.present {
  background: #eafaf0;
  color: #137333;
  border-color: #b7e1cd;
}
.status-select.absent,
.status-absent .status-select,
.status-absent .status-chip,
.absent {
  background: #fde8e8;
  color: #b42318;
  border-color: #f5c2c2;
}
.status-select.late,
.status-late .status-select,
.status-late .status-chip,
.late {
  background: #fff4e5;
  color: #b26b00;
  border-color: #ffd8a8;
}
.status-select.excused,
.status-excused .status-select,
.status-excused .status-chip,
.excused {
  background: #e7f5ff;
  color: #0b63a8;
  border-color: #a5d8ff;
}
.status-select.runaway,
.status-runaway .status-select,
.status-runaway .status-chip,
.runaway {
  background: #fdecec;
  color: #b00020;
  border-color: #f5b5b5;
}
.status-select.left_early,
.status-left_early .status-select,
.status-left_early .status-chip,
.left_early {
  background: #f3f0ff;
  color: #5e35b1;
  border-color: #d0c2ff;
}

.status-select {
  border-width: 1px;
}
.quick-actions .btn {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
}

/* انتقالات ناعمة للقائمة لتقليل الوميض */
.dropdown-fade-enter-active,
.dropdown-fade-leave-active {
  transition: opacity 120ms ease, transform 120ms ease;
}
.dropdown-fade-enter-from,
.dropdown-fade-leave-to {
  opacity: 0;
  transform: scale(0.98);
}
.grid-toolbar .search-icon {
  position: absolute;
  inset-inline-start: 10px;
  top: 50%;
  transform: translateY(-50%);
  opacity: 0.5;
}

/* Toolbar for filters and actions: wrap on small screens, single line on large without horizontal scroll */
/* Attendance Form Styles */
.attendance-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1rem;
  align-items: end;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  font-size: 0.875rem;
  color: #495057;
  margin-bottom: 0;
}

.form-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  padding-top: 0.5rem;
  border-top: 1px solid #e9ecef;
}

.form-actions button {
  flex: 1 1 auto;
  min-width: 140px;
}

.btn-text-short {
  display: none;
}

/* Mobile & Up - All in one row */
@media (min-width: 576px) {
  .form-row {
    grid-template-columns: 160px 150px 1fr auto;
  }

  .form-field-wide {
    grid-column: auto;
  }

  .btn-load {
    align-self: end;
  }

  .form-actions button {
    flex: 0 1 auto;
  }
}

/* Tablet & Up */
@media (min-width: 768px) {
  .form-row {
    grid-template-columns: 180px 160px 1fr auto;
  }
}

/* Desktop */
@media (min-width: 992px) {
  .form-row {
    grid-template-columns: 200px 180px 1fr auto;
  }
}

/* Large Desktop */
@media (min-width: 1200px) {
  .form-row {
    grid-template-columns: 220px 200px 1fr auto;
  }
}

/* Mobile - Show short text */
@media (max-width: 576px) {
  .btn-text {
    display: none;
  }

  .btn-text-short {
    display: inline;
  }

  .form-actions button {
    min-width: 100px;
  }
}

/* Stats Header */
.stats-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid #e9ecef;
  flex-wrap: wrap;
}

.date-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  border-radius: 8px;
  font-size: 0.875rem;
  font-weight: 600;
  color: #495057;
  border: 1px solid #dee2e6;
  white-space: nowrap;
}

@media (max-width: 576px) {
  .stats-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .date-badge {
    align-self: stretch;
    justify-content: center;
  }
}

/* Two-column students grid (full-bleed) */
.students-two-col {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
  width: var(--page-w);
  margin-inline: auto;
  padding-inline: 0 12px;
  box-sizing: border-box;
}
@media (min-width: 992px) {
  /* lg breakpoint */
  .students-two-col {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  }
}
.students-two-col > .auto-card {
  width: 100%;
}

.loader-line {
  height: 3px;
  background: linear-gradient(90deg, #8a1538, #b23a48);
  animation: load 1.1s linear infinite;
  border-radius: 2px;
}
@keyframes load {
  from {
    background-position: 0 0;
  }
  to {
    background-position: 200% 0;
  }
}

/* Single-line enhancements */
.name-row {
  white-space: nowrap;
}
.status-chip.no-wrap {
  white-space: nowrap;
  flex: 0 0 auto;
}
.student-card header {
  flex-wrap: nowrap;
}
.controls-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap; /* Allow wrapping to prevent overflow */
}
.controls-row .form-select {
  flex: 0 0 auto;
  min-width: 160px;
  max-width: 100%;
}
.controls-row .form-control {
  flex: 1 1 auto;
  min-width: 120px;
  max-width: 100%;
  word-wrap: break-word;
  overflow-wrap: break-word;
  box-sizing: border-box; /* Ensure padding doesn't cause overflow */
}
.exit-reasons {
  flex-wrap: nowrap !important;
  overflow-x: auto;
  white-space: nowrap;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: thin;
}
.exit-reasons > * {
  white-space: nowrap;
}
.exit-controls {
  flex-wrap: nowrap;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}
.quick-actions {
  flex: 0 0 auto;
}
</style>

<style scoped>
/* السماح بالتمرير على مستوى الصفحة بدلاً من الجدول */
.page-grid {
  grid-template-rows: auto auto auto auto;
}
/* إزالة القيود التي تمنع تمدد المكونات وظهور تمرير الصفحة */
.page-grid > * {
  margin: 0 !important;
}
/* الحفاظ على عرض المكونات بالكامل */
.page-grid .auto-card {
  width: 100%;
}
.page-grid .glass-form,
.page-grid .glass-header {
  width: 100%;
}
/* عدم تحويل بطاقة الجدول إلى flex لتجنب تمرير داخلي */
.page-grid .auto-card.p-0 {
}

/* Align the 95% width container to the right edge (RTL) */
/* Larger screens: slightly increase grid density */
@media (min-width: 1400px) {
  .student-grid {
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 14px;
  }
}
</style>

<style scoped>
/* Single-line toolbar (filters + action buttons) */
.form-toolbar {
  display: flex;
  align-items: end;
  gap: 0.5rem;
  flex-wrap: nowrap;
  overflow-x: auto;
  white-space: nowrap;
  -webkit-overflow-scrolling: touch;
}
.form-toolbar > * {
  flex: 0 0 auto;
}
.form-toolbar .form-field {
  min-width: 150px;
}
.form-toolbar .form-field.form-field-wide {
  min-width: 240px;
}
.form-toolbar .btn-load {
  height: 38px;
}
@media (min-width: 768px) {
  .form-toolbar .form-field {
    min-width: 170px;
  }
  .form-toolbar .form-field.form-field-wide {
    min-width: 300px;
  }
}
</style>

<style scoped>
/* خلفية سلفر للطالب غير الفعال */
.student-card.inactive {
  background: silver !important;
  border-color: #b0b0b0 !important;
}
</style>
