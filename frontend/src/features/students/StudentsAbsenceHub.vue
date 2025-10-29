<template>
  <section class="d-grid gap-3">
    <DsCard
      v-motion
      :initial="{ opacity: 0, y: -30 }"
      :enter="{ opacity: 1, y: 0, transition: { duration: 400 } }"
      :animate="false"
    >
      <div class="d-flex align-items-center gap-3">
        <Icon
          icon="solar:user-minus-rounded-bold-duotone"
          class="text-4xl"
          style="color: #8a1538"
        />
        <div>
          <div class="text-xl font-bold">غياب الطلبة</div>
          <div class="text-muted text-sm">
            إدارة شاملة للحضور والغياب مع تقارير تفصيلية وإحصائيات متقدمة
          </div>
        </div>
      </div>
    </DsCard>

    <!-- Main Actions -->
    <div class="cards-grid-7">
      <div
        v-for="(tile, index) in tiles"
        :key="tile.name"
        v-motion
        :initial="{ opacity: 0, y: 30 }"
        :enter="{ opacity: 1, y: 0, transition: { duration: 400, delay: 250 + index * 50 } }"
      >
        <IconTile
          :to="tile.to"
          :icon="tile.icon"
          :title="tile.title"
          :subtitle="tile.subtitle"
          :color="tile.color"
          compact
        />
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import IconTile from "../../widgets/IconTile.vue";
import DsCard from "../../components/ui/DsCard.vue";

const tiles = [
  {
    name: "attendance",
    to: { name: "teacher-attendance" },
    icon: "solar:clipboard-check-bold-duotone",
    title: "تسجيل الغياب",
    subtitle: "تسجيل حضور وغياب اليوم",
    color: "#8a1538",
  },
  {
    name: "history",
    to: { name: "teacher-attendance-history" },
    icon: "solar:history-bold-duotone",
    title: "سجل الغياب",
    subtitle: "بحث وتصدير السجلات",
    color: "#b23a48",
  },
  {
    name: "procedures",
    to: { name: "attendance-procedures" },
    icon: "solar:document-text-bold-duotone",
    title: "إجراءات الغياب",
    subtitle: "تنبيهات ومتابعة الحالات",
    color: "#6a1b9a",
  },
  {
    name: "stats",
    to: { name: "stats" },
    icon: "solar:chart-2-bold-duotone",
    title: "الإحصائيات",
    subtitle: "نسب وتحليلات تفصيلية",
    color: "#1976d2",
  },
];
</script>

<style scoped>
.wide-95 {
  width: min(95vw, 95%);
  margin-inline: auto;
}
</style>
