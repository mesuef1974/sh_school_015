<template>
  <section class="d-grid gap-3">
    <header class="auto-card p-3 d-flex align-items-center gap-3">
      <Icon icon="fa6-solid:user-graduate" style="font-size:28px;color:#2e7d32" />
      <div>
        <div class="fw-bold">إدارة شؤون الطلبة</div>
        <div class="text-muted small">روابط شؤون الطلبة</div>
      </div>
      <span class="ms-auto"></span>
    </header>

    <div class="row g-3">
      <div class="col-6 col-md-4 col-xl-3">
        <IconTile
          :to="{ name: 'students-absence' }"
          icon="fa6-solid:user-minus"
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
</script>

<style scoped>
</style>