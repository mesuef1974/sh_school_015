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
    v-bind="a11yAttrs"
    @click="handleClick"
  >
    <Icon v-if="loading" icon="mdi:loading" class="animate-spin" />
    <Icon v-else-if="icon" :icon="icon" />
    <slot />
  </component>
</template>

<script setup lang="ts">
import { computed, useSlots } from "vue";

interface Props {
  variant?: "primary" | "success" | "danger" | "warning" | "info" | "outline";
  size?: "sm" | "md" | "lg";
  icon?: string;
  loading?: boolean;
  disabled?: boolean;
  to?: string | object;
  href?: string;
  type?: "button" | "submit" | "reset";
  label?: string; // A11y: used when button is icon-only
}

const props = withDefaults(defineProps<Props>(), {
  variant: "primary",
  size: "md",
  type: "button",
});

const emit = defineEmits<{
  click: [event: MouseEvent];
}>();

const slots = useSlots();

// Heuristic: if default slot missing or renders empty text nodes → icon-only
const isIconOnly = computed(() => {
  const s = slots.default?.();
  if (!s || s.length === 0) return true;
  return s.every((v) => {
    const c = (v.children as any);
    return typeof c === "string" ? c.trim().length === 0 : false;
  });
});

if (import.meta.env.DEV && isIconOnly.value && !props.label) {
  console.warn("[A11y] DsButton with icon-only requires `label` for aria-label/title.");
}

const a11yAttrs = computed(() => {
  if (isIconOnly.value) {
    return props.label ? { "aria-label": props.label, title: props.label } : {};
  }
  return {};
});

const buttonClasses = computed(() => {
  const classes = ["ds-btn"];

  // Variant
  if (props.variant === "primary") classes.push("ds-btn-primary");
  else if (props.variant === "success") classes.push("ds-btn-success");
  else if (props.variant === "danger") classes.push("ds-btn-danger");

  // Size
  if (props.size === "sm") classes.push("ds-btn-sm");
  else if (props.size === "lg") classes.push("ds-btn-lg");

  return classes.join(" ");
});

const handleClick = (event: MouseEvent) => {
  if (!props.disabled && !props.loading) {
    emit("click", event);
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
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>