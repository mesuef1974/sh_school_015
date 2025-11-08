<template>
  <span class="ds-icon" :style="styleVars" :aria-hidden="label ? 'false' : 'true'" :role="label ? 'img' : undefined" :aria-label="label || undefined">
    <!-- Inline SVG printer icon (currentColor) -->
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M6 8V3.75C6 3.33579 6.33579 3 6.75 3H17.25C17.6642 3 18 3.33579 18 3.75V8" stroke="currentColor" stroke-width="1.5"/>
      <rect x="3" y="8" width="18" height="8" rx="2" stroke="currentColor" stroke-width="1.5"/>
      <rect x="7" y="14" width="10" height="7" rx="1" fill="currentColor" opacity="0.12"/>
      <rect x="7" y="14" width="10" height="7" rx="1" stroke="currentColor" stroke-width="1.5"/>
      <rect x="8.75" y="16" width="6.5" height="1.5" rx="0.75" fill="currentColor"/>
      <circle cx="18" cy="11" r="1" fill="currentColor"/>
    </svg>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ size?: number; color?: string; label?: string }>()

const styleVars = computed(() => ({
  '--icon-size': props.size ? `${props.size}px` : '1em',
  '--icon-color': props.color || 'currentColor',
}) as Record<string, string>)
</script>

<style scoped>
.ds-icon { display: inline-flex; align-items: center; justify-content: center; line-height: 1; color: var(--icon-color); }
.ds-icon svg { width: var(--icon-size); height: var(--icon-size); display: block; }
</style>
