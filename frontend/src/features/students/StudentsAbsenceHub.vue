<template>
  <section class="d-grid gap-3">
    <header class="auto-card p-3 d-flex align-items-center gap-3">
      <Icon icon="fa6-solid:user-minus" style="font-size:28px;color:#8a1538" />
      <div>
        <div class="fw-bold">غياب الطلبة</div>
        <div class="text-muted small">روابط المهام المتعلقة بالغياب</div>
      </div>
      <span class="ms-auto"></span>
    </header>

    <div class="row g-3">
      <div class="col-6 col-md-4 col-xl-3">
        <IconTile
          :to="{ name: 'teacher-attendance' }"
          icon="fa6-solid:clipboard-check"
          title="تسجيل الغياب"
          subtitle="لليوم المحدد"
          color="#8a1538"
        />
      </div>
      <div class="col-6 col-md-4 col-xl-3">
        <IconTile
          :to="{ name: 'teacher-attendance-history' }"
          icon="fa6-regular:calendar-days"
          title="سجل الغياب"
          subtitle="بحث وتصدير"
          color="#b23a48"
        />
      </div>
      <div class="col-6 col-md-4 col-xl-3">
        <IconTile
          :to="{ name: 'attendance-procedures' }"
          icon="fa6-solid:clipboard-list"
          title="إجراءات الغياب"
          subtitle="تنبيهات وتتبّع"
          color="#6a1b9a"
        />
      </div>
      <div class="col-6 col-md-4 col-xl-3">
        <IconTile
          :to="{ name: 'stats' }"
          icon="fa6-solid:chart-simple"
          title="الإحصائيات"
          subtitle="نِسَب وملخصات"
          color="#b23a48"
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