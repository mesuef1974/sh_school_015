<template>
  <section class="d-grid gap-3 page-grid">
    <div class="auto-card p-3">
      <div class="d-flex align-items-center gap-2 mb-2 header-bar">
        <Icon icon="solar:shield-check-bold-duotone" class="header-icon" />
        <div>
          <div class="fw-bold">طلبات الاعتماد — مشرف الجناح</div>
          <div class="text-muted small">مراجعة واعتماد/رفض السجلات المرسلة من المعلمين</div>
        </div>
        <div class="flex-fill text-center wing-title" v-if="wingLabel">{{ wingLabel }}</div>
        <span class="ms-auto"></span>
        <input type="date" class="form-control w-auto" v-model="dateStr" @change="onDateChange" />
        <select class="form-select w-auto" v-model.number="selectedClassId" @change="load">
          <option :value="null">كل الصفوف</option>
          <option v-for="c in classes" :key="c.id" :value="c.id">
            {{ c.name || "صف #" + c.id }}
          </option>
        </select>
        <DsButton variant="primary" icon="solar:refresh-bold-duotone" @click="load">تحديث</DsButton>
      </div>

      <div v-if="loading" class="loader-line"></div>
      <template v-else>
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
            :disabled="!selectedIds.size"
            variant="success"
            icon="solar:check-circle-bold-duotone"
            @click="decide('approve')"
            >اعتماد المحدد</DsButton
          >
          <DsButton
            :disabled="!selectedIds.size"
            variant="danger"
            icon="solar:close-circle-bold-duotone"
            @click="decide('reject')"
            >رفض المحدد</DsButton
          >
        </div>
        <div class="table-responsive table-card">
          <table class="table table-hover align-middle">
            <thead>
              <tr>
                <th style="width: 36px">
                  <input type="checkbox" @change="toggleAll($event)" :checked="allChecked" />
                </th>
                <th v-if="columnVis.student" role="button" @click="toggleSort('student')">
                  الطالب
                  <span class="sort" v-if="sortKey === 'student'">{{
                    sortDir === "asc" ? "▲" : "▼"
                  }}</span>
                </th>
                <th v-if="columnVis.class" role="button" @click="toggleSort('class')">
                  الصف
                  <span class="sort" v-if="sortKey === 'class'">{{
                    sortDir === "asc" ? "▲" : "▼"
                  }}</span>
                </th>
                <th v-if="columnVis.period" role="button" @click="toggleSort('period')">
                  الحصة
                  <span class="sort" v-if="sortKey === 'period'">{{
                    sortDir === "asc" ? "▲" : "▼"
                  }}</span>
                </th>
                <th v-if="columnVis.status" role="button" @click="toggleSort('status')">
                  الحالة
                  <span class="sort" v-if="sortKey === 'status'">{{
                    sortDir === "asc" ? "▲" : "▼"
                  }}</span>
                </th>
                <th v-if="columnVis.teacher" role="button" @click="toggleSort('teacher')">
                  المعلم
                  <span class="sort" v-if="sortKey === 'teacher'">{{
                    sortDir === "asc" ? "▲" : "▼"
                  }}</span>
                </th>
                <th v-if="columnVis.note" role="button" @click="toggleSort('note')">
                  الملاحظة
                  <span class="sort" v-if="sortKey === 'note'">{{
                    sortDir === "asc" ? "▲" : "▼"
                  }}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="it in filteredAndSorted" :key="it.id">
                <td><input type="checkbox" :value="it.id" v-model="checkedList" /></td>
                <td v-if="columnVis.student">{{ it.student_name || "#" + it.student_id }}</td>
                <td v-if="columnVis.class">{{ it.class_name || "صف #" + (it.class_id || "") }}</td>
                <td v-if="columnVis.period">حصة {{ it.period_number || "-" }}</td>
                <td v-if="columnVis.status">
                  <span class="badge text-bg-secondary">{{ statusLabel(it.status) }}</span>
                </td>
                <td v-if="columnVis.teacher">{{ it.teacher_name || "—" }}</td>
                <td v-if="columnVis.note" class="small text-muted">{{ it.note || "—" }}</td>
              </tr>
              <tr v-if="!filteredItems.length">
                <td :colspan="1 + visibleColumnsCount" class="text-center text-muted">
                  لا توجد عناصر مطابقة
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
    </div>
  </section>
</template>
<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { Icon } from "@iconify/vue";
import DsButton from "../../../components/ui/DsButton.vue";
import DsBadge from "../../../components/ui/DsBadge.vue";
import {
  getWingPending,
  postWingDecide,
  getTeacherClasses,
  getWingMe,
  getWingTimetable,
} from "../../../shared/api/client";
import { useToast } from "vue-toastification";

const toast = useToast();
const items = ref<any[]>([]);
const loading = ref(false);
const today = new Date().toISOString().slice(0, 10);
const dateStr = ref<string>(today);
const classes = ref<{ id: number; name?: string | null }[]>([]);
const selectedClassId = ref<number | null>(null);
const checkedList = ref<number[]>([]);
const selectedIds = computed(() => new Set(checkedList.value));

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
  try {
    const params: any = { date: dateStr.value };
    if (selectedClassId.value) params.class_id = selectedClassId.value;
    const res = await getWingPending(params);
    items.value = res.items || [];
    checkedList.value = [];
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
  } catch (e: any) {
    try {
      toast.error(e?.response?.data?.detail || "تعذر تحميل الطلبات");
    } catch {}
  } finally {
    loading.value = false;
  }
}

function toggleAll(ev: Event) {
  const chk = (ev.target as HTMLInputElement).checked;
  const ids = filteredItems.value.map((it) => it.id);
  checkedList.value = chk ? ids : [];
}

async function decide(action: "approve" | "reject") {
  if (!selectedIds.value.size) return;
  const comment = action === "reject" ? prompt("سبب الرفض (اختياري):") || "" : "";
  try {
    const ids = Array.from(selectedIds.value);
    const res = await postWingDecide({ action, ids, comment });
    const msg =
      action === "approve" ? `تم اعتماد ${res.updated} عنصرًا` : `تم رفض ${res.updated} عنصرًا`;
    try {
      toast.success(msg, { autoClose: 2500 });
    } catch {}
    await load();
  } catch (e: any) {
    try {
      toast.error(e?.response?.data?.detail || "فشل تنفيذ العملية");
    } catch {}
  }
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
  // Prefer wing timetable daily for the selected date to get classes of this wing
  try {
    if (wingId.value) {
      const res: any = await getWingTimetable({
        mode: "daily",
        wing_id: wingId.value,
        date: dateStr.value,
      });
      const items = (res as any)?.items || [];
      const uniq = new Map<number, { id: number; name?: string | null }>();
      for (const it of items) {
        if (it.class_id && !uniq.has(it.class_id))
          uniq.set(it.class_id, { id: it.class_id, name: it.class_name });
      }
      classes.value = Array.from(uniq.values()).sort((a, b) =>
        ("" + (a.name || a.id)).localeCompare("" + (b.name || b.id), "ar")
      );
    }
  } catch {}
  // Fallback to teacher classes (will later be filtered implicitly by approvals load)
  if (!classes.value.length) {
    try {
      const res = await getTeacherClasses();
      classes.value = (res?.classes || []).sort((a: any, b: any) =>
        ("" + (a.name || a.id)).localeCompare("" + (b.name || b.id), "ar")
      );
    } catch {}
  }
}

function onDateChange() {
  // Rebuild classes for the new date (timetable may change per day)
  loadWingClasses().then(() => load());
}

onMounted(async () => {
  loadPrefs();
  await loadWing();
  await loadWingClasses();
  await load();
});
</script>
<style scoped>
.header-icon {
  font-size: 22px;
}
.table-card {
  margin-top: 0.5rem;
}
.header-bar {
  align-items: center;
}
.wing-title {
  color: #6a1b1b;
  font-weight: 700;
  font-size: 1.15rem;
}
</style>
