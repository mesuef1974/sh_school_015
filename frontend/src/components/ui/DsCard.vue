<template>
  <div
    :class="cardClasses"
    v-motion
    :initial="animate ? { opacity: 0, y: 20 } : undefined"
    :enter="animate ? { opacity: 1, y: 0, transition: { duration: 400, delay: delay } } : undefined"
  >
    <div v-if="$slots.header || title" class="ds-card-header">
      <slot name="header">
        <h3 class="ds-card-title">{{ title }}</h3>
      </slot>
    </div>

    <div class="ds-card-body">
      <slot />
    </div>

    <div v-if="$slots.footer" class="ds-card-footer">
      <slot name="footer" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

interface Props {
  title?: string;
  interactive?: boolean;
  noPadding?: boolean;
  animate?: boolean;
  delay?: number;
}

const props = withDefaults(defineProps<Props>(), {
  interactive: false,
  noPadding: false,
  animate: true,
  delay: 0,
});

const cardClasses = computed(() => {
  const classes = ['ds-card'];
  if (props.interactive) classes.push('ds-card-interactive');
  if (props.noPadding) classes.push('ds-card-no-padding');
  return classes.join(' ');
});
</script>

<style scoped>
.ds-card-header {
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid #e5e7eb;
}

.ds-card-title {
  margin: 0;
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  color: var(--maron-primary);
}

.ds-card-body {
  /* Body styles */
}

.ds-card-footer {
  margin-top: var(--space-4);
  padding-top: var(--space-4);
  border-top: 1px solid #e5e7eb;
}

.ds-card-no-padding {
  padding: 0;
}

.ds-card-no-padding .ds-card-header {
  padding: var(--space-6);
  padding-bottom: var(--space-4);
  margin-bottom: 0;
}

.ds-card-no-padding .ds-card-body {
  padding: var(--space-6);
  padding-top: 0;
}

.ds-card-no-padding .ds-card-footer {
  padding: var(--space-6);
  padding-top: var(--space-4);
  margin-top: 0;
}
</style>
