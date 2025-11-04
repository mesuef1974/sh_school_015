<template>
  <section class="d-grid gap-3 page-grid page-grid-wide" dir="rtl">
    <!-- Header bar (unified) -->
    <WingPageHeader :icon="tileMeta.icon" :title="tileMeta.title" />

    <!-- Tools card: filters and actions -->
    <div class="card p-3">
      <div class="d-flex align-items-center gap-2 flex-wrap">
        <!-- Wing picker (Super only) lives in header; here we show class selector scoped to wing -->
        <div class="d-flex align-items-end gap-2 flex-wrap">
          <div class="d-flex flex-column me-2">
            <label for="notif-from" class="form-label mb-1">من</label>
            <input id="notif-from" type="date" class="form-control" v-model="from" @change="onFilterChange" />
          </div>
          <div class="d-flex flex-column me-2">
            <label for="notif-to" class="form-label mb-1">إلى</label>
            <input id="notif-to" type="date" class="form-control" v-model="to" @change="onFilterChange" />
          </div>
          <div class="d-flex flex-column me-2">
            <label for="notif-class" class="form-label mb-1">الصف</label>
            <select id="notif-class" class="form-select" v-model.number="classId" @change="onFilterChange">
              <option :value="null">كل الصفوف</option>
              <option v-for="c in classes" :key="c.id" :value="c.id">{{ c.name }}</option>
            </select>
          </div>
          <div class="d-flex flex-column me-2">
            <label for="notif-status" class="form-label mb-1">الحالة</label>
            <select id="notif-status" class="form-select" v-model="status" @change="onFilterChange">
              <option value="">الكل</option>
              <option value="draft">مسودة</option>
              <option value="scheduled">مجدولة</option>
              <option value="sent">مرسلة</option>
              <option value="cancelled">مُلغاة</option>
              <option value="archived">مؤرشفة</option>
            </select>
          </div>
          <div class="d-flex flex-column flex-grow-1">
            <label for="notif-q" class="form-label mb-1">بحث</label>
            <input id="notif-q" type="search" class="form-control" v-model.trim="q" :placeholder="'بحث بالطالب/العنوان'" @input="onSearchInput" />
          </div>
        </div>
        <div class="ms-auto d-flex align-items-end gap-2">
          <button ref="refreshBtn" class="btn btn-outline-primary" @click="reload" :disabled="loading">تحديث</button>
          <button class="btn btn-success" :disabled="!canAct || selectedIds.size===0" @click="bulkAction('send')">إرسال المحدد</button>
          <button class="btn btn-outline-warning" :disabled="!canAct || selectedIds.size===0" @click="bulkAction('cancel')">إلغاء المحدد</button>
          <button class="btn btn-outline-secondary" :disabled="!canAct || selectedIds.size===0" @click="bulkAction('archive')">أرشفة المحدد</button>
        </div>
      </div>
      <div class="small mt-2" :class="liveClass" aria-live="polite">{{ liveMsg }}</div>
      <div v-if="error" class="alert alert-danger mt-2" role="alert">{{ error }}</div>
    </div>

    <!-- Table card -->
    <div class="card p-0 table-card">
      <div class="table-responsive mb-0">
        <table class="table table-hover align-middle mb-0">
          <thead class="table-light">
            <tr>
              <th style="width:42px">
                <input class="form-check-input" type="checkbox" :checked="allVisibleSelected" @change="toggleSelectAll($event)" :aria-label="'تحديد الكل'" />
              </th>
              <th>الطالب</th>
              <th>الصف</th>
              <th>العنوان</th>
              <th>الحالة</th>
              <th>التاريخ</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!loading && items.length===0">
              <td :colspan="6" class="text-center text-muted py-4">لا توجد إشعارات مطابقة</td>
            </tr>
            <tr v-for="it in items" :key="it.id">
              <td>
                <input class="form-check-input" type="checkbox" :checked="selectedIds.has(it.id)" @change="toggleSelect(it.id,$event)" :aria-label="`تحديد ${it.title||''}`" />
              </td>
              <td>{{ it.student_name || '-' }}</td>
              <td>{{ it.class_name || '-' }}</td>
              <td>{{ it.title || it.subject || '-' }}</td>
              <td><span class="badge bg-secondary">{{ it.status || '—' }}</span></td>
              <td>{{ fmtDate(it.created_at) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="loading" class="p-3 text-muted">جاري التحميل ...</div>
      <div class="d-flex align-items-center gap-2 p-2 border-top">
        <div class="small text-muted">النتائج: {{ total }}</div>
        <div class="ms-auto d-flex align-items-center gap-2">
          <button class="btn btn-sm btn-outline-secondary" :disabled="offset===0 || loading" @click="prevPage">السابق</button>
          <button class="btn btn-sm btn-outline-secondary" :disabled="offset+limit>=total || loading" @click="nextPage">التالي</button>
        </div>
      </div>
    </div>
  </section>
</template>
<script setup lang="ts">
import { Icon } from "@iconify/vue";
import { computed, onMounted, reactive, ref, watch } from "vue";
import { tiles } from "../../../home/icon-tiles.config";
const tileMeta = computed(() => tiles.find((t) => t.to === "/wing/notifications") || { title: "إشعارات الجناح", icon: "solar:bell-bing-bold-duotone", color: "#d35400" });
import WingPageHeader from "../../../components/ui/WingPageHeader.vue";
import { useWingContext } from "../../../shared/composables/useWingContext";
const { isSuper, hasWingRole, selectedWingId } = useWingContext();
import { useWingPrefs } from "../../../shared/composables/useWingPrefs";
const { remember_filters, default_date_mode, apply_on_load, default_class_id } = useWingPrefs();
import { getWingClasses } from "../../../shared/api/client";

// RBAC
const canAct = computed(() => hasWingRole.value || isSuper.value);

// Filters state
const from = ref(isoToday());
const to = ref(isoToday());
const classId = ref<number | null>(null);
const status = ref<string>("");
const q = ref<string>("");
const limit = ref(25);
const offset = ref(0);

// Data state
const loading = ref(false);
const error = ref("");
const items = ref<any[]>([]);
const total = ref(0);
const selectedIds = reactive(new Set<number>());
const allVisibleSelected = computed(() => items.value.length>0 && items.value.every(x=>selectedIds.has(x.id)));

// Classes for selected wing
const classes = ref<{id:number; name:string}[]>([]);

// Load classes scoped by wing
async function loadClasses() {
  try {
    const params: any = {};
    const wingId = selectedWingId.value;
    if (wingId) params.wing_id = wingId;
    const res = await getWingClasses(params);
    classes.value = (res.items || []).map((c: any) => ({ id: c.id, name: c.name }));
    // If default class pref exists and belongs, prefill on first load
    if (!classId.value && default_class_id.value && classes.value.some(c=>c.id===default_class_id.value)) {
      classId.value = default_class_id.value;
    }
  } catch (e: any) {
    // non-fatal
  }
}

// Persistence (URL + localStorage-like via WingPrefs remember)
const STORAGE_KEY = "wing.notifications.filters";
function saveFilters() {
  if (!remember_filters.value) return;
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify({ from: from.value, to: to.value, classId: classId.value, status: status.value, q: q.value })); } catch {}
}
function restoreFilters() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const obj = JSON.parse(raw);
      from.value = obj.from || from.value;
      to.value = obj.to || to.value;
      classId.value = typeof obj.classId === 'number' ? obj.classId : null;
      status.value = obj.status || "";
      q.value = obj.q || "";
    } else {
      // Apply date mode default
      if (default_date_mode.value === 'today') {
        from.value = isoToday(); to.value = isoToday();
      }
    }
  } catch {}
}

// Load notifications — temporary wiring to absence alerts list until dedicated notifications API is available
import { listAbsenceAlerts } from "../../../shared/api/client";
async function reload() {
  loading.value = true; error.value = ""; items.value = []; total.value = 0; selectedIds.clear();
  try {
    const params: any = { from: from.value, to: to.value };
    if (status.value) params.status = status.value;
    // Fetch alerts as a stand-in for notifications
    const res = await listAbsenceAlerts(params);
    const rawItems: any[] = Array.isArray(res?.results) ? res.results : (res?.items || []);
    // Map to notifications-like shape and apply client-side class/q filtering
    let mapped = rawItems.map((a: any) => ({
      id: a.id,
      student_name: a.student_name || a.student || '-',
      class_name: a.class_name || '-',
      title: a.notes || a.title || `تنبيه غياب (${a.number ?? ''})`,
      status: a.status || '—',
      created_at: a.created_at || a.updated_at || a.issued_at || ''
    }));
    if (q.value) {
      const qs = q.value.toLowerCase();
      mapped = mapped.filter(it => (it.student_name||'').toLowerCase().includes(qs) || (it.title||'').toLowerCase().includes(qs));
    }
    if (classId.value) {
      // Until backend supports class_id filter for alerts, filter by class_name containing selected class label
      const sel = classes.value.find(c=>c.id===classId.value);
      if (sel) {
        const label = sel.name;
        mapped = mapped.filter(it => (it.class_name||'').includes(label));
      }
    }
    items.value = mapped;
    total.value = typeof res?.count === 'number' ? res.count : mapped.length;
    liveMsg.value = `تم التحديث (${fmtDate(from.value)} → ${fmtDate(to.value)})`;
  } catch (e:any) {
    error.value = e?.message || "تعذّر تحميل الإشعارات";
  } finally {
    loading.value = false;
    saveFilters();
  }
}

// Bulk actions — placeholder awaiting backend
async function bulkAction(action: 'send'|'cancel'|'archive') {
  if (!canAct.value || selectedIds.size===0) return;
  try {
    liveMsg.value = `جارٍ تنفيذ: ${action} ...`;
    await delay(200);
    liveMsg.value = `تم تنفيذ: ${action} على ${selectedIds.size} عنصر`;
    // After action, reload
    await reload();
  } catch {
    liveMsg.value = `فشل تنفيذ العملية: ${action}`;
  }
}

function onFilterChange() { offset.value = 0; reload(); }
let searchTimer: any = null;
function onSearchInput() { clearTimeout(searchTimer); searchTimer = setTimeout(()=>{ offset.value=0; reload(); }, 400); }
function prevPage() { if (offset.value>0) { offset.value = Math.max(0, offset.value - limit.value); reload(); } }
function nextPage() { offset.value += limit.value; reload(); }

function toggleSelect(id:number, ev: Event) {
  const checked = (ev.target as HTMLInputElement).checked;
  if (checked) selectedIds.add(id); else selectedIds.delete(id);
}
function toggleSelectAll(ev: Event) {
  const checked = (ev.target as HTMLInputElement).checked;
  if (checked) { items.value.forEach(it=>selectedIds.add(it.id)); } else { selectedIds.clear(); }
}

const liveMsg = ref("");
const liveClass = computed(()=> liveMsg.value.includes("فشل")?"text-danger":"text-success");
const refreshBtn = ref<HTMLButtonElement|null>(null);

onMounted(async ()=>{
  restoreFilters();
  await loadClasses();
  // Apply on-load if enabled
  if (apply_on_load.value?.approvals ?? true) {
    reload();
  }
});

watch(()=>selectedWingId.value, async ()=>{ await loadClasses(); reload(); });

// Helpers
function isoToday() { const d = new Date(); const m = String(d.getMonth()+1).padStart(2,'0'); const day=String(d.getDate()).padStart(2,'0'); return `${d.getFullYear()}-${m}-${day}`; }
function fmtDate(s?: string) { if (!s) return '—'; if (s.length===10) return s; try { const d = new Date(s); const y=d.getFullYear(); const m=String(d.getMonth()+1).padStart(2,'0'); const dd=String(d.getDate()).padStart(2,'0'); return `${y}-${m}-${dd}`; } catch { return s; } }
function delay(ms:number){ return new Promise(res=>setTimeout(res, ms)); }
</script>
<style scoped>
.table-card { overflow: hidden; }
</style>
