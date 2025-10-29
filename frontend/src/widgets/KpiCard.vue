<template>
  <div class="kpi-card auto-card p-3 d-flex align-items-center gap-2" :class="variantClass">
    <div v-if="icon" class="icon-wrap d-flex align-items-center justify-content-center rounded-12">
      <i :class="icon"></i>
    </div>
    <div class="flex-fill">
      <div class="text-muted small">{{ title }}</div>
      <div class="display-6 m-0 d-flex align-items-baseline gap-1">
        <span v-if="!loading">{{ valueDisplay }}</span>
        <span v-else class="w-100"><div class="loader-line"></div></span>
        <small v-if="suffix && !loading" class="text-muted">{{ suffix }}</small>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  title: string;
  value?: string | number | null;
  suffix?: string;
  icon?: string;
  variant?: "default" | "danger" | "warning" | "secondary";
  loading?: boolean;
}>();

const valueDisplay = computed(() => props.value ?? "--");
const variantClass = computed(() => ({
  "kpi-danger": props.variant === "danger",
  "kpi-warning": props.variant === "warning",
  "kpi-secondary": props.variant === "secondary",
}));
</script>
<style scoped>
.kpi-card {
  min-height: 92px;
}
.icon-wrap {
  width: 44px;
  height: 44px;
  background: rgba(123, 30, 30, 0.08);
  color: var(--maron-primary);
}
.kpi-danger .icon-wrap {
  background: rgba(220, 53, 69, 0.08);
  color: #dc3545;
}
.kpi-warning .icon-wrap {
  background: rgba(255, 193, 7, 0.12);
  color: #b58100;
}
.kpi-secondary .icon-wrap {
  background: rgba(108, 117, 125, 0.12);
  color: #6c757d;
}
</style>
