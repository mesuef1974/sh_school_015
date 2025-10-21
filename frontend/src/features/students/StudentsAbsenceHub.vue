<template>
  <section class="d-grid gap-3 wide-95">
    <DsCard
      v-motion
      :initial="{ opacity: 0, y: -30 }"
      :enter="{ opacity: 1, y: 0, transition: { duration: 400 } }"
      :animate="false"
    >
      <div class="d-flex align-items-center gap-3">
        <Icon icon="solar:user-minus-rounded-bold-duotone" class="text-4xl" style="color: #8a1538" />
        <div>
          <div class="text-xl font-bold">غياب الطلبة</div>
          <div class="text-muted text-sm">إدارة شاملة للحضور والغياب مع تقارير تفصيلية وإحصائيات متقدمة</div>
        </div>
      </div>
    </DsCard>

    <!-- Quick Stats -->
    <div class="row g-3">
      <div class="col-6 col-md-3">
        <DsCard
          v-motion
          :initial="{ opacity: 0, scale: 0.8 }"
          :enter="{ opacity: 1, scale: 1, transition: { duration: 400, delay: 50 } }"
          :animate="false"
          :interactive="true"
        >
          <div class="text-center">
            <Icon icon="solar:calendar-mark-bold-duotone" class="text-3xl mb-2" style="color: var(--color-info)" />
            <div class="small text-muted mb-1">اليوم</div>
            <div class="h5 fw-bold mb-0">{{ todayDate }}</div>
          </div>
        </DsCard>
      </div>
      <div class="col-6 col-md-3">
        <DsCard
          v-motion
          :initial="{ opacity: 0, scale: 0.8 }"
          :enter="{ opacity: 1, scale: 1, transition: { duration: 400, delay: 100 } }"
          :animate="false"
          :interactive="true"
        >
          <div class="text-center">
            <Icon icon="solar:check-circle-bold-duotone" class="text-3xl mb-2" style="color: var(--color-success)" />
            <div class="small text-muted mb-1">نسبة الحضور</div>
            <div class="h5 fw-bold mb-0 text-success">--</div>
            <DsBadge variant="info" size="sm" class="mt-1">قريباً</DsBadge>
          </div>
        </DsCard>
      </div>
      <div class="col-6 col-md-3">
        <DsCard
          v-motion
          :initial="{ opacity: 0, scale: 0.8 }"
          :enter="{ opacity: 1, scale: 1, transition: { duration: 400, delay: 150 } }"
          :animate="false"
          :interactive="true"
        >
          <div class="text-center">
            <Icon icon="solar:close-circle-bold-duotone" class="text-3xl mb-2" style="color: var(--color-danger)" />
            <div class="small text-muted mb-1">الغياب اليوم</div>
            <div class="h5 fw-bold mb-0 text-danger">--</div>
            <DsBadge variant="info" size="sm" class="mt-1">قريباً</DsBadge>
          </div>
        </DsCard>
      </div>
      <div class="col-6 col-md-3">
        <DsCard
          v-motion
          :initial="{ opacity: 0, scale: 0.8 }"
          :enter="{ opacity: 1, scale: 1, transition: { duration: 400, delay: 200 } }"
          :animate="false"
          :interactive="true"
        >
          <div class="text-center">
            <Icon icon="solar:clock-circle-bold-duotone" class="text-3xl mb-2" style="color: var(--color-warning)" />
            <div class="small text-muted mb-1">المتأخرون</div>
            <div class="h5 fw-bold mb-0 text-warning">--</div>
            <DsBadge variant="info" size="sm" class="mt-1">قريباً</DsBadge>
          </div>
        </DsCard>
      </div>
    </div>

    <!-- Main Actions -->
    <div class="row g-3">
      <div
        v-for="(tile, index) in tiles"
        :key="tile.name"
        class="col-6 col-md-4 col-xl-3"
        v-motion
        :initial="{ opacity: 0, y: 30 }"
        :enter="{ opacity: 1, y: 0, transition: { duration: 400, delay: 250 + (index * 50) } }"
      >
        <IconTile
          :to="tile.to"
          :icon="tile.icon"
          :title="tile.title"
          :subtitle="tile.subtitle"
          :color="tile.color"
        />
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import IconTile from '../../widgets/IconTile.vue';
import DsCard from '../../components/ui/DsCard.vue';
import DsBadge from '../../components/ui/DsBadge.vue';

const todayDate = computed(() => {
  const days = ['الأحد', 'الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت'];
  const date = new Date();
  return `${days[date.getDay()]} ${date.getDate()}/${date.getMonth() + 1}`;
});

const tiles = [
  {
    name: 'attendance',
    to: { name: 'teacher-attendance' },
    icon: 'solar:clipboard-check-bold-duotone',
    title: 'تسجيل الغياب',
    subtitle: 'تسجيل حضور وغياب اليوم',
    color: '#8a1538'
  },
  {
    name: 'history',
    to: { name: 'teacher-attendance-history' },
    icon: 'solar:history-bold-duotone',
    title: 'سجل الغياب',
    subtitle: 'بحث وتصدير السجلات',
    color: '#b23a48'
  },
  {
    name: 'procedures',
    to: { name: 'attendance-procedures' },
    icon: 'solar:document-text-bold-duotone',
    title: 'إجراءات الغياب',
    subtitle: 'تنبيهات ومتابعة الحالات',
    color: '#6a1b9a'
  },
  {
    name: 'stats',
    to: { name: 'stats' },
    icon: 'solar:chart-2-bold-duotone',
    title: 'الإحصائيات',
    subtitle: 'نسب وتحليلات تفصيلية',
    color: '#1976d2'
  }
];
</script>

<style scoped>
.wide-95 {
  width: min(95vw, 95%);
  margin-inline: auto;
}
</style>