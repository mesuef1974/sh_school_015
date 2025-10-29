<template>
  <div class="empty-state text-center p-4 auto-card">
    <div class="display-6 mb-2">{{ title }}</div>
    <p class="text-muted mb-3">{{ subtitle }}</p>
    <slot />
  </div>
</template>
<script setup lang="ts">
const props = defineProps<{ title: string; subtitle?: string }>();
</script>
<style scoped>
.empty-state {
  background: #fff;
}
</style>
