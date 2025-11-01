<template>
  <section class="d-grid gap-3 page-grid page-grid-wide" dir="rtl">
    <!-- Header bar -->
    <WingPageHeader :icon="tileMeta.icon" :title="tileMeta.title" />

    <!-- General preferences -->
    <div class="card p-3">
      <h6 class="fw-bold mb-3 d-flex align-items-center gap-2">
        <Icon icon="solar:settings-bold-duotone" class="me-1" />
        الإعدادات العامة
      </h6>

      <div class="row g-3 align-items-end">
        <!-- Wing selection helper (Super only) -->
        <div class="col-12" v-if="isSuper">
          <label class="form-label">الجناح الحالي في الشريط</label>
          <div class="d-flex align-items-center gap-2 flex-wrap">
            <WingWingPicker id="pick-settings-wing" />
            <button class="btn btn-outline-primary btn-sm" :disabled="!selectedWingId" @click="setDefaultWingFromPicker">
              عيّن هذا الجناح كافتراضي
            </button>
            <span class="text-muted small" v-if="prefs.default_wing_id">
              الجناح الافتراضي المحفوظ: <strong>#{{ prefs.default_wing_id }}</strong>
            </span>
          </div>
        </div>

        <!-- Preferred class (scoped to selected/default wing) -->
        <div class="col-md-6 col-12">
          <label for="pref-class" class="form-label">الصف المفضّل</label>
          <select id="pref-class" class="form-select" v-model.number="prefs.default_class_id">
            <option :value="null">— لا اختيار —</option>
            <option v-for="c in classes" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
          <div class="form-text">سيُستخدم كقيمة ابتدائية في الصفحات التي تدعم اختيار الصف. {{ selectedClassName ? `الاختيار الحالي: ${selectedClassName}` : '' }}</div>
        </div>

        <!-- Students search limit -->
        <div class="col-md-3 col-6">
          <label for="pref-limit" class="form-label">حد أقصى لنتائج بحث الطلبة</label>
          <input id="pref-limit" type="number" class="form-control" min="50" max="2000" step="50" v-model.number="prefs.students_search_limit" />
          <div class="form-text">بين 50 و 2000. القيمة الافتراضية 300.</div>
        </div>

        <!-- CSV toggle -->
        <div class="col-md-3 col-6">
          <label class="form-label d-block">تفعيل أزرار CSV</label>
          <div class="form-check form-switch">
            <input class="form-check-input" type="checkbox" id="pref-csv" v-model="prefs.enable_csv_buttons" />
            <label class="form-check-label" for="pref-csv">إظهار زر «تصدير CSV» عند توفره</label>
          </div>
          <div class="form-check form-switch mt-2">
            <input class="form-check-input" type="checkbox" id="pref-csv-headers" v-model="prefs.csv_include_headers" />
            <label class="form-check-label" for="pref-csv-headers">تضمين رؤوس الأعمدة في CSV</label>
          </div>
        </div>

        <!-- Remember filters toggle -->
        <div class="col-md-6 col-12">
          <label class="form-label d-block">تذكّر فلاتر الصفحات</label>
          <div class="form-check form-switch">
            <input class="form-check-input" type="checkbox" id="pref-remember" v-model="prefs.remember_filters" />
            <label class="form-check-label" for="pref-remember">حفظ فلاتر البحث والاختيارات تلقائيًا</label>
          </div>
        </div>

        <!-- Date mode -->
        <div class="col-md-6 col-12">
          <label for="pref-date-mode" class="form-label">طريقة تهيئة التاريخ في الصفحات</label>
          <select id="pref-date-mode" class="form-select" v-model="prefs.default_date_mode">
            <option value="today">اليوم</option>
            <option value="remember">تذكّر آخر اختيار</option>
            <option value="last">آخر تاريخ مستخدم</option>
          </select>
        </div>

        <!-- Apply on load toggles -->
        <div class="col-12">
          <label class="form-label d-block">تطبيق الإعدادات تلقائيًا عند فتح الصفحة</label>
          <div class="d-flex flex-wrap gap-3">
            <div class="form-check form-switch">
              <input class="form-check-input" type="checkbox" id="pref-apply-classes" v-model="prefs.apply_on_load.classes" />
              <label class="form-check-label" for="pref-apply-classes">صفوف وطلبة</label>
            </div>
            <div class="form-check form-switch">
              <input class="form-check-input" type="checkbox" id="pref-apply-approvals" v-model="prefs.apply_on_load.approvals" />
              <label class="form-check-label" for="pref-apply-approvals">طلبات الاعتماد</label>
            </div>
            <div class="form-check form-switch">
              <input class="form-check-input" type="checkbox" id="pref-apply-daily" v-model="prefs.apply_on_load.daily" />
              <label class="form-check-label" for="pref-apply-daily">الغياب اليومي</label>
            </div>
            <div class="form-check form-switch">
              <input class="form-check-input" type="checkbox" id="pref-apply-exits" v-model="prefs.apply_on_load.exits" />
              <label class="form-check-label" for="pref-apply-exits">أذونات الخروج</label>
            </div>
          </div>
        </div>

        <!-- Actions -->
        <div class="col-12 d-flex gap-2 mt-2">
          <button class="btn btn-primary" @click="save">حفظ</button>
          <button class="btn btn-outline-secondary" @click="reset">استعادة الإفتراضيات</button>
          <button class="btn btn-outline-success" @click="exportPrefs">تصدير الإعدادات (JSON)</button>
          <label class="btn btn-outline-dark mb-0">
            استيراد (JSON)
            <input type="file" accept="application/json,.json" class="d-none" @change="importPrefs">
          </label>
          <span class="ms-auto small" :class="liveClass" aria-live="polite">{{ liveMsg }}</span>
        </div>
      </div>

      <div v-if="error" class="alert alert-danger mt-3" role="alert">{{ error }}</div>
    </div>

    <!-- Page-specific preferences: Approvals & Exits -->
    <div class="card p-3">
      <h6 class="fw-bold mb-3 d-flex align-items-center gap-2">
        <Icon icon="solar:checklist-minimalistic-bold-duotone" />
        إعدادات الصفحات (طلبات الاعتماد / أذونات الخروج)
      </h6>
      <div class="row g-3">
        <div class="col-md-6 col-12">
          <label class="form-label">الوضع الافتراضي لطلبات الاعتماد</label>
          <div class="d-flex gap-3 flex-wrap" role="group" aria-label="approvals-mode">
            <div class="form-check">
              <input class="form-check-input" type="radio" id="approvals-mode-period" value="period" v-model="prefs.approvals_default_mode">
              <label class="form-check-label" for="approvals-mode-period">حسب الحصص</label>
            </div>
            <div class="form-check">
              <input class="form-check-input" type="radio" id="approvals-mode-daily" value="daily" v-model="prefs.approvals_default_mode">
              <label class="form-check-label" for="approvals-mode-daily">الحالة اليومية</label>
            </div>
          </div>
        </div>
        <div class="col-md-6 col-12">
          <label for="exits-status" class="form-label">الحالة الافتراضية في أذونات الخروج</label>
          <select id="exits-status" class="form-select" v-model="prefs.exits_default_status">
            <option value="pending">معلقة للمراجعة</option>
            <option value="approved">معتمدة</option>
            <option value="rejected">مرفوضة</option>
            <option value="open_now">جلسات مفتوحة الآن</option>
          </select>
        </div>
      </div>
    </div>

    <!-- Page-specific preferences: Daily attendance & Students page -->
    <div class="card p-3">
      <h6 class="fw-bold mb-3 d-flex align-items-center gap-2">
        <Icon icon="solar:calendar-bold-duotone" />
        إعدادات الغياب اليومي وصفحة «صفوف وطلبة»
      </h6>
      <div class="row g-3">
        <div class="col-md-6 col-12">
          <label for="daily-class-beh" class="form-label">سلوك مرشّح الصف في الغياب اليومي</label>
          <select id="daily-class-beh" class="form-select" v-model="prefs.daily_class_filter_behavior">
            <option value="none">بدون تعبئة تلقائية</option>
            <option value="remember">تذكّر آخر صف</option>
            <option value="default_class">استخدام «الصف المفضّل»</option>
          </select>
        </div>
        <div class="col-md-6 col-12">
          <label class="form-label d-block">أعمدة صفحة «الطلبة» (المعروضة على الشاشة)</label>
          <div class="row g-2">
            <div class="col-6 col-md-4" v-for="(label, key) in studentColumnsOptions" :key="key">
              <div class="form-check form-switch">
                <input class="form-check-input" type="checkbox" :id="`col-${key}`" v-model="(prefs.students_columns_visibility as any)[key]" />
                <label class="form-check-label" :for="`col-${key}`">{{ label }}</label>
              </div>
            </div>
          </div>
          <hr class="my-3" />
          <label class="form-label d-block">أعمدة تُضاف عند «التصدير فقط»</label>
          <div class="row g-2">
            <div class="col-6 col-md-4" v-for="(label, key) in studentExportOptions" :key="key">
              <div class="form-check form-switch">
                <input class="form-check-input" type="checkbox" :id="`ex-${key}`" v-model="(prefs.students_export_columns as any)[key]" />
                <label class="form-check-label" :for="`ex-${key}`">{{ label }}</label>
              </div>
            </div>
          </div>
          <div class="form-check form-switch mt-2">
            <input class="form-check-input" type="checkbox" id="pref-contact" v-model="prefs.contact_actions_enabled" />
            <label class="form-check-label" for="pref-contact">تفعيل إجراءات الاتصال (اتصال/نسخ الأرقام)</label>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
<script setup lang="ts">
import { Icon } from "@iconify/vue";
import { computed, onMounted, reactive, ref, watch } from "vue";
import { tiles } from "../../../home/icon-tiles.config";
const tileMeta = computed(() => tiles.find((t) => t.to === "/wing/settings") || { title: "إعدادات الجناح", icon: "solar:settings-bold-duotone", color: "#7f8c8d" });
import WingPageHeader from "../../../components/ui/WingPageHeader.vue";
import { useWingContext } from "../../../shared/composables/useWingContext";
import WingWingPicker from "../../../components/ui/WingWingPicker.vue";
import { useWingPrefs } from "../../../shared/composables/useWingPrefs";
import { getWingClasses } from "../../../shared/api/client";

const { isSuper, selectedWingId } = useWingContext();

// Preferences (reactive)
const prefsApi = useWingPrefs();
const { default_wing_id, default_class_id, students_search_limit, enable_csv_buttons, remember_filters, default_date_mode, approvals_default_mode, exits_default_status, daily_class_filter_behavior, students_columns_visibility, students_export_columns, contact_actions_enabled, csv_include_headers, apply_on_load } = prefsApi;
const { set, reset: resetPrefs, save: savePrefs, exportJson, importJson } = prefsApi;

// Options for checklists
const studentColumnsOptions: Record<string, string> = {
  show_parent: 'ولي الأمر',
  show_parent_phone: 'هاتف ولي الأمر',
  show_extra_phone: 'هاتف إضافي',
  show_needs: 'يحتاج',
  show_active: 'نشط',
  show_day_state: 'حالة اليوم',
};
const studentExportOptions: Record<string, string> = {
  parent_name: 'ولي الأمر',
  parent_phone: 'هاتف ولي الأمر',
  extra_phone_no: 'هاتف إضافي',
  phone_no: 'هاتف الطالب',
  active: 'نشط',
  needs: 'يحتاج',
};

const prefs = reactive({
  get default_wing_id() { return default_wing_id.value; },
  set default_wing_id(v: number | null) { set("default_wing_id", v as any); },
  get default_class_id() { return default_class_id.value; },
  set default_class_id(v: number | null) { set("default_class_id", v as any); },
  get students_search_limit() { return students_search_limit.value; },
  set students_search_limit(v: number) { set("students_search_limit", v as any); },
  get enable_csv_buttons() { return enable_csv_buttons.value; },
  set enable_csv_buttons(v: boolean) { set("enable_csv_buttons", v as any); },
  get remember_filters() { return remember_filters.value; },
  set remember_filters(v: boolean) { set("remember_filters", v as any); },
  // new fields
  get default_date_mode() { return default_date_mode.value; },
  set default_date_mode(v: any) { set("default_date_mode", v as any); },
  get approvals_default_mode() { return approvals_default_mode.value; },
  set approvals_default_mode(v: any) { set("approvals_default_mode", v as any); },
  get exits_default_status() { return exits_default_status.value; },
  set exits_default_status(v: any) { set("exits_default_status", v as any); },
  get daily_class_filter_behavior() { return daily_class_filter_behavior.value; },
  set daily_class_filter_behavior(v: any) { set("daily_class_filter_behavior", v as any); },
  get students_columns_visibility() { return students_columns_visibility.value; },
  set students_columns_visibility(v: any) { set("students_columns_visibility", v as any); },
  get students_export_columns() { return students_export_columns.value; },
  set students_export_columns(v: any) { set("students_export_columns", v as any); },
  get contact_actions_enabled() { return contact_actions_enabled.value; },
  set contact_actions_enabled(v: boolean) { set("contact_actions_enabled", v as any); },
  get csv_include_headers() { return csv_include_headers.value; },
  set csv_include_headers(v: boolean) { set("csv_include_headers", v as any); },
  get apply_on_load() { return apply_on_load.value; },
  set apply_on_load(v: any) { set("apply_on_load", v as any); },
});

const liveMsg = ref("");
const liveClass = computed(() => (liveMsg.value.includes("فشل") || liveMsg.value.includes("تعذّر")) ? "text-danger" : "text-success");
const error = ref("");

// Classes for current wing
const classes = ref<{id:number; name:string}[]>([]);
const selectedClassName = computed(() => classes.value.find(c => c.id === prefs.default_class_id)?.name || "");

async function loadClasses() {
  try {
    error.value = "";
    classes.value = [];
    const wingId = selectedWingId.value || prefs.default_wing_id || null;
    const params: any = {};
    if (wingId) params.wing_id = wingId;
    const res = await getWingClasses(params);
    classes.value = (res.items || res || []).map((c: any) => ({ id: c.id, name: c.name }));
    // If saved default_class_id not in list, clear it
    if (prefs.default_class_id && !classes.value.some(c => c.id === prefs.default_class_id)) {
      prefs.default_class_id = null;
    }
  } catch (e: any) {
    error.value = e?.message || "تعذّر تحميل الصفوف";
  }
}

function setDefaultWingFromPicker() {
  if (selectedWingId.value) {
    prefs.default_wing_id = selectedWingId.value as number;
    liveMsg.value = `تم تعيين الجناح #${selectedWingId.value} كافتراضي`;
  }
}

function save() {
  savePrefs();
  liveMsg.value = "تم حفظ التفضيلات";
}
function reset() {
  resetPrefs();
  liveMsg.value = "تمت استعادة الإفتراضيات";
  loadClasses();
}

function exportPrefs() {
  try {
    const data = exportJson();
    const blob = new Blob([data], { type: "application/json;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "wing-settings.json";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    liveMsg.value = "تم تصدير الإعدادات";
  } catch {
    liveMsg.value = "تعذّر تصدير الإعدادات";
  }
}

async function importPrefs(ev: Event) {
  const input = ev.target as HTMLInputElement;
  const file = input.files && input.files[0];
  if (!file) return;
  try {
    const text = await file.text();
    const ok = importJson(text);
    if (ok) {
      liveMsg.value = "تم استيراد الإعدادات";
      loadClasses();
    } else {
      liveMsg.value = "فشل استيراد الإعدادات";
    }
  } catch {
    liveMsg.value = "تعذّر قراءة الملف";
  } finally {
    input.value = "";
  }
}

onMounted(loadClasses);
watch(() => selectedWingId.value, () => loadClasses());
</script>
<style scoped>
</style>