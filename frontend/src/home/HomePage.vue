<template>
  <section class="d-grid gap-3">
    <header
      v-motion
      :initial="{ opacity: 0, y: -50 }"
      :enter="{ opacity: 1, y: 0, transition: { duration: 500 } }"
      class="auto-card p-3 d-flex align-items-center gap-3"
    >
      <img
        :src="logoSrc"
        alt=""
        style="
          height: 54px;
          filter: brightness(0) saturate(100%) invert(15%) sepia(50%) saturate(2500%)
            hue-rotate(330deg) brightness(90%) contrast(90%);
        "
      />
      <div class="fw-bold" style="white-space: nowrap">{{ salutation }}، {{ name }}</div>
      <span class="ms-auto"></span>
      <!-- مثال بسيط على استخدام Lottie عبر vue3-lottie: يظهر على الشاشات المتوسطة فما فوق -->
      <Vue3Lottie
        class="d-none d-md-block"
        path="https://cdn.lordicon.com/egiwmiit.json"
        :loop="true"
        :autoplay="true"
        :speed="1"
        style="height: 54px"
        aria-label="Animated greeting"
      />
    </header>

    <!-- Toolbar: reorder/cut/copy/paste -->
    <div class="auto-card p-2 d-flex align-items-center gap-2 flex-wrap">
      <DsButton
        size="sm"
        :variant="reorderMode ? 'primary' : 'outline'"
        icon="solar:arrows-up-down-bold-duotone"
        @click="toggleReorder"
      >
        {{ reorderMode ? "إنهاء الترتيب" : "وضع الترتيب" }}
      </DsButton>
      <div class="vr d-none d-sm-block"></div>
      <DsButton
        size="sm"
        variant="outline"
        :disabled="!selectedId"
        icon="solar:scissors-bold-duotone"
        @click="onCut"
        >قص</DsButton
      >
      <DsButton
        size="sm"
        variant="outline"
        :disabled="!selectedId"
        icon="solar:copy-bold-duotone"
        @click="onCopy"
        >نسخ</DsButton
      >
      <DsButton
        size="sm"
        variant="success"
        :disabled="!canPaste"
        icon="solar:clipboard-list-bold-duotone"
        @click="onPaste"
        >لصق</DsButton
      >
      <span class="ms-auto small text-muted" v-if="selectedId">المحدد: {{ selectedId }}</span>
      <DsButton size="sm" variant="outline" icon="solar:refresh-bold-duotone" @click="resetOrder"
        >إعادة ضبط</DsButton
      >
    </div>

    <div class="cards-grid-7 tile-grid" :class="{ reordering: reorderMode }">
      <div
        v-for="(t, index) in orderedTiles"
        :key="t.__key"
        v-motion
        :initial="{ opacity: 0, scale: 0.9 }"
        :enter="{
          opacity: 1,
          scale: 1,
          transition: {
            delay: 100 + index * 50,
            duration: 400,
          },
        }"
      >
        <div
          class="tile-wrap"
          :class="{ selected: selectedId === t.id }"
          :draggable="reorderMode"
          @dragstart="onDragStart(t.__key, index, $event)"
          @dragover.prevent="onDragOver(index, $event)"
          @drop.prevent="onDrop(index, $event)"
          @click.prevent="onTileClick(t.id)"
        >
          <IconTile
            :to="reorderMode ? undefined : t.to"
            :href="reorderMode ? undefined : t.href"
            :icon="t.icon"
            :title="t.title"
            :subtitle="t.subtitle"
            :color="t.color"
            :badge="t.kpiKey ? (kpiMap as any)[t.kpiKey] : undefined"
            compact
          />
        </div>
      </div>
    </div>
  </section>
</template>
<script setup lang="ts">
import { computed, ref, onMounted, watch } from "vue";
import { useAuthStore } from "../app/stores/auth";
import IconTile from "../widgets/IconTile.vue";
import DsButton from "../components/ui/DsButton.vue";
import { tiles } from "./icon-tiles.config";

const auth = useAuthStore();
const name = computed(() => auth.profile?.full_name || auth.profile?.username || "");
const roles = computed(() => auth.profile?.roles || []);
const hasRole = (r: string) => roles.value.includes(r);
const isSuper = computed(() => !!auth.profile?.is_superuser);
const isTeacher = computed(() => hasRole("teacher"));
const logoSrc = "/assets/img/logo.png";

// Arabic salutation based on current hour
const hour = new Date().getHours();
const salutation = computed(() =>
  hour < 12 ? "صباح الخير" : hour < 17 ? "نهارك سعيد" : "مساء الخير"
);

// Visible tiles based on roles/permissions
const roleSet = computed(() => new Set(auth.profile?.roles || []));
const permSet = computed(() => new Set(auth.profile?.permissions || []));
const canSee = (t: any) => {
  const okRole = !t.roles?.length || t.roles.some((r: string) => roleSet.value.has(r));
  const okPerm = !t.permissions?.length || t.permissions.some((p: string) => permSet.value.has(p));
  return okRole && okPerm;
};
const isDevMesuef = computed(() => (auth.profile?.username || "").toLowerCase() === "mesuef");
const visibleTiles = computed(() => (isDevMesuef.value ? tiles : tiles.filter(canSee)));

// ----- Reorder, drag&drop, cut/copy/paste -----
const reorderMode = ref(false);
const selectedId = ref<string | null>(null);
const clipboard = ref<{ id: string; cut: boolean } | null>(null);
const dragKey = ref<string | null>(null);
const dragFromIndex = ref<number | null>(null);

const username = computed(() => auth.profile?.username || "guest");
const STORAGE_KEY = computed(() => `homeTileOrder:${username.value}`);
const orderIds = ref<string[]>([]);

function loadOrder() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY.value);
    orderIds.value = raw ? JSON.parse(raw) : [];
  } catch {
    orderIds.value = [];
  }
}
function saveOrder() {
  try {
    localStorage.setItem(STORAGE_KEY.value, JSON.stringify(orderIds.value));
  } catch {}
}

onMounted(() => {
  loadOrder();
});
watch(visibleTiles, () => {
  /* ensure order still valid when roles change */
  const visibleIds = new Set(visibleTiles.value.map((t) => t.id));
  orderIds.value = orderIds.value.filter((id) => visibleIds.has(id));
  saveOrder();
});

// Build ordered list with stable keys to support temporary duplicates when copying
const orderedTiles = computed(() => {
  const base = visibleTiles.value.map((t) => ({ ...t, __key: t.id }));
  if (!orderIds.value.length) return base;
  const map = new Map(base.map((t) => [t.id, t] as const));
  const result: any[] = [];
  for (const id of orderIds.value) {
    if (map.has(id)) result.push({ ...(map.get(id) as any), __key: id + ":ord" });
  }
  // Append any new items not in order list at the end
  base.forEach((t) => {
    if (!orderIds.value.includes(t.id)) result.push(t);
  });
  // If clipboard copy requires a preview duplicate (optional): ignore for now to keep minimal
  return result;
});

function indexOfKey(idx: number): number {
  return idx;
}

function toggleReorder() {
  reorderMode.value = !reorderMode.value;
}
function onTileClick(id: string) {
  selectedId.value = id;
}

function moveItem(from: number, to: number) {
  const current = orderedTiles.value.map((t) => t.id);
  const id = current[from];
  if (id == null) return;
  // Build new order by current and then persist ids
  current.splice(from, 1);
  current.splice(to, 0, id);
  orderIds.value = current;
  saveOrder();
}

function onDragStart(key: string, index: number, e: DragEvent) {
  if (!reorderMode.value) return;
  dragKey.value = key;
  dragFromIndex.value = index;
  try {
    e.dataTransfer?.setData("text/plain", key);
  } catch {}
  try {
    e.dataTransfer && (e.dataTransfer.effectAllowed = "move");
  } catch {}
}
function onDragOver(index: number, e: DragEvent) {
  if (!reorderMode.value) return;
  try {
    e.dataTransfer && (e.dataTransfer.dropEffect = "move");
  } catch {}
}
function onDrop(index: number, e: DragEvent) {
  if (!reorderMode.value) return;
  const from = dragFromIndex.value;
  if (from == null) return;
  moveItem(from, index);
  dragFromIndex.value = null;
  dragKey.value = null;
}

const canPaste = computed(() => !!clipboard.value && !!selectedId.value);
function onCut() {
  if (!selectedId.value) return;
  clipboard.value = { id: selectedId.value, cut: true };
}
function onCopy() {
  if (!selectedId.value) return;
  clipboard.value = { id: selectedId.value, cut: false };
}
function onPaste() {
  if (!clipboard.value || !selectedId.value) return;
  const targetIdx = orderedTiles.value.findIndex((t) => t.id === selectedId.value);
  if (targetIdx < 0) return;
  const srcId = clipboard.value.id;
  const list = orderedTiles.value.map((t) => t.id);
  const existingIdx = list.indexOf(srcId);
  if (clipboard.value.cut) {
    // Move src before target
    if (existingIdx >= 0) {
      list.splice(existingIdx, 1);
    }
    list.splice(targetIdx, 0, srcId);
    orderIds.value = list;
    saveOrder();
    clipboard.value = null;
  } else {
    // Copy: keep unique by just moving as well (no duplicates to avoid confusion)
    if (existingIdx >= 0) {
      list.splice(existingIdx, 1);
    }
    list.splice(targetIdx, 0, srcId);
    orderIds.value = list;
    saveOrder();
  }
}
function resetOrder() {
  orderIds.value = [];
  saveOrder();
}

// KPI badge placeholders from profile if available (extensible)
const kpiMap = computed(() => ({
  absentToday: (auth as any).profile?.kpis?.absentToday ?? undefined,
  presentPct: (auth as any).profile?.kpis?.presentPct ?? undefined,
  pendingApprovals: (auth as any).profile?.kpis?.pendingApprovals ?? undefined,
}));

// Intro overlay state (show once per session; optionally never again) — kept from previous implementation
const INTRO_KEY_FOREVER = "homeIntroNeverShow";
const INTRO_KEY_SESSION = "homeIntroSeen";
const prefersReduced =
  typeof window !== "undefined" && window.matchMedia
    ? window.matchMedia("(prefers-reduced-motion: reduce)")
    : null;
const reducedMotion = ref<boolean>(prefersReduced ? prefersReduced.matches : false);
const showIntro = ref<boolean>(false);
const allowMotion = ref<boolean>(false);
const failed = ref<boolean>(false);
const primaryPath = "https://assets10.lottiefiles.com/packages/lf20_1pxqjqps.json";
const backupPath = "https://cdn.lordicon.com/egiwmiit.json";
const currentPath = ref<string>(primaryPath);
const shouldAnimate = computed(() => (!reducedMotion.value || allowMotion.value) && !failed.value);

onMounted(() => {
  try {
    if (prefersReduced) {
      const handler = (e: MediaQueryListEvent) => {
        reducedMotion.value = e.matches;
      };
      // @ts-ignore - addEventListener not in older TS dom lib types
      prefersReduced.addEventListener
        ? prefersReduced.addEventListener("change", handler)
        : prefersReduced.addListener(handler);
    }
  } catch {}
  try {
    const never = localStorage.getItem(INTRO_KEY_FOREVER) === "1";
    const seenSession = sessionStorage.getItem(INTRO_KEY_SESSION) === "1";
    showIntro.value = !never && !seenSession;
  } catch {
    showIntro.value = true;
  }
  try {
    allowMotion.value = localStorage.getItem("homeIntroAllowMotion") === "1";
  } catch {}
});

function dismissIntro() {
  showIntro.value = false;
  try {
    sessionStorage.setItem(INTRO_KEY_SESSION, "1");
  } catch {}
}
function dismissIntroForever() {
  showIntro.value = false;
  try {
    localStorage.setItem(INTRO_KEY_FOREVER, "1");
    sessionStorage.setItem(INTRO_KEY_SESSION, "1");
  } catch {}
}
function enableMotionOverride() {
  allowMotion.value = true;
  failed.value = false;
  try {
    localStorage.setItem("homeIntroAllowMotion", "1");
  } catch {}
}
function retryAnimation() {
  failed.value = false;
  currentPath.value = currentPath.value === primaryPath ? backupPath : primaryPath;
}
</script>
<style scoped>
.tile-grid > div {
  position: relative;
}
/* تعزيز الإحساس بالعوم عبر مسافة وظل خفيفين تأتي من مكون IconTile */

/* أنماط شاشة الترحيب */
.intro-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1050; /* فوق الهيدر والبلاطات */
  padding: 16px;
}
.intro-card {
  max-width: 720px;
  width: 100%;
  position: relative;
}
.intro-close {
  position: absolute;
  top: 8px;
  inset-inline-start: 8px; /* RTL-friendly */
}
.intro-media {
  display: flex;
  justify-content: center;
}

/* Reorder visuals */
.tile-grid.reordering .tile-wrap {
  cursor: grab;
}
.tile-grid.reordering .tile-wrap:active {
  cursor: grabbing;
}
.tile-wrap.selected .tile {
  outline: 2px solid rgba(138, 21, 56, 0.35);
  outline-offset: 2px;
}
</style>
