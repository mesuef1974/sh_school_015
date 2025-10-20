<template>
  <section class="d-grid gap-3">
    <DsCard
      v-motion
      :initial="{ opacity: 0, y: -30 }"
      :enter="{ opacity: 1, y: 0, transition: { duration: 400 } }"
      :animate="false"
    >
      <div class="d-flex align-items-center gap-3">
        <Icon icon="solar:users-group-rounded-bold-duotone" class="text-4xl" style="color: var(--color-success)" />
        <div>
          <div class="text-xl font-bold">إدارة شؤون الطلبة</div>
          <div class="text-muted text-sm">روابط شؤون الطلبة</div>
        </div>
      </div>
    </DsCard>

    <div class="row g-3">
      <div
        v-motion
        :initial="{ opacity: 0, scale: 0.8 }"
        :enter="{ opacity: 1, scale: 1, transition: { duration: 400, delay: 100 } }"
        class="col-6 col-md-4 col-xl-3"
      >
        <IconTile
          :to="{ name: 'students-absence' }"
          icon="solar:user-minus-rounded-bold-duotone"
          title="غياب الطلبة"
          subtitle="إدارة ومراجعة"
          color="#2e7d32"
        />
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import IconTile from '../../widgets/IconTile.vue';
import DsCard from '../../components/ui/DsCard.vue';
</script>
