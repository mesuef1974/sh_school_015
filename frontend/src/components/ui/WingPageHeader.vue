<template>
  <div class="d-flex align-items-center gap-2 header-bar frame" :dir="dir">
    <Icon :icon="icon" class="header-icon" :style="iconStyle" />
    <div class="flex-grow-1">
      <div class="fw-bold">{{ title }}</div>
      <div class="text-muted small" v-if="subtitleToShow">{{ subtitleToShow }}</div>
    </div>
    <!-- Right-aligned controls/actions injected by pages -->
    <div class="ms-auto d-flex align-items-center gap-2 flex-wrap">
      <!-- Default date/time badge (only when no actions slot is provided) -->
      <template v-if="!hasActionsSlot">
        <span class="small text-muted" aria-live="polite">
          <template v-if="isToday">اليوم: {{ selectedDateDMY }} • {{ liveTime }}</template>
          <template v-else>التاريخ: {{ selectedDateDMY }}</template>
        </span>
      </template>
      <!-- Global print trigger lives in page header (opposite side of title) -->
      <PrintPanelTrigger />
      <slot name="actions"></slot>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, ref, useSlots } from "vue";
import { Icon } from "@iconify/vue";
import { useWingContext } from "../../shared/composables/useWingContext";
import PrintPanelTrigger from "./PrintPanelTrigger.vue";
import { useRoute } from 'vue-router';
import { formatDateDMY, formatISOtoDMY, parseDMYtoISO, toIsoDate } from "../../shared/utils/date";

const props = withDefaults(defineProps<{
  icon: string;
  title: string;
  color?: string | null;
  subtitle?: string | null; // optional override
  dir?: 'rtl' | 'ltr';
}>(), {
  color: null,
  subtitle: null,
  dir: 'rtl'
});

const { ensureLoaded, wingLabelFull } = useWingContext();

onMounted(() => { ensureLoaded(); startLiveClock(); });
onBeforeUnmount(() => { stopLiveClock(); });

const subtitleToShow = computed(() => props.subtitle || wingLabelFull.value || "");
const iconStyle = computed(() => ({ color: props.color || "var(--maron-primary)" }));
const dir = computed(() => props.dir);

// Detect if actions slot provided (non-empty)
const slots = useSlots();
const hasActionsSlot = computed(() => !!slots.actions);

// Date/time badge state derived from ?date
const route = useRoute();
const selectedDateDMY = computed(() => {
  const qd = String(route.query.date || '').trim();
  if (qd) return formatISOtoDMY(qd) || formatDateDMY(new Date());
  return formatDateDMY(new Date());
});
const isToday = computed(() => {
  const qd = String(route.query.date || '').trim();
  const iso = qd || toIsoDate(new Date());
  return iso === toIsoDate(new Date());
});
const liveTime = ref<string>("");
function updateLiveTime() {
  const now = new Date();
  const hh = String(now.getHours()).padStart(2, '0');
  const mm = String(now.getMinutes()).padStart(2, '0');
  liveTime.value = `${hh}:${mm}`;
}
let liveClockTimer: any = null;
function startLiveClock() { stopLiveClock(); updateLiveTime(); liveClockTimer = setInterval(updateLiveTime, 60_000); }
function stopLiveClock() { if (liveClockTimer) { clearInterval(liveClockTimer); liveClockTimer = null; } }
</script>

<style scoped>
.header-icon { font-size: 48px; }
</style>
