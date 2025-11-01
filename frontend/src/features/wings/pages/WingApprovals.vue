<template>
  <section class="d-grid gap-3 page-grid page-grid-wide">
    <!-- Unified page header (icon + title + wing label only) -->
    <WingPageHeader :icon="tileMeta.icon" :title="tileMeta.title" :color="tileMeta.color">
          <template #actions>
            <WingWingPicker id="pick-approvals-wing" />
          </template>
        </WingPageHeader>

    <!-- Toolbar card: date, class filter, refresh -->
    <div class="auto-card p-2 d-flex align-items-center gap-2 flex-wrap">
      <DatePickerDMY
        :id="'wing-approvals-date'"
        :aria-label="'اختيار التاريخ'"
        wrapperClass="m-0"
        inputClass="form-control w-auto"
        v-model="dateStr"
        @change="onDateChange"
      />
      <select class="form-select w-auto" v-model.number="selectedClassId" @change="load" aria-label="تصفية حسب الصف">
        <option :value="null">كل الصفوف</option>
        <option v-for="c in classes" :key="c.id" :value="c.id">
          {{ c.name || 'صف #' + c.id }}
        </option>
      </select>
      <DsButton ref="refreshBtn" variant="primary" icon="solar:refresh-bold-duotone" @click="load">تحديث</DsButton>
      <span class="ms-auto small text-muted" aria-live="polite">{{ liveMsg }}</span>
    </div>

    <div v-if="error" class="alert alert-danger" role="alert">{{ error }}</div>

    <div v-if="!hasWingRole && !isSuper" class="alert alert-warning" role="alert">
      لا تملك صلاحية مشرف جناح لهذه الصفحة.
    </div>

    <div class="visually-hidden" aria-live="polite">{{ liveMsg }}</div>

    <div class="auto-card p-3">
      <div class="mb-2 d-flex align-items-center gap-2">
        <label class="form-label m-0 small text-muted">وضع العرض:</label>
        <div class="btn-group" role="group" aria-label="Display mode">
          <button type="button" class="btn btn-sm" :class="mode==='daily' ? 'btn-primary' : 'btn-outline-primary'" @click="mode='daily'; load()">الحالة العامة اليومية</button>
          <button type="button" class="btn btn-sm" :class="mode==='period' ? 'btn-primary' : 'btn-outline-primary'" @click="mode='period'; load()">حسب الحصة (المعلقة)</button>
        </div>
        <span class="small text-muted ms-2" v-if="mode==='daily'">يعتمد احتساب اليوم على الحصتين الأولى والثانية فقط وفق السياسة.</span>
      </div>

      <div v-if="loading" class="loader-line"></div>
      <template v-else>
        <!-- Daily general status view -->
        <div v-if="mode==='daily'">
          <div class="d-flex align-items-center gap-2 mb-2 flex-wrap">
            <DsBadge :text="`بدون عذر: ${dailyCounts.unexcused}`" />
            <DsBadge :text="`بعذر: ${dailyCounts.excused}`" />
            <DsBadge :text="`غير محسوب: ${dailyCounts.none}`" />
            <span class="ms-auto"></span>
            <small class="text-muted">يعتمد التصنيف على الحصتين الأولى والثانية فقط.</small>
          </div>
          <div class="table-responsive table-card">
            <table class="table table-hover align-middle">
              <thead>
                <tr>
                  <th>الطالب</th>
                  <th>الصف</th>
                  <th>الحالة العامة</th>
                  <th>ح1</th>
                  <th>ح2</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="it in dailyItems" :key="`${it.student_id}-${it.class_id}`">
                  <td>{{ it.student_name || ('#' + it.student_id) }}</td>
                  <td>{{ it.class_name || (it.class_id ? ('صف #' + it.class_id) : '—') }}</td>
                  <td>
                    <span :class="['att-chip','day-state', it.state || 'none']">{{ stateLabel(it.state) }}</span>
                  </td>
                  <td>
                    <span :class="['att-chip','att-status', (it.p1 || 'none')]">{{ statusLabel(it.p1 || '') }}</span>
                  </td>
                  <td>
                    <span :class="['att-chip','att-status', (it.p2 || 'none')]">{{ statusLabel(it.p2 || '') }}</span>
                  </td>
                </tr>
                <tr v-if="!dailyItems.length">
                  <td colspan="5" class="text-center text-muted">لا توجد بيانات لليوم المختار</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <!-- Period-based pending approvals view -->
        <div v-else>
        <div class="d-flex align-items-center gap-2 mb-2 flex-wrap">
          <DsBadge :text="`الإجمالي: ${items.length}`" />
          <DsBadge
            v-if="filteredItems.length !== items.length"
            :text="`بعد الفلترة: ${filteredItems.length}`"
          />
          <span class="ms-auto"></span>
          <div
            v-if="selectedClassId"
            class="filters d-flex align-items-center gap-2 flex-wrap me-auto"
          >
            <div class="d-flex align-items-center gap-1">
              <span class="small text-muted">الحالة:</span>
              <label
                class="form-check form-check-inline small"
                v-for="s in statusOptions"
                :key="s.value"
              >
                <input
                  class="form-check-input"
                  type="checkbox"
                  :value="s.value"
                  @change="onStatusToggle($event, s.value)"
                  :checked="filters.statuses.has(s.value)"
                />
                <span class="form-check-label">{{ s.label }}</span>
              </label>
            </div>
            <div class="d-flex align-items-center gap-1">
              <span class="small text-muted">حصة:</span>
              <select
                class="form-select form-select-sm w-auto"
                v-model.number="filters.period"
                @change="savePrefs"
              >
                <option :value="null">الكل</option>
                <option v-for="p in periods" :key="p" :value="p">{{ p }}</option>
              </select>
            </div>
            <div class="d-flex align-items-center gap-1">
              <span class="small text-muted">المعلم:</span>
              <select
                class="form-select form-select-sm w-auto"
                v-model="filters.teacher"
                @change="savePrefs"
              >
                <option value="">الكل</option>
                <option v-for="t in teachers" :key="t" :value="t">{{ t || "—" }}</option>
              </select>
            </div>
            <div class="d-flex align-items-center gap-1">
              <span class="small text-muted">بحث:</span>
              <input
                type="search"
                class="form-control form-control-sm"
                style="min-width: 160px"
                v-model.trim="filters.q"
                @input="savePrefs"
                placeholder="اسم الطالب/ملاحظة"
              />
            </div>
            <button class="btn btn-sm btn-outline-secondary" type="button" @click="resetFilters">
              إعادة الضبط
            </button>
          </div>
          <details class="ms-2">
            <summary class="btn btn-sm btn-outline-primary">خيارات الجدول</summary>
            <div class="dropdown-card p-2 mt-1">
              <div class="small fw-bold mb-1">إظهار الأعمدة</div>
              <label class="form-check small" v-for="(v, k) in columnVis" :key="k">
                <input
                  class="form-check-input"
                  type="checkbox"
                  v-model="(columnVis as any)[k]"
                  @change="savePrefs"
                />
                <span class="form-check-label">{{ columnLabels[k] }}</span>
              </label>
              <hr class="my-2" />
              <div class="small text-muted">انقر على عنوان العمود للفرز تصاعديًا/تنازليًا</div>
            </div>
          </details>
          <DsButton
            :disabled="!selectedIds.size || !canAct"
            variant="success"
            icon="solar:check-circle-bold-duotone"
            @click="decide('approve')"
            >اعتماد المحدد</DsButton
          >
          <DsButton
            :disabled="!selectedIds.size || !canAct"
            variant="danger"
            icon="solar:close-circle-bold-duotone"
            @click="decide('reject')"
            >رفض المحدد</DsButton
          >
          <DsButton
            :disabled="!selectedIds.size || !canAct"
            variant="warning"
            icon="solar:document-add-bold-duotone"
            @click="openExcuseModal()"
            >اعتبار بعذر</DsButton
          >
        </div>
        <div class="table-responsive table-card">
          <table class="table table-hover align-middle">
            <thead>
              <tr>
                <th style="width: 36px">
                  <input type="checkbox" @change="toggleAll($event)" :checked="allChecked" />
                </th>
                <th v-if="columnVis.student" role="button" tabindex="0" :aria-sort="sortKey==='student' ? (sortDir==='asc'?'ascending':'descending') : 'none'" @click="toggleSort('student')" @keydown.enter.prevent="toggleSort('student')" @keydown.space.prevent="toggleSort('student')">
                  الطالب
                  <span class="sort" v-if="sortKey === 'student'">{{
                    sortDir === "asc" ? "▲" : "▼"
                  }}</span>
                </th>
                <th v-if="columnVis.class" role="button" tabindex="0" :aria-sort="sortKey==='class' ? (sortDir==='asc'?'ascending':'descending') : 'none'" @click="toggleSort('class')" @keydown.enter.prevent="toggleSort('class')" @keydown.space.prevent="toggleSort('class')">
                  الصف
                  <span class="sort" v-if="sortKey === 'class'">{{
                    sortDir === "asc" ? "▲" : "▼"
                  }}</span>
                </th>
                <th v-if="columnVis.period" role="button" tabindex="0" :aria-sort="sortKey==='period' ? (sortDir==='asc'?'ascending':'descending') : 'none'" @click="toggleSort('period')" @keydown.enter.prevent="toggleSort('period')" @keydown.space.prevent="toggleSort('period')">
                  الحصة
                  <span class="sort" v-if="sortKey === 'period'">{{
                    sortDir === "asc" ? "▲" : "▼"
                  }}</span>
                </th>
                <th v-if="columnVis.status" role="button" tabindex="0" :aria-sort="sortKey==='status' ? (sortDir==='asc'?'ascending':'descending') : 'none'" @click="toggleSort('status')" @keydown.enter.prevent="toggleSort('status')" @keydown.space.prevent="toggleSort('status')">
                  الحالة
                  <span class="sort" v-if="sortKey === 'status'">{{
                    sortDir === "asc" ? "▲" : "▼"
                  }}</span>
                </th>
                <th v-if="columnVis.teacher" role="button" tabindex="0" :aria-sort="sortKey==='teacher' ? (sortDir==='asc'?'ascending':'descending') : 'none'" @click="toggleSort('teacher')" @keydown.enter.prevent="toggleSort('teacher')" @keydown.space.prevent="toggleSort('teacher')">
                  المعلم
                  <span class="sort" v-if="sortKey === 'teacher'">{{
                    sortDir === "asc" ? "▲" : "▼"
                  }}</span>
                </th>
                <th v-if="columnVis.note" role="button" tabindex="0" :aria-sort="sortKey==='note' ? (sortDir==='asc'?'ascending':'descending') : 'none'" @click="toggleSort('note')" @keydown.enter.prevent="toggleSort('note')" @keydown.space.prevent="toggleSort('note')">
                  الملاحظة
                  <span class="sort" v-if="sortKey === 'note'">{{
                    sortDir === "asc" ? "▲" : "▼"
                  }}</span>
                </th>
                <th style="width: 160px">إجراءات</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="it in filteredAndSorted" :key="it.id">
                <td><input type="checkbox" :value="it.id" v-model="checkedList" /></td>
                <td v-if="columnVis.student">{{ it.student_name || "#" + it.student_id }}</td>
                <td v-if="columnVis.class">{{ it.class_name || "صف #" + (it.class_id || "") }}</td>
                <td v-if="columnVis.period">حصة {{ it.period_number || "-" }}</td>
                <td v-if="columnVis.status">
                  <span :class="['att-chip','att-status', (it.status || 'none')]">{{ statusLabel(it.status) }}</span>
                </td>
                <td v-if="columnVis.teacher">{{ it.teacher_name || "—" }}</td>
                <td v-if="columnVis.note" class="small text-muted">{{ it.note || "—" }}</td>
                <td class="text-nowrap">
                  <button class="btn btn-sm btn-success me-1" :disabled="!canAct" @click="decideOne('approve', it)">
                    اعتماد
                  </button>
                  <button class="btn btn-sm btn-danger me-1" :disabled="!canAct" @click="decideOne('reject', it)">
                    رفض
                  </button>
                  <button class="btn btn-sm btn-warning" :disabled="!canAct" @click="openExcuseFor(it)">
                    بعذر
                  </button>
                </td>
              </tr>
              <tr v-if="!filteredItems.length">
                <td :colspan="2 + visibleColumnsCount" class="text-center text-muted">
                  لا توجد عناصر مطابقة
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        </div>
      </template>
    </div>

    <!-- Excuse Modal (lightweight, no external deps) -->
    <div v-if="excuseModal.open" class="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="excuseModalTitle">
      <div class="modal-card" @keydown.esc.prevent="closeExcuseModal">
        <div class="modal-header d-flex align-items-center gap-2">
          <h5 id="excuseModalTitle" class="m-0">اعتبار السجلات المحددة بعذر</h5>
          <span class="ms-auto"></span>
          <button class="btn btn-sm btn-outline-secondary" type="button" @click="closeExcuseModal" aria-label="إغلاق">✕</button>
        </div>
        <div class="modal-body">
          <div class="mb-2 small text-muted">سيتم تطبيق الإجراء على {{ selectedIds.size }} سجلًا.</div>
          <div class="mb-2">
            <label class="form-label">ملاحظة (اختياري)</label>
            <textarea class="form-control" rows="2" v-model.trim="excuseModal.comment" placeholder="سبب/ملاحظة"></textarea>
          </div>
          <div class="mb-2">
            <label class="form-label">رفع مستند إثبات (اختياري)</label>
            <input type="file" class="form-control" :accept="ACCEPT_TYPES" @change="onEvidenceChange" />
            <div class="form-text">الأنواع المسموحة: {{ ACCEPT_TYPES }} — الحد الأقصى: 5MB</div>
            <div v-if="excuseModal.error" class="text-danger small mt-1">{{ excuseModal.error }}</div>
          </div>
          <div class="mb-2">
            <label class="form-label">ملاحظة على الإثبات (اختياري)</label>
            <input type="text" class="form-control" v-model.trim="excuseModal.evidenceNote" placeholder="وصف قصير للمرفق" />
          </div>
        </div>
        <div class="modal-footer d-flex gap-2">
          <button class="btn btn-secondary" type="button" @click="closeExcuseModal">إلغاء</button>
          <button class="btn btn-warning" type="button" @click="confirmExcused" :disabled="excuseModal.busy">
            <Icon icon="solar:document-add-bold-duotone" />
            <span class="ms-1">تنفيذ بعذر</span>
          </button>
        </div>
      </div>
    </div>
  </section>
</template>
<script setup lang="ts">
import { onMounted, watch } from 'vue';
import { useWingContext } from '../../../shared/composables/useWingContext';
const { ensureLoaded, wingLabelFull, hasWingRole, isSuper, selectedWingId } = useWingContext();
import { tiles } from '../../../home/icon-tiles.config';
const tileMeta = computed(() => tiles.find(t => t.to === '/wing/approvals') || { title: 'طلبات الاعتماد', icon: 'solar:shield-check-bold-duotone', color: '#2e7d32' });
onMounted(() => { ensureLoaded(); });
import { ref, computed, onMounted } from "vue";
import { useRoute, useRouter } from 'vue-router';

// RBAC: allow actions only for wing supervisor or super admin
const canAct = computed(() => !!(hasWingRole?.value || isSuper?.value));

// Live region message for a11y
const liveMsg = ref<string>("");

// Router for URL state persistence
const route = useRoute();
const router = useRouter();

// Excuse modal state
const ACCEPT_TYPES = 'image/jpeg,image/png,image/webp,application/pdf';
const MAX_SIZE = 5 * 1024 * 1024; // 5MB
const excuseModal = ref<{ open: boolean; comment: string; evidenceFile: File | null; evidenceNote: string; error: string | null; busy: boolean }>({
  open: false,
  comment: '',
  evidenceFile: null,
  evidenceNote: '',
  error: null,
  busy: false,
});
import { Icon } from "@iconify/vue";
import DatePickerDMY from "../../../components/ui/DatePickerDMY.vue";
import DsButton from "../../../components/ui/DsButton.vue";
import DsBadge from "../../../components/ui/DsBadge.vue";
import StatusLegend from "../../../components/ui/StatusLegend.vue";
import WingPageHeader from "../../../components/ui/WingPageHeader.vue";
import WingWingPicker from "../../../components/ui/WingWingPicker.vue";
import {
  getWingPending,
  postWingDecide,
  getWingMe,
  getWingDailyAbsences,
  postWingSetExcused,
  getWingClasses,
} from "../../../shared/api/client";
import { useToast } from "vue-toastification";

const toast = useToast();
const items = ref<any[]>([]);
const dailyItems = ref<any[]>([]);
const dailyCounts = ref<{ excused: number; unexcused: number; none: number }>({ excused: 0, unexcused: 0, none: 0 });
const loading = ref(false);
const error = ref<string | null>(null);
const today = new Date().toISOString().slice(0, 10);
const dateStr = ref<string>(today);
// Display mode for the page: 'daily' general status vs 'period' pending queue
const mode = ref<'daily' | 'period'>('period');
import { useWingPrefs } from "../../../shared/composables/useWingPrefs";
const { approvals_default_mode: approvalsDefaultMode, default_date_mode: approvalsDateMode, apply_on_load: applyOnLoad } = useWingPrefs();
// Initialize mode from prefs if configured
if (applyOnLoad.value.approvals) {
  mode.value = approvalsDefaultMode.value;
  if (approvalsDateMode.value === 'today') {
    dateStr.value = today;
  } else if (approvalsDateMode.value === 'remember') {
    const prev = localStorage.getItem('wing_approvals.last_date');
    if (prev) dateStr.value = prev;
  }
}
const classes = ref<{ id: number; name?: string | null }[]>([]);
const selectedClassId = ref<number | null>(null);
const checkedList = ref<number[]>([]);
const selectedIds = computed(() => new Set(checkedList.value));

// Focus management: keep a stable focus target after actions
const refreshBtn = ref<any | null>(null);
async function focusRefresh() {
  try {
    await Promise.resolve();
    const el = (refreshBtn as any)?.value?.$el || (refreshBtn as any)?.value;
    // Try component root or inner native button
    const target: HTMLElement | null = (el?.querySelector && el.querySelector('button')) || el;
    if (target && typeof target.focus === 'function') target.focus();
  } catch {}
}

// Wing context
const wingId = ref<number | null>(null);
const meInfo = ref<any | null>(null);
const wingLabel = computed(() => {
  const info: any = meInfo.value || {};
  const names: string[] | undefined = info?.wings?.names;
  const ids: number[] | undefined = info?.wings?.ids;
  let label = "";
  if (names && names.length) {
    const raw = (names[0] || "").toString().trim();
    let m = raw.match(/الجناح\s*(\d+)\s*[-–]?\s*(.+)/);
    if (m) {
      const num = m[1];
      const name = (m[2] || "").trim();
      label = `${name} (${num})`;
    } else {
      m = raw.match(/(.+)\s*[-–]\s*الجناح\s*(\d+)/);
      if (m) {
        const name = (m[1] || "").trim();
        const num = m[2];
        label = `${name} (${num})`;
      } else {
        m = raw.match(/الجناح\s*(\d+)/);
        if (m) label = `(${m[1]})`;
        else label = raw;
      }
    }
  } else if (ids && ids.length) {
    label = `(${ids[0]})`;
  }
  return label;
});

// --- Filters, sorting, and column options ---
const PREF_KEY = "wing_approvals_prefs";

const statusOptions = [
  { value: "present", label: "حاضر" },
  { value: "absent", label: "غائب" },
  { value: "late", label: "متأخر" },
  { value: "excused", label: "إذن خروج" },
  { value: "runaway", label: "هروب" },
  { value: "left_early", label: "انصراف مبكر" },
];

const filters = ref<{ statuses: Set<string>; period: number | null; teacher: string; q: string }>({
  statuses: new Set<string>(),
  period: null,
  teacher: "",
  q: "",
});

// Column visibility and labels
const columnVis = ref<{
  student: boolean;
  class: boolean;
  period: boolean;
  status: boolean;
  teacher: boolean;
  note: boolean;
}>({
  student: true,
  class: true,
  period: true,
  status: true,
  teacher: true,
  note: true,
});
const columnLabels: Record<string, string> = {
  student: "الطالب",
  class: "الصف",
  period: "الحصة",
  status: "الحالة",
  teacher: "المعلم",
  note: "الملاحظة",
};

const sortKey = ref<"" | "student" | "class" | "period" | "status" | "teacher" | "note">("");
const sortDir = ref<"asc" | "desc">("asc");

const periods = computed<number[]>(() => {
  const set = new Set<number>();
  for (const it of items.value) {
    if (it.period_number != null) set.add(Number(it.period_number));
  }
  return Array.from(set).sort((a, b) => a - b);
});
const teachers = computed<string[]>(() => {
  const set = new Set<string>();
  for (const it of items.value) {
    if (it.teacher_name) set.add(String(it.teacher_name));
    else set.add("");
  }
  const arr = Array.from(set);
  // Put empty (unknown) at the end
  const nonEmpty = arr.filter((x) => x);
  nonEmpty.sort((a, b) => a.localeCompare(b, "ar"));
  const hasEmpty = arr.includes("");
  return hasEmpty ? [...nonEmpty, ""] : nonEmpty;
});

const filteredItems = computed<any[]>(() => {
  const f = filters.value;
  const q = (f.q || "").toLowerCase().trim();
  const hasStatuses = f.statuses && f.statuses.size > 0;
  return items.value.filter((it) => {
    if (hasStatuses && !f.statuses.has(it.status)) return false;
    if (f.period != null && Number(it.period_number) !== Number(f.period)) return false;
    if (f.teacher && (it.teacher_name || "") !== f.teacher) return false;
    if (q) {
      const hay =
        `${it.student_name || ""} ${it.note || ""} ${it.subject_name || ""}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
});

// Select-all state based on visible rows only
const allChecked = computed(
  () => filteredItems.value.length > 0 && checkedList.value.length === filteredItems.value.length
);

const filteredAndSorted = computed<any[]>(() => {
  const arr = filteredItems.value.slice();
  if (!sortKey.value) return arr;
  const dir = sortDir.value === "asc" ? 1 : -1;
  const key = sortKey.value;
  const val = (it: any) => {
    switch (key) {
      case "student":
        return it.student_name || String(it.student_id || "");
      case "class":
        return it.class_name || String(it.class_id || "");
      case "period":
        return it.period_number ?? 0;
      case "status":
        return statusLabel(it.status);
      case "teacher":
        return it.teacher_name || "";
      case "note":
        return it.note || "";
      default:
        return "";
    }
  };
  return arr.sort((a, b) => {
    const va = val(a);
    const vb = val(b);
    if (typeof va === "number" && typeof vb === "number") return (va - vb) * dir;
    const sa = "" + va;
    const sb = "" + vb;
    const cmp = sa.localeCompare(sb, "ar");
    return cmp * dir;
  });
});

const visibleColumnsCount = computed(() => Object.values(columnVis.value).filter(Boolean).length);

function toggleSort(k: "student" | "class" | "period" | "status" | "teacher" | "note") {
  if (sortKey.value === k) {
    sortDir.value = sortDir.value === "asc" ? "desc" : "asc";
  } else {
    sortKey.value = k;
    sortDir.value = "asc";
  }
  savePrefs();
}

function onStatusToggle(ev: Event, s: string) {
  const chk = (ev.target as HTMLInputElement).checked;
  if (chk) filters.value.statuses.add(s);
  else filters.value.statuses.delete(s);
  // trigger reactivity for Set
  filters.value = { ...filters.value, statuses: new Set(filters.value.statuses) } as any;
  savePrefs();
}

function resetFilters() {
  filters.value = { statuses: new Set<string>(), period: null, teacher: "", q: "" };
  sortKey.value = "";
  sortDir.value = "asc";
  savePrefs();
}

function savePrefs() {
  try {
    const data = {
      statuses: Array.from(filters.value.statuses),
      period: filters.value.period,
      teacher: filters.value.teacher,
      q: filters.value.q,
      columnVis: columnVis.value,
      sortKey: sortKey.value,
      sortDir: sortDir.value,
    };
    localStorage.setItem(PREF_KEY, JSON.stringify(data));
  } catch {}
}

function loadPrefs() {
  try {
    const raw = localStorage.getItem(PREF_KEY);
    if (!raw) return;
    const data = JSON.parse(raw);
    if (data.statuses) filters.value.statuses = new Set<string>(data.statuses);
    if (typeof data.period !== "undefined") filters.value.period = data.period;
    if (typeof data.teacher === "string") filters.value.teacher = data.teacher;
    if (typeof data.q === "string") filters.value.q = data.q;
    if (data.columnVis) columnVis.value = { ...columnVis.value, ...data.columnVis } as any;
    if (data.sortKey) sortKey.value = data.sortKey;
    if (data.sortDir) sortDir.value = data.sortDir;
  } catch {}
}

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
      return s || "—";
  }
}

async function load() {
  loading.value = true;
  error.value = null;
  try {
    const params: any = { date: dateStr.value };
    if (selectedClassId.value) params.class_id = selectedClassId.value;
    if (selectedWingId?.value) params.wing_id = selectedWingId.value;
    if (mode.value === 'daily') {
      const res = await getWingDailyAbsences(params);
      dailyItems.value = res.items || [];
      dailyCounts.value = res.counts || { excused: 0, unexcused: 0, none: 0 };
      liveMsg.value = `عدد الطلبة اليوم — بدون عذر: ${dailyCounts.value.unexcused}, بعذر: ${dailyCounts.value.excused}, غير محسوب: ${dailyCounts.value.none}`;
      // derive classes from daily items when needed
      if (!classes.value.length && Array.isArray(res.items)) {
        const map = new Map<number, { id: number; name?: string | null }>();
        for (const it of res.items) {
          if (it.class_id && !map.has(it.class_id))
            map.set(it.class_id, { id: it.class_id, name: it.class_name });
        }
        classes.value = Array.from(map.values()).sort((a, b) =>
          ("" + (a.name || a.id)).localeCompare("" + (b.name || b.id), "ar")
        );
      }
    } else {
      const res = await getWingPending(params);
      items.value = res.items || [];
      checkedList.value = [];
      liveMsg.value = `العناصر المعلقة المعروضة: ${items.value.length}`;
      // If classes not yet loaded from timetable, derive available classes from items (fallback)
      if (!classes.value.length && Array.isArray(res.items)) {
        const map = new Map<number, { id: number; name?: string | null }>();
        for (const it of res.items) {
          if (it.class_id && !map.has(it.class_id))
            map.set(it.class_id, { id: it.class_id, name: it.class_name });
        }
        classes.value = Array.from(map.values()).sort((a, b) =>
          ("" + (a.name || a.id)).localeCompare("" + (b.name || b.id), "ar")
        );
      }
    }
  } catch (e: any) {
    const msg = e?.response?.data?.detail || (mode.value==='daily' ? 'تعذر تحميل الحالة اليومية' : 'تعذر تحميل الطلبات');
    error.value = msg;
    liveMsg.value = `خطأ: ${msg}`;
    try { toast.error(msg); } catch {}
  } finally {
    loading.value = false;
  }
}

function toggleAll(ev: Event) {
  const chk = (ev.target as HTMLInputElement).checked;
  const ids = filteredItems.value.map((it) => it.id);
  checkedList.value = chk ? ids : [];
}

function openExcuseModal() {
  if (!selectedIds.value.size || !canAct.value) return;
  excuseModal.value.open = true;
  excuseModal.value.comment = '';
  excuseModal.value.evidenceFile = null;
  excuseModal.value.evidenceNote = '';
  excuseModal.value.error = null;
}
function closeExcuseModal() {
  excuseModal.value.open = false;
}
function onEvidenceChange(ev: Event) {
  const input = ev.target as HTMLInputElement;
  const file = input?.files && input.files[0] ? input.files[0] : null;
  excuseModal.value.error = null;
  if (!file) { excuseModal.value.evidenceFile = null; return; }
  if (file.size > MAX_SIZE) {
    excuseModal.value.error = `حجم الملف يتجاوز 5MB (الحجم الحالي ${(file.size/1024/1024).toFixed(2)}MB)`;
    excuseModal.value.evidenceFile = null;
    return;
  }
  const okTypes = ACCEPT_TYPES.split(',');
  if (okTypes.length && !okTypes.includes(file.type)) {
    excuseModal.value.error = 'نوع الملف غير مسموح';
    excuseModal.value.evidenceFile = null;
    return;
  }
  excuseModal.value.evidenceFile = file;
}
async function confirmExcused() {
  if (!selectedIds.value.size) return;
  excuseModal.value.busy = true;
  try {
    const ids = Array.from(selectedIds.value);
    const payload: any = { ids, comment: excuseModal.value.comment };
    if (excuseModal.value.evidenceFile) payload.evidenceFile = excuseModal.value.evidenceFile;
    if (excuseModal.value.evidenceNote) payload.evidenceNote = excuseModal.value.evidenceNote;
    const res = await postWingSetExcused(payload);
    const successMsg = `تم اعتبار ${res.updated} سجلات بعذر`;
    liveMsg.value = successMsg;
    try { toast.success(successMsg, { autoClose: 2500 }); } catch {}
    excuseModal.value.open = false;
    // Partial refresh: in period mode, remove affected rows locally
    if (mode.value === 'period') {
      const idSet = new Set(ids);
      items.value = items.value.filter((it) => !idSet.has(it.id));
      checkedList.value = checkedList.value.filter((id) => !idSet.has(id));
    } else {
      await load();
    }
    await focusRefresh();
  } catch (e: any) {
    const msg = e?.response?.data?.detail || e?.message || 'فشل تعيين بعذر';
    excuseModal.value.error = msg;
    liveMsg.value = `خطأ: ${msg}`;
    try { toast.error(msg); } catch {}
  } finally {
    excuseModal.value.busy = false;
  }
}

async function decide(action: "approve" | "reject") {
  if (!selectedIds.value.size || !canAct.value) return;
  const comment = action === "reject" ? prompt("سبب الرفض (اختياري):") || "" : "";
  try {
    const ids = Array.from(selectedIds.value);
    const res = await postWingDecide({ action, ids, comment });
    const msg = action === "approve" ? `تم اعتماد ${res.updated} عنصرًا` : `تم رفض ${res.updated} عنصرًا`;
    liveMsg.value = msg;
    try { toast.success(msg, { autoClose: 2500 }); } catch {}
    // Partial refresh in period mode: remove affected rows locally
    if (mode.value === 'period') {
      const idSet = new Set(ids);
      items.value = items.value.filter((it) => !idSet.has(it.id));
      checkedList.value = checkedList.value.filter((id) => !idSet.has(id));
    } else {
      await load();
    }
  } catch (e: any) {
    const emsg = e?.response?.data?.detail || "فشل تنفيذ العملية";
    liveMsg.value = `خطأ: ${emsg}`;
    try { toast.error(emsg); } catch {}
  } finally {
    await focusRefresh();
  }
}

// Per-row quick actions
async function decideOne(action: "approve" | "reject", it: any) {
  if (!canAct.value || !it?.id) return;
  const comment = action === "reject" ? prompt("سبب الرفض (اختياري):") || "" : "";
  try {
    const res = await postWingDecide({ action, ids: [it.id], comment });
    const msg = action === "approve" ? `تم اعتماد عنصر واحد` : `تم رفض عنصر واحد`;
    liveMsg.value = msg;
    try { toast.success(msg, { autoClose: 2000 }); } catch {}
    if (mode.value === 'period') {
      items.value = items.value.filter((row) => row.id !== it.id);
      checkedList.value = checkedList.value.filter((id) => id !== it.id);
    } else {
      await load();
    }
  } catch (e: any) {
    const emsg = e?.response?.data?.detail || "فشل تنفيذ العملية";
    liveMsg.value = `خطأ: ${emsg}`;
    try { toast.error(emsg); } catch {}
  } finally {
    await focusRefresh();
  }
}

function openExcuseFor(it: any) {
  if (!canAct.value || !it?.id) return;
  // Reuse bulk modal logic by setting selection to the single row
  checkedList.value = [it.id];
  openExcuseModal();
}

async function loadWing() {
  try {
    const me = await getWingMe();
    meInfo.value = me;
    const ids: number[] | undefined = (me as any)?.wings?.ids;
    wingId.value = Array.isArray(ids) && ids.length ? ids[0] : null;
  } catch {}
}

async function loadWingClasses() {
  classes.value = [];
  try {
    // Use wing-scoped endpoint to ensure only the supervisor's wing classes are listed
    const paramsWing: any = {};
    if (selectedWingId?.value) paramsWing.wing_id = selectedWingId.value;
    const res = await getWingClasses(paramsWing);
    const items = (res?.items || []).map((c: any) => ({ id: c.id, name: c.name }));
    classes.value = items.sort((a: any, b: any) => ("" + (a.name || a.id)).localeCompare("" + (b.name || b.id), "ar"));
  } catch {
    // keep empty on failure; dropdown will show "كل الصفوف"
  }
}

function onDateChange() {
  // Rebuild classes for the new date (timetable may change per day)
  loadWingClasses().then(() => load());
}

onMounted(async () => {
  loadPrefs();
  // Restore state from URL query (mode, class)
  try {
    const q: any = route.query || {};
    const m = (q.mode || '').toString();
    if (m === 'daily' || m === 'period') mode.value = m as any;
    const cls = q.class != null ? Number(q.class) : NaN;
    if (!Number.isNaN(cls) && cls > 0) selectedClassId.value = cls;
  } catch {}
  await loadWing();
  await loadWingClasses();
  await load();
});

// Persist state to URL when mode/class changes
watch([mode, selectedClassId], () => {
  try {
    const q = { ...route.query } as any;
    q.mode = mode.value;
    q.class = selectedClassId.value || '';
    router.replace({ query: q });
  } catch {}
});
</script>
<style scoped>
.header-icon {
  font-size: 22px;
}
.table-card {
  margin-top: 0.5rem;
}
/* Use global maroon header-bar styles from maronia.css (.header-bar.frame) */
.wing-title {
  color: #6a1b1b;
  font-weight: 700;
  font-size: 1.15rem;
}
.modal-backdrop{position:fixed;inset:0;background:rgba(0,0,0,.4);z-index:1050;display:flex;align-items:center;justify-content:center;padding:1rem}
.modal-card{background:#fff;border-radius:8px;min-width:min(90vw,520px);max-width:95vw;box-shadow:0 10px 30px rgba(0,0,0,.2)}
.modal-header,.modal-footer{padding:.5rem .75rem;border-bottom:1px solid #eee}
.modal-footer{border-top:1px solid #eee;border-bottom:0;justify-content:flex-end}
.modal-body{padding:.75rem}
</style>