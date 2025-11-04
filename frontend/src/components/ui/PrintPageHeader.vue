<template>
  <!-- Standardized print-only header for paper output -->
  <div class="print-only mb-2" dir="rtl">
    <h5 class="m-0">{{ title }}</h5>
    <div v-if="subtitle" class="small text-muted">{{ subtitle }}</div>
    <div v-for="(line, idx) in metaLines" :key="idx" class="small text-muted">{{ line }}</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
interface Props {
  title: string;
  subtitle?: string;
  metaLines?: string[];
}
const props = defineProps<Props>();
const title = computed(() => props.title || "");
const subtitle = computed(() => props.subtitle || "");
const metaLines = computed(() => props.metaLines || []);
</script>

<style scoped>
/* No extra styles; relies on global print.css .print-only rules */
</style>