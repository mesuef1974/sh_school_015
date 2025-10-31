<template>
  <section class="d-grid gap-3 page-grid page-grid-wide" dir="rtl">
    <div class="d-flex align-items-center gap-2 mb-2 header-bar frame">
      <Icon :icon="tileMeta.icon" class="header-icon" width="28" height="28" :style="{ color: tileMeta.color }" />
      <div>
        <div class="fw-bold">{{ tileMeta.title }}</div>
        <div class="text-muted small" v-if="wingLabelFull">{{ wingLabelFull }}</div>
        <div class="text-muted small" v-else>التنبيهات — شريط العنوان فقط (Placeholder)</div>
      </div>
      <span class="ms-auto"></span>
    </div>
  </section>
</template>
<script setup lang="ts">
import { Icon } from "@iconify/vue";
import { computed } from "vue";
import { tiles } from "../../../home/icon-tiles.config";
const tileMeta = computed(() => tiles.find((t) => t.to === "/wing/notifications") || { title: "التنبيهات", icon: "solar:bell-bing-bold-duotone", color: "#d35400" });
import { useWingContext } from "../../../shared/composables/useWingContext";
const { wingLabelFull } = useWingContext();
</script>
<style scoped>
.header-icon { font-size: 22px; }
</style>