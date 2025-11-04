<template>
  <section class="d-grid gap-3 page-grid page-grid-wide" dir="rtl">
    <!-- Unified page header -->
    <WingPageHeader :icon="tileMeta.icon" :title="tileMeta.title" :color="tileMeta.color">
          <template #actions>
            <WingWingPicker id="pick-exits-wing" />
          </template>
        </WingPageHeader>

    <!-- Toolbar card with filters/actions -->
    <div class="auto-card p-3 d-flex align-items-center gap-2 flex-wrap no-print">
      <label class="visually-hidden" for="exit-date">التاريخ</label>
      <input id="exit-date" type="date" v-model="date" class="form-control form-control-sm w-auto" :aria-label="'التاريخ'" />

      <label class="visually-hidden" for="exit-class">تصفية حسب الصف</label>
      <select id="exit-class" v-model.number="classId" class="form-select form-select-sm w-auto" :aria-label="'تصفية حسب الصف'">
        <option :value="0">كل الصفوف</option>
        <option v-for="c in classes" :key="c.id" :value="c.id">{{ c.name }}</option>
      </select>

      <label class="visually-hidden" for="exit-status">الحالة</label>
      <select id="exit-status" v-model="status" class="form-select form-select-sm w-auto" :aria-label="'الحالة'">
        <option value="submitted">معلقة للمراجعة</option>
        <option value="approved">معتمدة</option>
        <option value="rejected">مرفوضة</option>
        <option value="open">جلسات مفتوحة الآن</option>
      </select>

      <button class="btn btn-sm btn-primary" @click="reload" ref="refreshBtn" :disabled="loading">
        <Icon icon="mdi:refresh" class="me-1" /> تحديث
      </button>
      <button class="btn btn-sm btn-success" @click="approveAllVisible" :disabled="!canAct || loading || items.length===0 || status!=='submitted'">
        <Icon icon="mdi:check-all" class="me-1"/> اعتماد الكل الظاهر
      </button>
      <button class="btn btn-sm btn-danger" @click="rejectAllVisible" :disabled="!canAct || loading || items.length===0 || status!=='submitted'">
        <Icon icon="mdi:close-circle-multiple" class="me-1"/> رفض الكل الظاهر
      </button>

      <span class="ms-auto small text-muted" aria-live="polite">{{ liveMsg }}</span>
    </div>

    <div v-if="error" class="alert alert-danger" role="alert">{{ error }}</div>

    <!-- Print-only context header for paper output -->
    <PrintPageHeader
      :title="`إذونات الخروج — جناح ${selectedWingId || '-'}`"
      :meta-lines="[
        `التاريخ: ${date}`,
        `الحالة: ${status}`,
        `الصف: ${classId ? ('#'+classId) : 'كل الصفوف'}`
      ]"
    />

    <!-- Cards by student -->
    <div v-if="loading" class="text-center text-muted p-4">جاري التحميل ...</div>
    <div v-else>
      <div v-if="grouped.length === 0" class="frame p-4 text-center text-muted">لا توجد أذونات مطابقة للمعايير الحالية.</div>
      <div class="row g-3">
        <div class="col-12 col-md-6 col-xl-4" v-for="g in grouped" :key="g.student_id">
          <div class="card h-100 shadow-sm">
            <div class="card-header d-flex align-items-center gap-2">
              <Icon icon="mdi:account" />
              <div class="fw-bold">{{ g.student_name || 'طالب #' + g.student_id }}</div>
              <span class="badge bg-secondary ms-auto" :title="'عدد الأذونات في البطاقة'">{{ g.events.length }}</span>
            </div>
            <div class="card-body">
              <div class="d-flex flex-column gap-2 mb-2">
                <div class="d-flex align-items-center gap-2 text-muted small">
                  <Icon icon="mdi:school"/> <span>{{ g.class_name || '-' }}</span>
                </div>
                <div class="d-flex align-items-center gap-2">
                  <Icon icon="mdi:account-tie" class="text-muted"/>
                  <span class="small">ولي الأمر:</span>
                  <strong class="small">{{ g.parent_name || '-' }}</strong>
                </div>
                <div class="d-flex align-items-center gap-2 flex-wrap small">
                  <Icon icon="mdi:phone" class="text-muted"/>
                  <a v-if="g.parent_phone" :href="'tel:'+g.parent_phone" class="me-2">{{ g.parent_phone }}</a>
                  <a v-if="g.extra_phone_no" :href="'tel:'+g.extra_phone_no" class="me-2">{{ g.extra_phone_no }}</a>
                  <a v-if="g.phone_no" :href="'tel:'+g.phone_no" class="me-2">{{ g.phone_no }}</a>
                  <span v-if="!g.parent_phone && !g.extra_phone_no && !g.phone_no" class="text-muted">لا توجد أرقام محفوظة</span>
                </div>
              </div>

              <ul class="list-group list-group-flush">
                <li class="list-group-item" v-for="e in g.events" :key="e.id">
                  <div class="d-flex align-items-center gap-2">
                    <Icon :icon="iconByReason(e.reason)" class="text-info"/>
                    <div class="flex-fill">
                      <div class="d-flex align-items-center gap-2">
                        <span class="badge" :class="statusBadge(e.review_status)">{{ statusLabel(e) }}</span>
                        <span class="small text-muted">{{ timeRange(e) }}</span>
                      </div>
                      <div class="small text-muted" v-if="e.note">{{ e.note }}</div>
                    </div>
                    <div class="ms-auto d-flex gap-1">
                      <button v-if="status==='submitted'" class="btn btn-sm btn-outline-success" :disabled="!canAct" @click="decideOne('approve', e)">
                        <Icon icon="mdi:check" />
                      </button>
                      <button v-if="status==='submitted'" class="btn btn-sm btn-outline-danger" :disabled="!canAct" @click="decideOne('reject', e)">
                        <Icon icon="mdi:close" />
                      </button>
                    </div>
                  </div>
                </li>
              </ul>
            </div>
            <div class="card-footer d-flex align-items-center">
              <button class="btn btn-sm btn-success me-2" :disabled="!canAct || status!=='submitted'" @click="approveStudent(g)">
                <Icon icon="mdi:check-all" class="me-1"/> اعتماد كل أذونات الطالب
              </button>
              <button class="btn btn-sm btn-danger" :disabled="!canAct || status!=='submitted'" @click="rejectStudent(g)">
                <Icon icon="mdi:close-circle-multiple" class="me-1"/> رفض كل أذونات الطالب
              </button>
              <span class="ms-auto small text-muted">{{ g.events.length }} عنصر</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { useWingPrefs } from "../../../shared/composables/useWingPrefs";
import { Icon } from "@iconify/vue";
import { computed, onMounted, reactive, ref, watch } from "vue";
import { tiles } from "../../../home/icon-tiles.config";
const tileMeta = computed(() => tiles.find((t) => t.to === "/wing/exits") || { title: "أذونات الخروج", icon: "solar:exit-bold-duotone", color: "#8e44ad" });
import { useWingContext } from "../../../shared/composables/useWingContext";
import WingPageHeader from "../../../components/ui/WingPageHeader.vue";
import WingWingPicker from "../../../components/ui/WingWingPicker.vue";
import PrintPageHeader from "../../../components/ui/PrintPageHeader.vue";
import { getWingClasses, getWingStudents, getExitEvents, getOpenExitEvents, postExitDecide } from "../../../shared/api/client";
// Lightweight date helpers to avoid external dependency
function pad2(n: number) { return n < 10 ? "0"+n : String(n); }
function todayISO(): string {
  const d = new Date();
  return `${d.getFullYear()}-${pad2(d.getMonth()+1)}-${pad2(d.getDate())}`;
}
function fmtHMFromIso(s?: string | null): string {
  if (!s) return "";
  const d = new Date(s);
  if (isNaN(d.getTime())) return "";
  return `${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
}

const { wingLabelFull, hasWingRole, isSuper, selectedWingId } = useWingContext();
const canAct = computed(() => isSuper.value || hasWingRole.value);

const { exits_default_status, default_date_mode, apply_on_load } = useWingPrefs();
const date = ref<string>(todayISO());
const classId = ref<number>(0);
const status = ref<"submitted" | "approved" | "rejected" | "open">("submitted");
const loading = ref(false);
const error = ref<string>("");
const liveMsg = ref<string>("");
const refreshBtn = ref<HTMLButtonElement | null>(null);

const classes = ref<{ id: number; name: string }[]>([]);
const items = ref<any[]>([]); // raw events after fetch
const studentMap = reactive<Record<number, any>>({});

function iconByReason(reason?: string | null) {
  switch ((reason || '').toLowerCase()) {
    case 'nurse': return 'mdi:medical-bag';
    case 'restroom': return 'mdi:toilet';
    case 'wing': return 'mdi:account-badge';
    case 'admin': return 'mdi:office-building';
    default: return 'mdi:exit-run';
  }
}
function statusBadge(st?: string | null) {
  if (st === 'approved') return 'bg-success';
  if (st === 'rejected') return 'bg-danger';
  if (st === 'submitted') return 'bg-warning text-dark';
  return 'bg-secondary';
}
function statusLabel(e: any) {
  if (status.value === 'open') return 'جلسة مفتوحة';
  return e.review_status === 'approved' ? 'معتمد' : e.review_status === 'rejected' ? 'مرفوض' : 'معلق';
}
function timeRange(e: any) {
  const start = e.started_at ? fmtHMFromIso(e.started_at) : '';
  const end = e.returned_at ? fmtHMFromIso(e.returned_at) : '';
  return end ? `${start}–${end}` : start;
}

const grouped = computed(() => {
  const by = new Map<number, { student_id: number; student_name?: string|null; class_name?: string|null; parent_name?: string|null; parent_phone?: string|null; extra_phone_no?: string|null; phone_no?: string|null; events: any[] }>();
  for (const e of items.value) {
    const sid = e.student_id;
    if (!sid) continue;
    if (!by.has(sid)) {
      const st = studentMap[sid] || {};
      by.set(sid, {
        student_id: sid,
        student_name: e.student_name || st.full_name,
        class_name: st.class_name,
        parent_name: st.parent_name,
        parent_phone: st.parent_phone,
        extra_phone_no: st.extra_phone_no,
        phone_no: st.phone_no,
        events: [],
      });
    }
    by.get(sid)!.events.push(e);
  }
  return Array.from(by.values());
});

async function loadWingClasses() {
  const params: any = {};
  if (selectedWingId?.value) params.wing_id = selectedWingId.value;
  const res = await getWingClasses(params);
  classes.value = (res.items || res || []).map((c: any) => ({ id: c.id, name: c.name })).sort((a: any, b: any) => a.name.localeCompare(b.name, 'ar'));
}

async function loadWingStudents() {
  // Load students once for contact info mapping
  const params: any = {};
  if (selectedWingId?.value) params.wing_id = selectedWingId.value;
  const res = await getWingStudents(params);
  for (const s of res.items || res || []) {
    studentMap[s.id] = s;
  }
}

async function reload() {
  try {
    loading.value = true;
    error.value = "";
    items.value = [];
    liveMsg.value = "";

    const params: any = {};
    if (classId.value) params.class_id = classId.value;
    if (selectedWingId?.value) params.wing_id = selectedWingId.value;
    if (status.value !== 'open') {
      params.date = date.value;
    }

    if (status.value === 'open') {
      const data = await getOpenExitEvents(params);
      // map to uniform shape
      items.value = data.map((e) => ({ ...e, review_status: null }));
      liveMsg.value = `جلسات مفتوحة الآن: ${items.value.length}`;
    } else {
      params.review_status = status.value;
      const data = await getExitEvents(params);
      items.value = data;
      liveMsg.value = `عدد الأذونات (${statusLabel({review_status: status.value})}): ${items.value.length}`;
    }
  } catch (err: any) {
    console.error(err);
    error.value = err?.response?.data?.detail || err?.message || 'حدث خطأ غير متوقع';
  } finally {
    loading.value = false;
  }
}

async function decideOne(action: 'approve'|'reject', e: any) {
  try {
    const res = await postExitDecide({ action, ids: [e.id] });
    if (res.updated > 0) {
      // remove from items when we are in submitted filter
      if (status.value === 'submitted') {
        items.value = items.value.filter((x) => x.id !== e.id);
      } else {
        e.review_status = action === 'approve' ? 'approved' : 'rejected';
      }
      liveMsg.value = `تم ${action === 'approve' ? 'اعتماد' : 'رفض'} إذن واحد.`;
    }
  } catch (err: any) {
    console.error(err);
    error.value = err?.response?.data?.detail || err?.message || 'تعذر تنفيذ الإجراء';
  }
}
async function approveStudent(g: any) {
  const ids = g.events.map((e: any) => e.id);
  await decideMany('approve', ids);
}
async function rejectStudent(g: any) {
  const ids = g.events.map((e: any) => e.id);
  await decideMany('reject', ids);
}
async function approveAllVisible() { await decideMany('approve', items.value.map((e) => e.id)); }
async function rejectAllVisible() { await decideMany('reject', items.value.map((e) => e.id)); }

async function decideMany(action: 'approve'|'reject', ids: number[]) {
  if (!ids.length) return;
  try {
    const res = await postExitDecide({ action, ids });
    if (status.value === 'submitted') {
      const set = new Set(ids);
      items.value = items.value.filter((e) => !set.has(e.id));
    } else {
      for (const e of items.value) if (ids.includes(e.id)) e.review_status = action === 'approve' ? 'approved' : 'rejected';
    }
    liveMsg.value = `تم ${action === 'approve' ? 'اعتماد' : 'رفض'} ${res.updated} إذن`;
    // focus back to refresh for stability
    setTimeout(() => refreshBtn.value?.focus(), 0);
  } catch (err: any) {
    console.error(err);
    error.value = err?.response?.data?.detail || err?.message || 'تعذر تنفيذ الإجراء';
  }
}

onMounted(async () => {
  // Apply Wing Settings defaults on load
  if (apply_on_load.value.exits) {
    status.value = exits_default_status.value === 'open_now' ? 'open' : (exits_default_status.value as any);
    if (default_date_mode.value === 'today') {
      date.value = todayISO();
    } else if (default_date_mode.value === 'remember') {
      const prev = localStorage.getItem('wing_exits.last_date');
      if (prev) date.value = prev;
      else date.value = todayISO();
    }
    // 'last' keeps whatever router/state provided; default to today if empty
    if (!date.value) date.value = todayISO();
  }
  await Promise.all([loadWingClasses(), loadWingStudents()]);
  await reload();
});

watch([date, classId, status], () => {
  // Persist last selections if user prefers remember/defaults
  try {
    localStorage.setItem('wing_exits.last_date', date.value);
    localStorage.setItem('wing_exits.last_class', String(classId.value || 0));
  } catch {}
  // Auto reload on filter change
  reload();
});
// Reload when wing selection changes (super admin)
watch(selectedWingId, async () => {
  await loadWingClasses();
  await loadWingStudents();
  await reload();
});
</script>

<style scoped>
.header-icon { font-size: 22px; }
.card-header { background-color: #f8f9fa; }
.list-group-item { font-size: .95rem; }
</style>