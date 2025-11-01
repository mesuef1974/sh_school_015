<template>
  <div class="d-flex align-items-center gap-2 header-bar frame" :dir="dir">
    <Icon :icon="icon" class="header-icon" :style="iconStyle" />
    <div class="flex-grow-1">
      <div class="fw-bold">{{ title }}</div>
      <div class="text-muted small" v-if="subtitleToShow">{{ subtitleToShow }}</div>
    </div>
    <!-- Right-aligned controls/actions injected by pages -->
    <div class="ms-auto d-flex align-items-center gap-2 flex-wrap">
      <!-- Global print trigger lives in page header (opposite side of title) -->
      <PrintPanelTrigger />
      <slot name="actions"></slot>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from "vue";
import { Icon } from "@iconify/vue";
import { useWingContext } from "../../shared/composables/useWingContext";
import PrintPanelTrigger from "./PrintPanelTrigger.vue";

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

onMounted(() => { ensureLoaded(); });

const subtitleToShow = computed(() => props.subtitle || wingLabelFull.value || "");
const iconStyle = computed(() => ({ color: props.color || "var(--maron-primary)" }));
const dir = computed(() => props.dir);
</script>

<style scoped>
.header-icon { font-size: 48px; }
</style>