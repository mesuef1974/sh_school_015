<template>
  <span :class="badgeClasses">
    <Icon v-if="icon" :icon="icon" class="badge-icon" />
    <slot />
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue';

interface Props {
  variant?: 'success' | 'warning' | 'danger' | 'info';
  icon?: string;
  size?: 'sm' | 'md' | 'lg';
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'info',
  size: 'md',
});

const badgeClasses = computed(() => {
  const classes = ['ds-badge'];

  // Variant
  if (props.variant === 'success') classes.push('ds-badge-success');
  else if (props.variant === 'warning') classes.push('ds-badge-warning');
  else if (props.variant === 'danger') classes.push('ds-badge-danger');
  else if (props.variant === 'info') classes.push('ds-badge-info');

  // Size
  if (props.size === 'sm') classes.push('ds-badge-sm');
  else if (props.size === 'lg') classes.push('ds-badge-lg');

  return classes.join(' ');
});
</script>

<style scoped>
.badge-icon {
  font-size: 1em;
}

.ds-badge-sm {
  padding: 0 var(--space-2);
  font-size: 0.625rem;
}

.ds-badge-lg {
  padding: var(--space-2) var(--space-4);
  font-size: var(--font-size-sm);
}
</style>
