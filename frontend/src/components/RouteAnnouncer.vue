<template>
  <!-- Accessible route change announcer for screen readers (dev/prod safe) -->
  <div
    aria-live="polite"
    aria-atomic="true"
    role="status"
    class="sr-only"
  >
    {{ message }}
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const message = ref('')

function computeAnnouncement(): string {
  // Prefer document.title (already i18n-bound), fallback to route name/path
  const title = typeof document !== 'undefined' ? document.title : ''
  if (title && title.trim().length > 0) return title
  return (route.meta?.ariaLabel as string) || (route.meta?.title as string) || (route.name as string) || route.path
}

watch(
  () => route.fullPath,
  () => {
    // Defer a tick to allow document.title watchers to update first
    queueMicrotask(() => { message.value = computeAnnouncement() })
  },
  { immediate: true }
)
</script>

<style scoped>
/* Visually hidden but accessible to AT (screen readers) */
.sr-only {
  position: absolute !important;
  width: 1px !important;
  height: 1px !important;
  padding: 0 !important;
  margin: -1px !important;
  overflow: hidden !important;
  clip: rect(0, 0, 0, 0) !important;
  white-space: nowrap !important;
  border: 0 !important;
}
</style>
