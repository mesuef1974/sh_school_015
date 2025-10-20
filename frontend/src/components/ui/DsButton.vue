<template>
  <component
    :is="to ? 'router-link' : href ? 'a' : 'button'"
    :to="to"
    :href="href"
    :type="type"
    :disabled="disabled || loading"
    :class="buttonClasses"
    :aria-busy="loading"
    :aria-disabled="disabled"
    @click="handleClick"
  >
    <Icon v-if="loading" icon="mdi:loading" class="animate-spin" />
    <Icon v-else-if="icon" :icon="icon" />
    <slot />
  </component>
</template>

<script setup lang="ts">
import { computed } from 'vue';

interface Props {
  variant?: 'primary' | 'success' | 'danger' | 'warning' | 'info' | 'outline';
  size?: 'sm' | 'md' | 'lg';
  icon?: string;
  loading?: boolean;
  disabled?: boolean;
  to?: string | object;
  href?: string;
  type?: 'button' | 'submit' | 'reset';
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'primary',
  size: 'md',
  type: 'button',
});

const emit = defineEmits<{
  click: [event: MouseEvent];
}>();

const buttonClasses = computed(() => {
  const classes = ['ds-btn'];

  // Variant
  if (props.variant === 'primary') classes.push('ds-btn-primary');
  else if (props.variant === 'success') classes.push('ds-btn-success');
  else if (props.variant === 'danger') classes.push('ds-btn-danger');

  // Size
  if (props.size === 'sm') classes.push('ds-btn-sm');
  else if (props.size === 'lg') classes.push('ds-btn-lg');

  return classes.join(' ');
});

const handleClick = (event: MouseEvent) => {
  if (!props.disabled && !props.loading) {
    emit('click', event);
  }
};
</script>

<style scoped>
.ds-btn-sm {
  padding: var(--space-2) var(--space-4);
  font-size: var(--font-size-sm);
}

.ds-btn-lg {
  padding: var(--space-4) var(--space-8);
  font-size: var(--font-size-lg);
}

.animate-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
