<template>
  <section class="d-grid gap-3 page-grid page-grid-wide" dir="rtl">
    <div class="d-flex align-items-center gap-2 mb-2 header-bar frame">
      <Icon :icon="tileMeta.icon" class="header-icon" width="28" height="28" :style="{ color: tileMeta.color }" />
      <div>
        <div class="fw-bold">{{ tileMeta.title }}</div>
        <div class="text-muted small" v-if="wingLabelFull">{{ wingLabelFull }}</div>
        <div class="text-muted small" v-else>مشرف الجناح — عرض مؤشرات الحضور لصفوف الجناح</div>
      </div>
      <span class="ms-auto"></span>
      <a :href="backendUrl('/wing/dashboard/')" target="_blank" rel="noopener" class="btn btn-outline-secondary btn-sm">
        <Icon icon="solar:box-minimalistic-open-bold-duotone" /> الصفحة القديمة
      </a>
    </div>

    <div class="card">
      <div class="card-body">
        <div class="d-flex align-items-center gap-2 mb-2">
          <Icon icon="solar:radar-2-bold-duotone" class="text-primary" width="22" height="22" />
          <h5 class="m-0 card-title-maroon">مؤشرات عامة (تمهيدي)</h5>
        </div>
        <div class="table-card">
          <table class="table table-hover align-middle">
            <thead>
              <tr>
                <th>الصف</th>
                <th>الحضور</th>
                <th>التأخر</th>
                <th>الحالة</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="i in 6" :key="i">
                <td>شعبة {{ i }}</td>
                <td>--%</td>
                <td>--</td>
                <td><span class="badge text-bg-secondary">قيد التطوير</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </section>
</template>
<script setup lang="ts">
import { Icon } from "@iconify/vue";
import { backendUrl } from "../../../shared/config";
import { onMounted, computed } from 'vue';
import { tiles } from "../../../home/icon-tiles.config";
const tileMeta = computed(() => tiles.find(t => t.to === "/attendance/wing/monitor") || { title: "مراقبة حضور الجناح", icon: "solar:radar-2-bold-duotone", color: "#0d47a1" });
import { useWingContext } from '../../../shared/composables/useWingContext';
const { ensureLoaded, wingLabelFull } = useWingContext();
onMounted(() => { ensureLoaded(); });
// لاحقًا: استدعاء API لمراقبة غياب الدور
</script>
<style scoped>
.table-card { margin-top: 0.5rem; }
.header-icon { font-size: 22px; }
</style>