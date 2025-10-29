<template>
  <section class="d-grid gap-3">
    <div class="auto-card p-3 d-flex align-items-center gap-2 flex-wrap">
      <Icon icon="solar:ui-bold-duotone" class="text-2xl" />
      <div class="fw-bold">مصمم الأيقونات — الصفحة الرئيسية</div>
      <span class="ms-auto small text-muted" v-if="meta.version"
        >الإصدار: {{ meta.version }}
        <span v-if="meta.updated_by">— آخر تحرير: {{ meta.updated_by }}</span></span
      >
      <div class="d-flex align-items-center gap-2 ms-auto toolbar">
        <DsButton size="sm" variant="primary" icon="solar:plus-bold-duotone" @click="addTile"
          >إضافة بطاقة</DsButton
        >
        <DsButton
          size="sm"
          variant="outline"
          icon="solar:save-bold-duotone"
          :loading="saving"
          @click="save"
          >حفظ</DsButton
        >
        <DsButton size="sm" variant="outline" icon="solar:import-bold-duotone" @click="importJson"
          >استيراد</DsButton
        >
        <DsButton size="sm" variant="outline" icon="solar:export-bold-duotone" @click="exportJson"
          >تصدير</DsButton
        >
      </div>
    </div>

    <div class="row g-3">
      <!-- Editor form -->
      <div class="col-12 col-lg-5">
        <div class="auto-card p-3">
          <div class="d-flex align-items-center gap-2 mb-2">
            <Icon icon="solar:edit-bold-duotone" />
            <div class="fw-bold">تحرير البطاقة</div>
          </div>
          <div v-if="activeTile" class="vstack gap-2">
            <div class="row g-2">
              <div class="col-6">
                <label class="form-label small fw-bold">المعرّف</label>
                <input
                  class="form-control form-control-sm"
                  v-model.trim="activeTile.id"
                  placeholder="unique_id"
                />
              </div>
              <div class="col-6">
                <label class="form-label small fw-bold">اللون</label>
                <input
                  class="form-control form-control-sm"
                  v-model.trim="activeTile.color"
                  placeholder="#8a1538"
                />
              </div>
              <div class="col-12">
                <label class="form-label small fw-bold">العنوان</label>
                <input class="form-control form-control-sm" v-model.trim="activeTile.title" />
              </div>
              <div class="col-12">
                <label class="form-label small fw-bold">وصف مختصر</label>
                <input class="form-control form-control-sm" v-model.trim="activeTile.subtitle" />
              </div>
              <div class="col-6">
                <label class="form-label small fw-bold">الوجهة (to)</label>
                <input
                  class="form-control form-control-sm"
                  v-model.trim="activeTile.to"
                  placeholder="/path"
                />
              </div>
              <div class="col-6">
                <label class="form-label small fw-bold">الرابط (href)</label>
                <input
                  class="form-control form-control-sm"
                  v-model.trim="activeTile.href"
                  placeholder="https://..."
                />
              </div>
              <div class="col-12">
                <label class="form-label small fw-bold">الأيقونة (Iconify)</label>
                <input
                  class="form-control form-control-sm"
                  v-model.trim="activeTile.icon"
                  placeholder="solar:calendar-bold-duotone"
                />
                <small class="text-muted"
                  >مثال: solar:calendar-bold-duotone — استخدم
                  <a href="https://icon-sets.iconify.design/" target="_blank">Iconify</a></small
                >
              </div>
              <div class="col-12">
                <label class="form-label small fw-bold">الأدوار (roles)</label>
                <input
                  class="form-control form-control-sm"
                  v-model.trim="rolesCsv"
                  placeholder="teacher, wing_supervisor"
                />
                <small class="text-muted">افصل القيم بفاصلة</small>
              </div>
              <div class="col-12">
                <label class="form-label small fw-bold">الصلاحيات (permissions)</label>
                <input
                  class="form-control form-control-sm"
                  v-model.trim="permsCsv"
                  placeholder="attendance.session.write, analytics.kpi"
                />
                <small class="text-muted">افصل القيم بفاصلة</small>
              </div>
            </div>
            <div class="d-flex gap-2 mt-2">
              <DsButton
                size="sm"
                variant="success"
                icon="solar:check-circle-bold-duotone"
                @click="applyEdits"
                >تطبيق</DsButton
              >
              <DsButton
                size="sm"
                variant="outline"
                icon="solar:copy-bold-duotone"
                @click="duplicateTile"
                >استنساخ</DsButton
              >
              <DsButton
                size="sm"
                variant="danger"
                icon="solar:trash-bin-trash-bold-duotone"
                @click="removeTile"
                >حذف</DsButton
              >
            </div>
          </div>
          <div v-else class="text-muted text-center py-4">اختر بطاقة من القائمة لتحريرها</div>
        </div>

        <div class="auto-card p-3 mt-3">
          <div class="d-flex align-items-center gap-2 mb-2">
            <Icon icon="solar:sort-vertical-bold-duotone" />
            <div class="fw-bold">ترتيب البطاقات</div>
          </div>
          <ul class="list-group list-group-flush small sortable-list">
            <li
              v-for="(t, idx) in tiles"
              :key="t.id"
              class="list-group-item d-flex align-items-center gap-2"
            >
              <button class="btn btn-sm btn-light" @click="move(idx, -1)" :disabled="idx === 0">
                <Icon icon="solar:arrow-up-bold-duotone" />
              </button>
              <button
                class="btn btn-sm btn-light"
                @click="move(idx, +1)"
                :disabled="idx === tiles.length - 1"
              >
                <Icon icon="solar:arrow-down-bold-duotone" />
              </button>
              <span class="badge text-bg-secondary">{{ idx + 1 }}</span>
              <span class="flex-fill" @click="select(idx)"
                ><strong>{{ t.title }}</strong> <span class="text-muted">— {{ t.id }}</span></span
              >
              <span class="badge" :style="{ backgroundColor: t.color || '#eee' }">&nbsp;</span>
            </li>
          </ul>
        </div>
      </div>

      <!-- Live preview -->
      <div class="col-12 col-lg-7">
        <div class="auto-card p-3 mb-2 d-flex align-items-center gap-2">
          <Icon icon="solar:eye-bold-duotone" />
          <div class="fw-bold">معاينة الشبكة</div>
          <div class="ms-auto d-flex align-items-center gap-2">
            <input
              class="form-control form-control-sm"
              v-model.trim="q"
              placeholder="فلترة بالعنوان"
              style="max-width: 220px"
            />
          </div>
        </div>
        <div class="cards-grid-7 tile-grid">
          <div v-for="t in filtered" :key="t.id">
            <IconTile
              :icon="t.icon"
              :title="t.title"
              :subtitle="t.subtitle"
              :color="t.color"
              :to="undefined"
              :href="undefined"
              compact
            />
          </div>
          <div v-if="filtered.length === 0" class="text-muted small text-center py-4">
            لا توجد بطاقات وفق الفلتر الحالي
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import DsButton from "../../components/ui/DsButton.vue";
import IconTile from "../../widgets/IconTile.vue";
import { getUiTilesEffective, postUiTilesSave } from "../../shared/api/client";
import { tiles as staticTiles } from "../../home/icon-tiles.config";

interface Tile {
  id: string;
  title: string;
  subtitle?: string;
  to?: string;
  href?: string;
  icon: string;
  color?: string;
  roles?: string[];
  permissions?: string[];
  kpiKey?: string;
  enabled?: boolean;
}

const tiles = ref<Tile[]>([]);
const meta = ref<{ version?: number; updated_by?: string | null }>({});
const saving = ref(false);
const activeIndex = ref<number>(-1);
const q = ref("");

const filtered = computed(() =>
  tiles.value.filter((t) => !q.value || t.title.toLowerCase().includes(q.value.toLowerCase()))
);
const activeTile = computed<Tile | null>(() => tiles.value[activeIndex.value] || (null as any));
const rolesCsv = computed({
  get() {
    return (activeTile.value?.roles || []).join(", ");
  },
  set(v: string) {
    if (activeTile.value)
      activeTile.value.roles = (v || "")
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
  },
});
const permsCsv = computed({
  get() {
    return (activeTile.value?.permissions || []).join(", ");
  },
  set(v: string) {
    if (activeTile.value)
      activeTile.value.permissions = (v || "")
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
  },
});

function select(idx: number) {
  activeIndex.value = idx;
}
function addTile() {
  tiles.value.push({
    id: suggestId("tile_"),
    title: "بطاقة جديدة",
    subtitle: "",
    icon: "solar:star-bold-duotone",
    color: "#8a1538",
    roles: [],
    permissions: [],
    enabled: true,
  });
  activeIndex.value = tiles.value.length - 1;
}
function duplicateTile() {
  if (activeTile.value) {
    const t = JSON.parse(JSON.stringify(activeTile.value));
    t.id = suggestId(t.id + "_copy_");
    tiles.value.splice(activeIndex.value + 1, 0, t);
    activeIndex.value += 1;
  }
}
function removeTile() {
  if (activeIndex.value >= 0) {
    tiles.value.splice(activeIndex.value, 1);
    activeIndex.value = -1;
  }
}
function move(i: number, delta: number) {
  const j = i + delta;
  if (j < 0 || j >= tiles.value.length) return;
  const a = tiles.value[i];
  tiles.value.splice(i, 1);
  tiles.value.splice(j, 0, a);
  if (activeIndex.value === i) activeIndex.value = j;
}
function applyEdits() {
  /* reactive bindings already applied */
}
function suggestId(prefix: string) {
  let k = 1;
  const ids = new Set(tiles.value.map((t) => t.id));
  while (ids.has(prefix + k)) k++;
  return prefix + k;
}

async function loadInitial() {
  try {
    const res = await getUiTilesEffective();
    const arr = Array.isArray((res as any).tiles) ? (res as any).tiles : [];
    if (arr.length) {
      tiles.value = arr as Tile[];
      meta.value = {
        version: (res as any).version || 1,
        updated_by: (res as any).updated_by || null,
      };
      return;
    }
  } catch {}
  // fallback to static config
  tiles.value = (staticTiles as any[]).map((t) => ({ ...t, enabled: true }));
  meta.value = { version: 1, updated_by: null };
}

async function save() {
  saving.value = true;
  try {
    // Clean and persist
    const payload = { version: meta.value.version || 1, tiles: tiles.value.map((t) => ({ ...t })) };
    const res = await postUiTilesSave(payload);
    meta.value.version = res?.version || payload.version || 1;
  } finally {
    saving.value = false;
  }
}

function exportJson() {
  const data = { version: meta.value.version || 1, tiles: tiles.value };
  const blob = new Blob([new TextEncoder().encode(JSON.stringify(data, null, 2))], {
    type: "application/json;charset=utf-8",
  });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "home_tiles.json";
  a.click();
}

function importJson() {
  const inp = document.createElement("input");
  inp.type = "file";
  inp.accept = "application/json";
  inp.onchange = () => {
    const f = inp.files && inp.files[0];
    if (!f) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const parsed = JSON.parse(String(reader.result || "{}"));
        const arr = Array.isArray(parsed)
          ? parsed
          : Array.isArray(parsed.tiles)
            ? parsed.tiles
            : [];
        if (arr.length) {
          tiles.value = arr;
          meta.value.version = parsed.version || 1;
          activeIndex.value = -1;
        }
      } catch {}
    };
    reader.readAsText(f, "utf-8");
  };
  inp.click();
}

onMounted(loadInitial);
</script>

<style scoped>
.tile-grid .col-6,
.tile-grid .col-md-4,
.tile-grid .col-xl-3 {
  position: relative;
}
.sortable-list .list-group-item {
  user-select: none;
}
.toolbar :deep(button) {
  white-space: nowrap;
}
</style>
