<template>
  <section class="d-grid gap-3 page-grid page-grid-wide" dir="rtl">
    <!-- Unified header -->
    <WingPageHeader :icon="tileMeta.icon" :title="tileMeta.title" :color="tileMeta.color">
          <template #actions>
            <WingWingPicker id="pick-classes-wing" />
          </template>
        </WingPageHeader>

    <!-- Toolbar card: global student search -->
    <div class="auto-card p-2 d-flex align-items-center gap-2 flex-wrap" role="search" aria-label="بحث عن طالب">
      <div class="input-group w-auto">
        <input
          v-model.trim="qStudents"
          @keyup.enter="reloadStudents"
          class="form-control form-control-sm"
          :placeholder="'ابحث بالاسم أو الرقم المدرسي على مستوى الجناح'"
        />
        <button class="btn btn-sm btn-outline-secondary" type="button" @click="reloadStudents" aria-label="بحث الطلبة">
          <Icon icon="solar:magnifer-bold-duotone" />
        </button>
      </div>
      <span class="small text-muted ms-auto" aria-live="polite">{{ limitedSorted.length }} نتيجة</span>
    </div>

    <!-- No wing assigned message -->
    <div v-if="!loadingCtx && !hasWingRole && !isSuper" class="alert alert-warning">
      لا تملك صلاحية مشرف جناح، أو لم يُسند لك جناح بعد. يرجى التواصل مع الإدارة.
    </div>

    <div class="row g-3">
      <!-- Card: Classes list -->
      <div class="col-12 col-lg-5">
        <div id="classes-card" class="card h-100" :aria-busy="loadingClasses ? 'true' : 'false'">
          <div class="card-body">
            <div class="d-flex align-items-center gap-2 mb-2">
              <Icon icon="solar:buildings-3-bold-duotone" class="text-primary" width="22" height="22" />
              <h5 class="m-0">صفوف الجناح</h5>
              <span class="badge text-bg-secondary ms-auto" :aria-live="'polite'">{{ classes.length }}</span>
            </div>

            <div v-if="errorClasses" class="alert alert-danger d-flex align-items-center gap-2">
              <Icon icon="solar:danger-triangle-bold-duotone" />
              <span>{{ errorClasses }}</span>
              <button class="btn btn-sm btn-outline-light ms-auto" @click="reloadClasses">إعادة المحاولة</button>
            </div>

            <div v-if="loadingClasses" class="text-muted small">جاري تحميل الصفوف ...</div>
            <ul v-else class="list-group list-group-flush class-list" role="listbox" aria-label="قائمة الصفوف">
              <li
                v-for="c in classes"
                :key="c.id"
                class="list-group-item d-flex align-items-center gap-2 list-item-hover"
                :class="{ active: c.id === selectedClassId }"
                role="option"
                :aria-selected="c.id === selectedClassId ? 'true' : 'false'"
                tabindex="0"
                @click="selectClass(c.id)"
                @keydown.enter.prevent="selectClass(c.id)"
                @keydown.space.prevent="selectClass(c.id)"
              >
                <Icon icon="solar:bookmark-square-bold-duotone" class="text-info" />
                <div class="flex-fill">
                  <div class="fw-semibold">{{ c.name }}</div>
                  <div class="small text-muted">المرحلة: {{ c.grade ?? '-' }} | الشعبة: {{ c.section || '-' }}</div>
                </div>
                <span class="badge rounded-pill text-bg-light" :title="'عدد الطلبة'">{{ c.students_count ?? 0 }}</span>
              </li>
              <li v-if="!classes.length" class="list-group-item text-muted">لا توجد صفوف ضمن جناحك.</li>
            </ul>
          </div>
        </div>
      </div>

      <!-- Card: Students of selected class -->
      <div class="col-12 col-lg-7">
        <div id="students-card" class="card h-100" :aria-busy="loadingStudents ? 'true' : 'false'">
          <div class="card-body d-flex flex-column">
            <div class="d-flex align-items-center gap-2 mb-2">
              <Icon icon="solar:users-group-two-rounded-bold-duotone" class="text-success" width="22" height="22" />
              <h5 class="m-0">الطلبة</h5>
              <span class="badge text-bg-secondary ms-2" aria-live="polite">{{ limitedSorted.length }}</span>
              <span class="ms-auto"></span>
              <details class="me-2">
                <summary class="btn btn-sm btn-outline-primary">فلاتر</summary>
                <div class="dropdown-card p-2 mt-1 small">
                  <label class="form-check">
                    <input class="form-check-input" type="checkbox" v-model="filters.activeOnly" @change="savePrefs" />
                    <span class="form-check-label">نشط فقط</span>
                  </label>
                  <label class="form-check">
                    <input class="form-check-input" type="checkbox" v-model="filters.needsOnly" @change="savePrefs" />
                    <span class="form-check-label">يحتاج متابعة فقط</span>
                  </label>
                  <label class="form-check">
                    <input class="form-check-input" type="checkbox" v-model="filters.hasPhoneOnly" @change="savePrefs" />
                    <span class="form-check-label">لديه رقم ولي الأمر</span>
                  </label>
                  <div class="mt-2">حالة اليوم:</div>
                  <label class="form-check form-check-inline" v-for="s in dayStateOptions" :key="s.value">
                    <input class="form-check-input" type="checkbox" :value="s.value" @change="onDayStateToggle($event, s.value)" :checked="filters.dayStates.has(s.value)" />
                    <span class="form-check-label">{{ s.label }}</span>
                  </label>
                </div>
              </details>
              <button v-if="contact_actions_enabled" class="btn btn-sm btn-outline-secondary" type="button" @click="copyAllNumbers">نسخ كل الأرقام</button>
              <button v-if="enable_csv_buttons" class="btn btn-sm btn-outline-success" type="button" @click="exportCsv">تصدير CSV</button>
              <button v-if="enable_csv_buttons" class="btn btn-sm btn-outline-primary" type="button" @click="exportWord" aria-label="تصدير Word (قائمة الطلبة)">تصدير Word</button>
              <div class="w-100"></div>
              <PrintToolbar />
            </div>

            <!-- البحث في الأعلى يعمل على مستوى الجناح بالكامل؛ اختيار الصف للتنقّل البصري فقط ولا يقيّد النتائج. -->

            <div v-if="errorStudents" class="alert alert-danger d-flex align-items-center gap-2">
              <Icon icon="solar:danger-triangle-bold-duotone" />
              <span>{{ errorStudents }}</span>
              <button class="btn btn-sm btn-outline-light ms-auto" @click="reloadStudents">إعادة المحاولة</button>
            </div>

            <div v-if="loadingStudents" class="text-muted small">جاري تحميل الطلبة ...</div>

            <div v-else class="table-responsive flex-fill">
              <table class="table align-middle table-sm">
                <thead>
                  <tr>
                    <th scope="col">#</th>
                    <th scope="col" role="button" tabindex="0" :aria-sort="sortKey==='sid' ? (sortDir==='asc'?'ascending':'descending') : 'none'" @click="toggleSort('sid')" @keydown.enter.prevent="toggleSort('sid')" @keydown.space.prevent="toggleSort('sid')">الرقم المدرسي <span class="sort" v-if="sortKey==='sid'">{{ sortDir==='asc'?'▲':'▼' }}</span></th>
                    <th scope="col" role="button" tabindex="0" :aria-sort="sortKey==='name' ? (sortDir==='asc'?'ascending':'descending') : 'none'" @click="toggleSort('name')" @keydown.enter.prevent="toggleSort('name')" @keydown.space.prevent="toggleSort('name')">اسم الطالب <span class="sort" v-if="sortKey==='name'">{{ sortDir==='asc'?'▲':'▼' }}</span></th>
                    <th scope="col" role="button" tabindex="0" :aria-sort="sortKey==='class' ? (sortDir==='asc'?'ascending':'descending') : 'none'" @click="toggleSort('class')" @keydown.enter.prevent="toggleSort('class')" @keydown.space.prevent="toggleSort('class')">الصف <span class="sort" v-if="sortKey==='class'">{{ sortDir==='asc'?'▲':'▼' }}</span></th>
                    <th v-if="colVis.parent" scope="col">ولي الأمر</th>
                    <th v-if="phoneColShown" scope="col">أرقام التواصل</th>
                    <th v-if="colVis.day" scope="col" role="button" tabindex="0" :aria-sort="sortKey==='day' ? (sortDir==='asc'?'ascending':'descending') : 'none'" @click="toggleSort('day')" @keydown.enter.prevent="toggleSort('day')" @keydown.space.prevent="toggleSort('day')">حالة اليوم <span class="sort" v-if="sortKey==='day'">{{ sortDir==='asc'?'▲':'▼' }}</span></th>
                    <th v-if="colVis.active" scope="col" role="button" tabindex="0" :aria-sort="sortKey==='active' ? (sortDir==='asc'?'ascending':'descending') : 'none'" @click="toggleSort('active')" @keydown.enter.prevent="toggleSort('active')" @keydown.space.prevent="toggleSort('active')">نشط</th>
                    <th v-if="colVis.needs" scope="col" role="button" tabindex="0" :aria-sort="sortKey==='needs' ? (sortDir==='asc'?'ascending':'descending') : 'none'" @click="toggleSort('needs')" @keydown.enter.prevent="toggleSort('needs')" @keydown.space.prevent="toggleSort('needs')">يحتاج</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(s, idx) in limitedSorted" :key="s.id">
                    <td class="text-muted">{{ idx + 1 }}</td>
                    <td><code>{{ s.sid }}</code></td>
                    <td>{{ s.full_name }}</td>
                    <td>{{ s.class_name || '-' }}</td>
                    <td v-if="colVis.parent">{{ s.parent_name || '-' }}</td>
                    <td v-if="phoneColShown">
                      <div class="small lh-sm">
                        <div v-if="colVis.parentPhone && s.parent_phone">ولي: <a :href="`tel:${s.parent_phone}`">{{ s.parent_phone }}</a></div>
                        <div v-if="colVis.extraPhone && s.extra_phone_no">إضافي: <a :href="`tel:${s.extra_phone_no}`">{{ s.extra_phone_no }}</a></div>
                        <div v-if="s.phone_no" class="text-muted">طالب: <a :href="`tel:${s.phone_no}`">{{ s.phone_no }}</a></div>
                        <div v-if="!s.parent_phone && !s.extra_phone_no && !s.phone_no" class="text-muted">-</div>
                      </div>
                    </td>
                    <td v-if="colVis.day">
                      <span v-if="dailyById[s.id]" class="att-chip day-state" :class="dailyById[s.id].state">
                        {{ humanState(dailyById[s.id].state) }}
                      </span>
                      <div v-if="dailyById[s.id]" class="small text-muted">
                        <span v-if="dailyById[s.id].p1">ح1: {{ shortStatus(dailyById[s.id].p1) }}</span>
                        <span v-if="dailyById[s.id].p2" class="ms-2">ح2: {{ shortStatus(dailyById[s.id].p2) }}</span>
                      </div>
                      <span v-else class="text-muted small">—</span>
                    </td>
                    <td v-if="colVis.active">
                      <span :class="['badge', s.active ? 'text-bg-success' : 'text-bg-secondary']">{{ s.active ? 'نعم' : 'لا' }}</span>
                    </td>
                    <td v-if="colVis.needs">
                      <span :class="['badge', s.needs ? 'text-bg-warning' : 'text-bg-secondary']">{{ s.needs ? 'نعم' : 'لا' }}</span>
                    </td>
                  </tr>
                  <tr v-if="!filteredAndSorted.length">
                    <td :colspan="tableColCount" class="text-muted">لا يوجد طلبة مطابقة للبحث.</td>
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
import { Icon } from "@iconify/vue";
import { computed, onMounted, ref, watch } from "vue";
// @ts-ignore access global print manager
const $print = (window as any).printManager;
import { tiles } from "../../../home/icon-tiles.config";
import { useWingContext } from "../../../shared/composables/useWingContext";
import WingPageHeader from "../../../components/ui/WingPageHeader.vue";
import WingWingPicker from "../../../components/ui/WingWingPicker.vue";
import { getWingClasses, getWingStudents, getWingDailyAbsences, downloadWingStudentsWord } from "../../../shared/api/client";
import { useWingPrefs } from "../../../shared/composables/useWingPrefs";

// Wing settings (v2) integration
const { students_search_limit, students_columns_visibility, students_export_columns, contact_actions_enabled, remember_filters, enable_csv_buttons, csv_include_headers } = useWingPrefs();

const tileMeta = computed(() =>
  tiles.find((t) => t.to === "/wing/classes") || { title: "صفوف وطلبة", icon: "solar:home-2-bold-duotone", color: "#34495e" }
);
const { wingLabelFull, hasWingRole, isSuper, ensureLoaded, loading: loadingCtx, selectedWingId } = useWingContext();

// Classes state
const classes = ref<{ id: number; name?: string; grade?: number; section?: string; students_count?: number }[]>([]);
const qClasses = ref("");
const loadingClasses = ref(false);
const errorClasses = ref<string | null>(null);

// Students state
const selectedClassId = ref<number | null>(null);
const students = ref<{ id: number; sid?: string; full_name?: string; class_name?: string; parent_name?: string | null; parent_phone?: string | null; extra_phone_no?: string | null; phone_no?: string | null; active?: boolean | null; needs?: boolean | null }[]>([]);
const qStudents = ref("");
const loadingStudents = ref(false);
const errorStudents = ref<string | null>(null);
// Daily absence map for today keyed by student_id
const dailyById = ref<Record<number, { state: "excused" | "unexcused" | "none"; p1?: string | null; p2?: string | null }>>({});

// Preferences and filtering/sorting state
const PREF_KEY = 'wing_classes_prefs';
const filters = ref<{ activeOnly: boolean; needsOnly: boolean; hasPhoneOnly: boolean; dayStates: Set<string> }>(
  { activeOnly: false, needsOnly: false, hasPhoneOnly: false, dayStates: new Set<string>() }
);
const dayStateOptions = [
  { value: 'unexcused', label: 'بدون عذر' },
  { value: 'excused', label: 'بعذر' },
  { value: 'none', label: 'غير محسوب' },
];
const sortKey = ref<'sid'|'name'|'class'|'day'|'active'|'needs'>('name');
const sortDir = ref<'asc'|'desc'>('asc');

function toggleSort(k: 'sid'|'name'|'class'|'day'|'active'|'needs') {
  if (sortKey.value === k) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc';
  } else {
    sortKey.value = k;
    sortDir.value = 'asc';
  }
  savePrefs();
}

function savePrefs() {
  if (!remember_filters.value) return;
  try {
    const payload = {
      activeOnly: filters.value.activeOnly,
      needsOnly: filters.value.needsOnly,
      hasPhoneOnly: filters.value.hasPhoneOnly,
      dayStates: Array.from(filters.value.dayStates.values()),
      sortKey: sortKey.value,
      sortDir: sortDir.value,
    };
    localStorage.setItem(PREF_KEY, JSON.stringify(payload));
  } catch {}
}
function loadPrefs() {
  if (!remember_filters.value) return;
  try {
    const raw = localStorage.getItem(PREF_KEY);
    if (!raw) return;
    const obj = JSON.parse(raw);
    filters.value.activeOnly = !!obj.activeOnly;
    filters.value.needsOnly = !!obj.needsOnly;
    filters.value.hasPhoneOnly = !!obj.hasPhoneOnly;
    const ds = new Set<string>();
    if (Array.isArray(obj.dayStates)) obj.dayStates.forEach((v: any) => ds.add(String(v)));
    filters.value.dayStates = ds;
    if (obj.sortKey) sortKey.value = obj.sortKey;
    if (obj.sortDir) sortDir.value = obj.sortDir;
  } catch {}
}
function onDayStateToggle(ev: Event, val: string) {
  const chk = (ev.target as HTMLInputElement).checked;
  const set = new Set(filters.value.dayStates);
  if (chk) set.add(val); else set.delete(val);
  filters.value.dayStates = set;
  savePrefs();
}

const filteredItems = computed(() => {
  let arr = students.value.slice();
  if (filters.value.activeOnly) arr = arr.filter(s => !!s.active);
  if (filters.value.needsOnly) arr = arr.filter(s => !!s.needs);
  if (filters.value.hasPhoneOnly) arr = arr.filter(s => !!(s.parent_phone && String(s.parent_phone).trim().length));
  if (filters.value.dayStates.size) {
    arr = arr.filter(s => {
      const d = (dailyById.value as any)[s.id];
      const st = d?.state || 'none';
      return filters.value.dayStates.has(st);
    });
  }
  return arr;
});

const filteredAndSorted = computed(() => {
  const arr = filteredItems.value.slice();
  const dir = sortDir.value === 'asc' ? 1 : -1;
  const dayWeight: Record<string, number> = { unexcused: 2, excused: 1, none: 0 };
  arr.sort((a, b) => {
    let av: any = null, bv: any = null;
    switch (sortKey.value) {
      case 'sid':
        av = a.sid || ''; bv = b.sid || ''; break;
      case 'name':
        av = a.full_name || ''; bv = b.full_name || ''; break;
      case 'class':
        av = a.class_name || ''; bv = b.class_name || ''; break;
      case 'day': {
        const da = (dailyById.value as any)[a.id]?.state || 'none';
        const db = (dailyById.value as any)[b.id]?.state || 'none';
        av = dayWeight[da] ?? -1; bv = dayWeight[db] ?? -1; break;
      }
      case 'active':
        av = a.active ? 1 : 0; bv = b.active ? 1 : 0; break;
      case 'needs':
        av = a.needs ? 1 : 0; bv = b.needs ? 1 : 0; break;
      default:
        av = 0; bv = 0;
    }
    if (typeof av === 'string' && typeof bv === 'string') {
      const cmp = av.localeCompare(bv, 'ar');
      return cmp * dir;
    }
    if (av < bv) return -1 * dir;
    if (av > bv) return 1 * dir;
    return 0;
  });
  return arr;
});

// Apply students_search_limit from Wing Settings
const limitedSorted = computed(() => filteredAndSorted.value.slice(0, Math.max(50, Math.min(2000, Number(students_search_limit.value || 300)))));

// Column visibility derived from Wing Settings
const colVis = computed(() => ({
  parent: !!students_columns_visibility.value.show_parent,
  parentPhone: !!students_columns_visibility.value.show_parent_phone,
  extraPhone: !!students_columns_visibility.value.show_extra_phone,
  day: !!students_columns_visibility.value.show_day_state,
  active: !!students_columns_visibility.value.show_active,
  needs: !!students_columns_visibility.value.show_needs,
}));
const phoneColShown = computed(() => colVis.value.parentPhone || colVis.value.extraPhone || !!contact_actions_enabled.value);
const tableColCount = computed(() => {
  // Always visible: index, sid, name, class
  let n = 4;
  if (colVis.value.parent) n += 1;
  if (phoneColShown.value) n += 1;
  if (colVis.value.day) n += 1;
  if (colVis.value.active) n += 1;
  if (colVis.value.needs) n += 1;
  return n;
});

function copyAllNumbers() {
  const nums: string[] = [];
  for (const s of limitedSorted.value) {
    if (s.parent_phone) nums.push(String(s.parent_phone).trim());
    if (s.extra_phone_no) nums.push(String(s.extra_phone_no).trim());
    if (s.phone_no) nums.push(String(s.phone_no).trim());
  }
  const unique = Array.from(new Set(nums.filter(Boolean)));
  const text = unique.join('\n');
  if (!text) { window.alert('لا توجد أرقام لنسخها'); return; }
  navigator.clipboard?.writeText(text).then(() => {
    try { window.alert(`تم نسخ ${unique.length} رقمًا إلى الحافظة`); } catch {}
  }).catch(() => {
    // Fallback: open a temporary textarea
    const ta = document.createElement('textarea');
    ta.value = text; document.body.appendChild(ta); ta.select();
    try { document.execCommand('copy'); } catch {}
    document.body.removeChild(ta);
    try { window.alert(`تم نسخ ${unique.length} رقمًا إلى الحافظة`); } catch {}
  });
}

function exportCsv() {
  // Build dynamic columns based on current visibility and export-only preferences
  const headers: string[] = [];
  const buildRow = (s: any) => {
    const d = (dailyById.value as any)[s.id] || {};
    const row: any[] = [];
    // Visual order in UI: index(#) is not exported
    // 1) sid (رقم)
    headers.length === 0 && headers.push('الرقم المدرسي');
    row.push(s.sid || '');
    // 2) full_name
    headers.length === 1 && headers.push('اسم الطالب');
    row.push(s.full_name || '');
    // 3) class_name
    headers.length === 2 && headers.push('الصف');
    row.push(s.class_name || '');
    // 4) parent (optional on-screen or export-only)
    if (colVis.value.parent || (students_export_columns.value as any).parent_name) {
      if (headers.indexOf('ولي الأمر') === -1) headers.push('ولي الأمر');
      row.push(s.parent_name || '');
    }
    // 5) phone columns. Export granular sub-columns depending on visibility or export-only flags.
    const ex = students_export_columns.value as any;
    if (phoneColShown.value || ex.parent_phone || ex.extra_phone_no || ex.phone_no) {
      // Parent phone
      if (colVis.value.parentPhone || contact_actions_enabled.value || ex.parent_phone) {
        if (headers.indexOf('هاتف ولي الأمر') === -1) headers.push('هاتف ولي الأمر');
        row.push(s.parent_phone || '');
      }
      // Extra phone
      if (colVis.value.extraPhone || contact_actions_enabled.value || ex.extra_phone_no) {
        if (headers.indexOf('هاتف إضافي') === -1) headers.push('هاتف إضافي');
        row.push(s.extra_phone_no || '');
      }
      // Student phone
      if (ex.phone_no) {
        if (headers.indexOf('هاتف الطالب') === -1) headers.push('هاتف الطالب');
        row.push(s.phone_no || '');
      }
    }
    // 6) day state (optional) — only on-screen control affects this column; not exposed as export-only for now
    if (colVis.value.day) {
      if (headers.indexOf('حالة اليوم') === -1) headers.push('حالة اليوم');
      row.push(d.state || '');
      if (headers.indexOf('ح1') === -1) headers.push('ح1');
      row.push(d.p1 || '');
      if (headers.indexOf('ح2') === -1) headers.push('ح2');
      row.push(d.p2 || '');
    }
    // 7) active (optional)
    if (colVis.value.active || ex.active) {
      if (headers.indexOf('نشط') === -1) headers.push('نشط');
      row.push((s.active ?? false) ? '1' : '0');
    }
    // 8) needs (optional)
    if (colVis.value.needs || ex.needs) {
      if (headers.indexOf('يحتاج') === -1) headers.push('يحتاج');
      row.push((s.needs ?? false) ? '1' : '0');
    }
    return row;
  };

  const rows: any[] = [];
  if (csv_include_headers.value) {
    // Build headers by probing the first row structure
    const probe = limitedSorted.value[0];
    if (probe) {
      buildRow(probe); // fills headers in order
    } else {
      // No data, but we can still include default minimal headers
      headers.push('الرقم المدرسي','اسم الطالب','الصف');
    }
  }
  for (const s of limitedSorted.value) {
    rows.push(buildRow(s));
  }
  const csv = rows
    .map(r => r.map((v: any) => {
      let s = String(v);
      if (/[,"\n]/.test(s)) s = '"' + s.replace(/"/g, '""') + '"';
      return s;
    }).join(','))
    .join('\n');
  const headerLine = csv_include_headers.value ? headers.map(h => {
    let s = String(h);
    if (/[,"\n]/.test(s)) s = '"' + s.replace(/"/g, '""') + '"';
    return s;
  }).join(',') + (rows.length ? '\n' : '') : '';
  const bom = '\uFEFF';
  const blob = new Blob([bom + headerLine + csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  const ts = new Date().toISOString().replace(/[:T]/g, '-').slice(0,19);
  a.href = url;
  a.download = `wing-students-${ts}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// Backend Word export (DOCX) to match current scope (wing-wide search or selected class)
async function exportWord() {
  const params: any = {};
  if (qStudents.value && qStudents.value.length > 0) {
    params.q = qStudents.value;
  } else if (selectedClassId.value) {
    params.class_id = selectedClassId.value;
  }
  if (selectedWingId?.value) params.wing_id = selectedWingId.value;

  // Build columns param to match currently visible columns + export-only configured columns
  // Backend accepts keys: sid, full_name, class_name, parent_name, parent_phone, extra_phone_no, phone_no, active, needs
  const keys: string[] = [];
  // Always include in order: sid, full_name, class_name
  keys.push('sid');
  keys.push('full_name');
  keys.push('class_name');

  const ex = students_export_columns.value as any;
  // Parent name
  if (colVis.value.parent || ex.parent_name) keys.push('parent_name');
  // Phone parts
  if (phoneColShown.value || ex.parent_phone || ex.extra_phone_no || ex.phone_no) {
    if (colVis.value.parentPhone || contact_actions_enabled.value || ex.parent_phone) keys.push('parent_phone');
    if (colVis.value.extraPhone || contact_actions_enabled.value || ex.extra_phone_no) keys.push('extra_phone_no');
    if (ex.phone_no) keys.push('phone_no');
  }
  // active / needs
  if (colVis.value.active || ex.active) keys.push('active');
  if (colVis.value.needs || ex.needs) keys.push('needs');

  // Note: day-state is not part of backend students export
  params.columns = Array.from(new Set(keys)).join(',');

  try {
    await downloadWingStudentsWord(params);
  } catch (e: any) {
    try { window.alert(e?.response?.data?.detail || e?.message || 'فشل تنزيل الملف'); } catch {}
  }
}

function todayIso(): string {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${dd}`;
}
function humanState(s: string) {
  if (s === "excused") return "بعذر";
  if (s === "unexcused") return "بدون عذر";
  return "غير محسوب";
}
function shortStatus(s: any) {
  if (!s) return "-";
  const v = String(s);
  if (v === "present") return "ح";
  if (v === "absent") return "غ";
  if (v === "late") return "ت";
  if (v === "excused") return "إ";
  return v;
}

async function reloadClasses() {
  loadingClasses.value = true;
  errorClasses.value = null;
  try {
    const params: any = { q: qClasses.value || undefined };
    if (selectedWingId?.value) params.wing_id = selectedWingId.value;
    const res = await getWingClasses(params);
    classes.value = res.items || [];
    // Preserve selection if still present; otherwise keep it null (search works wing-wide)
    if (selectedClassId.value && !classes.value.some((c) => c.id === selectedClassId.value)) {
      selectedClassId.value = null;
    }
  } catch (e: any) {
    errorClasses.value = e?.message || "فشل تحميل الصفوف";
  } finally {
    loadingClasses.value = false;
  }
}

function selectClass(classId: number) {
  selectedClassId.value = classId;
  // Load students for the selected class immediately (when no search query)
  // If there is an active search query, results remain wing-wide by design
  reloadStudents();
}

let lastAbort: AbortController | null = null;
async function reloadStudents() {
  // Cancel previous in-flight request if any
  if (lastAbort) {
    try { lastAbort.abort(); } catch {}
  }
  const ac = new AbortController();
  lastAbort = ac;
  loadingStudents.value = true;
  errorStudents.value = null;
  try {
    // If there is a search query, search wing-wide; otherwise, if a class is selected, fetch that class's students
    const params: { q?: string; class_id?: number; wing_id?: number } = {};
    if (selectedWingId?.value) params.wing_id = selectedWingId.value;
    if (qStudents.value && qStudents.value.length > 0) {
      params.q = qStudents.value;
    } else if (selectedClassId.value) {
      params.class_id = selectedClassId.value;
    }

    const res = await getWingStudents(params);
    if (ac.signal.aborted) return; // ignore result if aborted
    students.value = res.items || [];
    // Fetch today's daily absences and map by student_id, scoping to class if applicable for performance
    try {
      const dailyParams: { date: string; class_id?: number; wing_id?: number } = { date: todayIso() };
      if (selectedWingId?.value) (dailyParams as any).wing_id = selectedWingId.value;
      if (!params.q && params.class_id) dailyParams.class_id = params.class_id;
      const daily = await getWingDailyAbsences(dailyParams);
      if (ac.signal.aborted) return;
      const map: Record<number, any> = {};
      for (const it of daily.items || []) {
        map[it.student_id] = { state: it.state, p1: it.p1, p2: it.p2 };
      }
      dailyById.value = map as any;
    } catch (e) {
      if (ac.signal.aborted) return;
      dailyById.value = {} as any;
    }
  } catch (e: any) {
    if (ac.signal.aborted) return;
    errorStudents.value = e?.message || "فشل تحميل الطلبة";
  } finally {
    if (!ac.signal.aborted) loadingStudents.value = false;
  }
}

// Debounce search input
let debounceTimer: any = null;
watch(qStudents, (nv) => {
  if (debounceTimer) clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => reloadStudents(), 400);
});


onMounted(async () => {
  loadPrefs();
  await ensureLoaded();
  await reloadClasses();
});

// Reload when wing selection changes (super admin)
watch(selectedWingId, async () => {
  await reloadClasses();
  await reloadStudents();
});
</script>

<style scoped>
.header-icon { font-size: 22px; }
.list-item-hover { cursor: pointer; }
.list-group-item.active {
  background-color: rgba(13, 110, 253, 0.1); /* fallback subtle primary */
}
.class-list { max-height: 60vh; overflow: auto; }
</style>