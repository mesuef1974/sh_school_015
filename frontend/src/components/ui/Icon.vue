<template>
  <span
    :class="['ds-icon', sizeClass, { block }]"
    :style="styleVars"
    v-bind="rootAria"
  >
    <component v-if="isIconify" :is="IconifyIcon" :icon="icon" />
    <span v-else v-html="svgHtml" :aria-hidden="!label"></span>
  </span>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watchEffect } from "vue";
import { Icon as IconifyIcon } from "@iconify/vue";
import { getSchoolIconSvg } from "../../shared/icons/useIcons";

const props = defineProps<{
  icon: string; // examples: 'sc:teacher', 'solar:calendar-bold-duotone', 'fa6-solid:house'
  size?: number | string;
  color?: string;
  block?: boolean;
  label?: string; // Optional: when provided, icon becomes functional (named)
}>();

const isSchool = computed(() => props.icon?.startsWith("sc:"));
const isIconify = computed(() => !isSchool.value);
const name = computed(() => props.icon);
const svgHtml = ref<string>("");

// A11y defaults: decorative by default; if label is provided, expose as role="img" with aria-label
const rootAria = computed(() =>
  props.label
    ? ({ role: "img", "aria-label": props.label, "aria-hidden": "false" } as Record<string, string>)
    : ({ "aria-hidden": "true" } as Record<string, string>)
);

const sizeClass = computed(() => {
  if (typeof props.size === "string") return props.size;
  return "";
});

const styleVars = computed(() => {
  const size = typeof props.size === "number" ? `${props.size}px` : undefined;
  return {
    "--icon-size": size || undefined,
    "--icon-color": props.color || "currentColor",
  } as Record<string, string>;
});

async function ensureSchoolSvg() {
  if (!isSchool.value) return;
  const n = name.value.slice(3);
  svgHtml.value = (await getSchoolIconSvg(n)) || "";
}

onMounted(() => {
  ensureSchoolSvg();
});
watchEffect(() => {
  ensureSchoolSvg();
});
</script>

<style scoped>
.ds-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  color: var(--icon-color, currentColor);
}
.ds-icon > span:deep(svg),
.ds-icon :deep(svg) {
  width: var(--icon-size, 1em);
  height: var(--icon-size, 1em);
  display: block;
}
/* Standard sizes */
.ds-icon.text-sm {
  --icon-size: 14px;
}
.ds-icon.text-base {
  --icon-size: 16px;
}
.ds-icon.text-lg {
  --icon-size: 20px;
}
.ds-icon.text-xl {
  --icon-size: 24px;
}
</style>