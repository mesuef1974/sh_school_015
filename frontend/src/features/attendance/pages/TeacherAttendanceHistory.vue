<template>
  <section>
    <!-- Compact Toolbar: Title + Filters + Search in one card -->
    <DsCard
      class="mb-3 toolbar-card"
      v-motion
      :initial="{ opacity: 0, y: -12 }"
      :enter="{ opacity: 1, y: 0 }"
    >
      <div class="d-flex flex-wrap align-items-center gap-3 mb-2">
        <div class="d-flex align-items-center gap-2">
          <Icon icon="solar:history-bold-duotone" class="text-3xl text-primary" />
          <div>
            <h1 class="h6 mb-0">سجل الغياب للمعلم</h1>
            <small class="text-muted">عرض سجلات الغياب مع فلاتر مدمجة</small>
          </div>
        </div>
        <div class="ms-auto d-flex align-items-center gap-2 search-inline" v-if="rows.length > 0">
          <Icon icon="solar:magnifer-bold-duotone" class="text-lg" />
          <input
            v-model="searchQuery"
            type="text"
            class="form-control form-control-sm"
            placeholder="بحث في أسماء الطلبة..."
            data-testid="history-search"
          />
          <div class="text-muted small d-none d-md-block">
            {{ filteredRows.length }} / {{ rows.length }}
          </div>
        </div>
      </div>

      <form @submit.prevent="loadHistory" class="row g-2 align-items-end">
        <div class="col-12 col-md-6 col-lg-3">
          <label class="form-label fw-bold small mb-1">
            <Icon icon="solar:layers-minimalistic-bold-duotone" width="16" class="me-1" />
            الصف
          </label>
          <select v-model.number="classId" required class="form-select form-select-sm">
            <option :value="null" disabled>اختر الصف</option>
            <option v-for="c in classes" :key="c.id" :value="c.id">
              {{ c.name || "صف #" + c.id }}
            </option>
          </select>
        </div>
        <div class="col-6 col-md-3 col-lg-2">
          <label class="form-label fw-bold small mb-1" for="histFrom">
            <Icon icon="solar:calendar-bold-duotone" width="16" class="me-1" />
            من
          </label>
          <DatePickerDMY :id="'histFrom'" v-model="fromStr" inputClass="form-control form-control-sm" wrapperClass="m-0" :aria-label="'من تاريخ'" />
        </div>
        <div class="col-6 col-md-3 col-lg-2">
          <label class="form-label fw-bold small mb-1" for="histTo">
            <Icon icon="solar:calendar-bold-duotone" width="16" class="me-1" />
            إلى
          </label>
          <DatePickerDMY :id="'histTo'" v-model="toStr" inputClass="form-control form-control-sm" wrapperClass="m-0" :aria-label="'إلى تاريخ'" />
        </div>
        <div class="col-6 col-md-3 col-lg-2">
          <label class="form-label fw-bold small mb-1">
            <Icon icon="solar:filter-bold-duotone" width="16" class="me-1" />
            الحالة
          </label>
          <select v-model="statusFilter" class="form-select form-select-sm">
            <option value="">الكل</option>
            <option value="present">حاضر</option>
            <option value="absent">غائب</option>
            <option value="late">متأخر</option>
            <option value="excused">إذن</option>
            <option value="runaway">هروب</option>
            <option value="left_early">انصراف مبكر</option>
          </select>
        </div>
        <div class="col-6 col-md-3 col-lg-2 order-lg-last ms-auto">
          <div class="d-flex gap-2 justify-content-start justify-content-lg-end">
            <DsButton
              type="submit"
              size="sm"
              variant="primary"
              icon="solar:magnifer-bold-duotone"
              :loading="loading"
            >
              بحث
            </DsButton>
            <DsButton
              type="button"
              size="sm"
              variant="success"
              icon="solar:export-bold-duotone"
              data-testid="history-export"
              :disabled="filteredRows.length === 0"
              @click="exportData"
            >
              تصدير
            </DsButton>
          </div>
        </div>
      </form>
    </DsCard>

    <!-- Loading State -->
    <DsCard v-if="loading" class="text-center py-5">
      <Icon
        icon="solar:refresh-bold-duotone"
        class="text-5xl mb-3 animate-spin"
        style="color: var(--maron-primary)"
      />
      <div class="text-muted">جاري تحميل البيانات...</div>
    </DsCard>

    <!-- Empty State -->
    <DsCard v-else-if="rows.length === 0" class="text-center py-5">
      <Icon
        icon="solar:inbox-line-bold-duotone"
        class="text-6xl mb-3"
        style="opacity: 0.3; color: var(--color-info)"
      />
      <div class="h5 mb-2">لا توجد سجلات</div>
      <div class="text-muted small">لا توجد سجلات غياب في النطاق الزمني المحدد</div>
    </DsCard>

    <!-- No Results State -->
    <DsCard v-else-if="filteredRows.length === 0" class="text-center py-5">
      <Icon
        icon="solar:magnifer-zoom-out-bold-duotone"
        class="text-6xl mb-3"
        style="opacity: 0.3; color: var(--color-warning)"
      />
      <div class="h5 mb-2">لا توجد نتائج</div>
      <div class="text-muted small">لا توجد سجلات تطابق معايير البحث والفلترة</div>
      <DsButton
        variant="outline"
        size="sm"
        class="mt-3"
        @click="
          searchQuery = '';
          statusFilter = '';
        "
      >
        <Icon icon="solar:refresh-bold-duotone" class="me-1" />
        إعادة تعيين الفلاتر
      </DsButton>
    </DsCard>

    <!-- Modern Professional Table -->
    <DsCard v-else class="p-0 overflow-hidden">
      <div class="modern-table-wrapper">
        <table class="modern-table">
          <thead>
            <tr>
              <th class="modern-th" style="width: 60px">
                <div class="th-content">
                  <Icon icon="solar:hashtag-bold-duotone" width="18" />
                  <span>#</span>
                </div>
              </th>
              <th class="modern-th" style="width: 110px">
                <div class="th-content">
                  <Icon icon="solar:calendar-bold-duotone" width="18" />
                  <span>التاريخ</span>
                </div>
              </th>
              <th class="modern-th" style="width: 110px">
                <div class="th-content">
                  <Icon icon="solar:calendar-date-bold-duotone" width="18" />
                  <span>اليوم</span>
                </div>
              </th>
              <th class="modern-th">
                <div class="th-content">
                  <Icon icon="solar:user-bold-duotone" width="18" />
                  <span>اسم الطالب</span>
                </div>
              </th>
              <th class="modern-th" style="width: 80px">
                <div class="th-content">
                  <Icon icon="solar:clock-circle-bold-duotone" width="18" />
                  <span>الحصة</span>
                </div>
              </th>
              <th class="modern-th" style="width: 120px">
                <div class="th-content">
                  <Icon icon="solar:book-2-bold-duotone" width="18" />
                  <span>المادة</span>
                </div>
              </th>
              <th class="modern-th" style="width: 120px">
                <div class="th-content">
                  <Icon icon="solar:widget-5-bold-duotone" width="18" />
                  <span>الحالة</span>
                </div>
              </th>
              <th class="modern-th" style="width: 600px">
                <div class="th-content">
                  <Icon icon="solar:notes-bold-duotone" width="18" />
                  <span>ملاحظة</span>
                </div>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(row, i) in filteredRows"
              :key="i"
              :class="['modern-tr', { inactive: isInactive(row) }]"
              v-motion
              :initial="{ opacity: 0, x: -20 }"
              :enter="{ opacity: 1, x: 0, transition: { duration: 300, delay: i * 20 } }"
            >
              <td class="modern-td text-center">
                <span class="row-number">{{ i + 1 }}</span>
              </td>
              <td class="modern-td">
                <div class="d-flex align-items-center gap-2">
                  <Icon icon="solar:calendar-mark-bold-duotone" width="16" style="opacity: 0.5" />
                  <span>{{ formatDate(row.date) }}</span>
                </div>
              </td>
              <td class="modern-td">
                <div class="d-flex align-items-center gap-2">
                  <Icon icon="solar:calendar-line-bold-duotone" width="16" style="opacity: 0.5" />
                  <span>{{ dayNameAr(row.date) }}</span>
                </div>
              </td>
              <td class="modern-td">
                <div class="student-cell">
                  <div class="student-avatar" :class="`avatar-${badgeVariant(row.status)}`">
                    <Icon :icon="statusIcon(row.status)" width="16" />
                  </div>
                  <span class="student-name-modern">{{ row.student_name }}</span>
                </div>
              </td>
              <td class="modern-td text-center">
                <div v-if="row.period_number" class="period-badge">
                  <Icon icon="solar:clock-circle-bold-duotone" width="14" />
                  <span>{{ row.period_number }}</span>
                </div>
                <span v-else class="text-muted">—</span>
              </td>
              <td class="modern-td">
                <div v-if="row.subject_name" class="subject-cell">
                  <Icon
                    v-if="subjectIcon(row.subject_name)"
                    :icon="subjectIcon(row.subject_name)"
                    width="16"
                    style="color: var(--maron-primary)"
                  />
                  <span class="subject-name-text">{{ row.subject_name }}</span>
                </div>
                <span v-else class="text-muted">—</span>
              </td>
              <td class="modern-td">
                <DsBadge
                  :variant="badgeVariant(row.status)"
                  :icon="statusIcon(row.status)"
                  size="sm"
                  class="status-badge"
                >
                  {{ statusLabel(row.status) }}
                </DsBadge>
              </td>
              <td class="modern-td">
                <div class="note-text" :title="row.note || ''">
                  {{ row.note || "—" }}
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination Footer -->
      <div class="table-footer">
        <div class="d-flex align-items-center justify-content-between flex-wrap gap-3">
          <div class="text-muted small">
            <Icon icon="solar:list-bold-duotone" width="16" class="me-1" />
            عرض <strong>{{ filteredRows.length }}</strong> سجل من أصل <strong>{{ total }}</strong>
          </div>
          <div class="d-flex align-items-center gap-2">
            <DsButton
              size="sm"
              variant="outline"
              data-testid="history-prev"
              :disabled="page <= 1 || loading"
              @click="prevPage"
              icon="solar:arrow-right-bold-duotone"
            >
              السابق
            </DsButton>
            <div class="pagination-info">
              صفحة <strong>{{ page }}</strong> من
              <strong>{{ Math.max(1, Math.ceil(total / pageSize)) }}</strong>
            </div>
            <DsButton
              size="sm"
              variant="outline"
              data-testid="history-next"
              :disabled="page * pageSize >= total || loading"
              @click="nextPage"
              icon="solar:arrow-left-bold-duotone"
            >
              التالي
            </DsButton>
          </div>
        </div>
      </div>
    </DsCard>
  </section>
</template>

<script setup lang="ts">
import DatePickerDMY from "../../../components/ui/DatePickerDMY.vue";
import { subjectIcon } from "../../../shared/icons/subjectIcons";
import { ref, onMounted, computed } from "vue";
import {
  getAttendanceHistory,
  getTeacherClasses,
  getAttendanceStudents,
} from "../../../shared/api/client";
import { formatDateDMY } from "../../../shared/utils/date";
import DsButton from "../../../components/ui/DsButton.vue";
import DsBadge from "../../../components/ui/DsBadge.vue";
import DsCard from "../../../components/ui/DsCard.vue";

const today = new Date();
const iso = (d: Date) => d.toISOString().slice(0, 10);
const defaultTo = iso(today);
const defaultFrom = iso(new Date(today.getTime() - 6 * 24 * 60 * 60 * 1000));

const classId = ref<number | null>(null);
const classes = ref<{ id: number; name?: string }[]>([]);
const fromStr = ref<string>(defaultFrom);
const toStr = ref<string>(defaultTo);
const loading = ref(false);
const page = ref(1);
const pageSize = ref(100);
const total = ref(0);

interface Row {
  date: string;
  student_id: number;
  student_name: string;
  status: string;
  note?: string | null;
  period_number?: number;
  subject_name?: string;
}
const rows = ref<Row[]>([]);

// Map of student_id -> active (true) or inactive (false)
const activeMap = ref<Record<number, boolean>>({});

function isInactive(row: Row): boolean {
  const v = activeMap.value[row.student_id as keyof typeof activeMap.value];
  return v === false;
}

// Filter states
const searchQuery = ref("");
const statusFilter = ref("");

// Filtered rows based on search and status
const filteredRows = computed(() => {
  let result = rows.value;

  // Filter by status
  if (statusFilter.value) {
    result = result.filter((r) => r.status === statusFilter.value);
  }

  // Filter by search query
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.trim().toLowerCase();
    result = result.filter((r) => r.student_name.toLowerCase().includes(query));
  }

  return result;
});

// Split filtered rows into two nearly equal columns
const filteredLeftCount = computed(() => Math.ceil(filteredRows.value.length / 2));
const filteredRowsLeft = computed(() => filteredRows.value.slice(0, filteredLeftCount.value));
const filteredRowsRight = computed(() => filteredRows.value.slice(filteredLeftCount.value));

function statusLabel(s: string) {
  switch (s) {
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
      return s;
  }
}
function statusClass(s: string) {
  return {
    "text-bg-success": s === "present",
    "text-bg-danger": s === "absent" || s === "runaway",
    "text-bg-warning": s === "late",
    "text-bg-secondary": s === "excused",
    "text-bg-info": s === "left_early",
  };
}

function badgeVariant(s: string): "success" | "danger" | "warning" | "info" {
  if (s === "present") return "success";
  if (s === "absent" || s === "runaway") return "danger";
  if (s === "late") return "warning";
  return "info";
}

function statusIcon(s: string): string {
  switch (s) {
    case "present":
      return "solar:check-circle-bold-duotone";
    case "absent":
      return "solar:close-circle-bold-duotone";
    case "late":
      return "solar:clock-circle-bold-duotone";
    case "excused":
      return "solar:shield-check-bold-duotone";
    case "runaway":
      return "solar:running-bold-duotone";
    case "left_early":
      return "solar:exit-bold-duotone";
    default:
      return "solar:question-circle-bold-duotone";
  }
}

async function loadStudents() {
  if (!classId.value) return;
  try {
    const sres = await getAttendanceStudents({ class_id: classId.value, date: toStr.value });
    const map: Record<number, boolean> = {};
    for (const s of sres.students || []) {
      map[s.id] = s.active !== false;
    }
    activeMap.value = map;
  } catch {
    activeMap.value = {};
  }
}

async function loadHistory() {
  if (!classId.value) return;
  loading.value = true;
  try {
    await loadStudents();
    const res = await getAttendanceHistory({
      class_id: classId.value,
      from: fromStr.value,
      to: toStr.value,
      page: page.value,
      page_size: pageSize.value,
    });
    total.value = res.count || 0;
    rows.value = (res.results || []).map((r) => ({
      date: r.date,
      student_id: r.student_id,
      student_name: r.student_name || `#${r.student_id}`,
      status: r.status,
      note: r.note,
      period_number: r.period_number,
      subject_name: r.subject_name,
    }));
  } finally {
    loading.value = false;
  }
}

const formatDate = (dateStr: string): string => formatDateDMY(dateStr);

// Arabic day names (Sun..Sat)
const DAY_NAMES_AR = ["الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت"];
function dayNameAr(dateStr: string): string {
  if (!dateStr) return "—";
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(dateStr));
  let d: Date;
  if (m) {
    const y = parseInt(m[1], 10);
    const mo = parseInt(m[2], 10);
    const dd = parseInt(m[3], 10);
    d = new Date(y, mo - 1, dd); // local date to avoid TZ shifts
  } else {
    d = new Date(dateStr);
  }
  if (isNaN(d.getTime())) return "—";
  const dow = d.getDay(); // 0=Sun..6=Sat
  return DAY_NAMES_AR[dow] || "—";
}

function nextPage() {
  if (page.value * pageSize.value < total.value) {
    page.value += 1;
    loadHistory();
  }
}
function prevPage() {
  if (page.value > 1) {
    page.value -= 1;
    loadHistory();
  }
}

function exportData() {
  if (filteredRows.value.length === 0) return;

  // Create CSV content
  const headers = ["#", "التاريخ", "اليوم", "الطالب", "الحصة", "المادة", "الحالة", "ملاحظة"];
  const csvRows = [headers.join(",")];

  filteredRows.value.forEach((row, i) => {
    const csvRow = [
      i + 1,
      formatDate(row.date),
      dayNameAr(row.date),
      row.student_name,
      row.period_number || "",
      row.subject_name || "",
      statusLabel(row.status),
      row.note || "",
    ]
      .map((field) => `"${field}"`)
      .join(",");
    csvRows.push(csvRow);
  });

  const csvContent = "\uFEFF" + csvRows.join("\n"); // BOM for Excel UTF-8 support
  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const link = document.createElement("a");
  const url = URL.createObjectURL(blob);

  const className =
    classes.value.find((c) => c.id === classId.value)?.name || `صف_${classId.value}`;
  const filename = `سجل_الغياب_${className}_${fromStr.value}_${toStr.value}.csv`;

  link.setAttribute("href", url);
  link.setAttribute("download", filename);
  link.style.visibility = "hidden";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

onMounted(async () => {
  try {
    const res = await getTeacherClasses();
    classes.value = res.classes || [];
    if (!classId.value && classes.value.length) {
      classId.value = classes.value[0].id;
    }
  } catch {
    classes.value = [];
  }
});
</script>

<style scoped>
/* Toolbar compact styles */
.toolbar-card :is(.form-label) {
  margin-bottom: 0.25rem;
}
.toolbar-card .form-control,
.toolbar-card .form-select {
  min-height: 36px;
}
.search-inline {
  min-width: 260px;
}
@media (max-width: 768px) {
  .search-inline {
    width: 100%;
    order: 3;
  }
}

/* Modern Professional Table Styles */
.modern-table-wrapper {
  overflow-x: auto;
  overflow-y: visible;
}

.modern-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: 0.9rem;
}

.modern-th {
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  border-bottom: 2px solid #dee2e6;
  padding: 1rem;
  text-align: end;
  font-weight: 600;
  color: #495057;
  position: sticky;
  top: 0;
  z-index: 10;
  white-space: nowrap;
}

.th-content {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.modern-tr {
  transition: all 0.2s ease;
  background: white;
}

/* Silver background for inactive students */
.modern-tr.inactive {
  background: silver !important;
}

.modern-tr:hover {
  background: #f8f9fa;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  transform: scale(1.001);
}

.modern-td {
  padding: 1rem;
  border-bottom: 1px solid #f0f0f0;
  vertical-align: middle;
}

.row-number {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, #e9ecef 0%, #f8f9fa 100%);
  color: #6c757d;
  font-weight: 600;
  font-size: 0.85rem;
}

.student-cell {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.student-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.avatar-success {
  background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
  color: #155724;
}

.avatar-danger {
  background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
  color: #721c24;
}

.avatar-warning {
  background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
  color: #856404;
}

.avatar-info {
  background: linear-gradient(135deg, #d1ecf1 0%, #bee5eb 100%);
  color: #0c5460;
}

.student-name-modern {
  font-weight: 500;
  color: #212529;
}

.status-badge {
  min-width: 100px;
  justify-content: center;
}

.note-text {
  color: #6c757d;
  font-size: 0.85rem;
  max-width: 600px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.4;
}

.table-footer {
  padding: 1rem 1.5rem;
  background: #f8f9fa;
  border-top: 1px solid #dee2e6;
}

.pagination-info {
  padding: 0.375rem 0.75rem;
  background: white;
  border: 1px solid #dee2e6;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  color: #495057;
}

.pagination-info strong {
  color: var(--maron-primary);
}

/* Loading spinner animation */
@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.animate-spin {
  animation: spin 2s linear infinite;
}

/* Period Badge */
.period-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.75rem;
  background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
  border: 2px solid #2196f3;
  border-radius: 12px;
  font-weight: 600;
  font-size: 0.85rem;
  color: #1976d2;
  box-shadow: 0 2px 6px rgba(33, 150, 243, 0.15);
}

/* Subject Cell */
.subject-cell {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.subject-name-text {
  font-weight: 500;
  color: #495057;
}

/* Responsive */
@media (max-width: 768px) {
  .modern-th,
  .modern-td {
    padding: 0.75rem 0.5rem;
    font-size: 0.85rem;
  }

  .student-avatar {
    width: 32px;
    height: 32px;
  }

  .note-text {
    max-width: 240px;
  }

  .pagination-info {
    font-size: 0.8rem;
  }
}
</style>