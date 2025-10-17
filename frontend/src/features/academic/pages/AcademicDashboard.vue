<template>
  <section>
    <h1 class="h5 page-header">لوحة المدير الأكاديمي</h1>
    <p class="text-muted">مؤشرات جودة الحضور والأداء الأكاديمي. (إصدار تمهيدي)</p>

    <div class="row g-3">
      <div class="col-12 col-lg-4" v-for="i in 3" :key="i">
        <div class="card p-3">
          <div class="fw-bold">مؤشر أكاديمي #{{ i }}</div>
          <div class="text-muted small">سيتم سحب البيانات من API لاحقًا.</div>
        </div>
      </div>
    </div>
  </section>
</template>
<script setup lang="ts">
</script>
<style scoped>
.card { box-shadow: 0 6px 24px rgba(0,0,0,.06); border-radius: .75rem; }
</style>