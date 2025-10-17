<template>
  <section>
    <h1 class="h5 page-header">لوحة مدير المدرسة</h1>
    <p class="text-muted">مؤشرات عامة للحضور والانضباط، وروابط للتقارير. (نسخة أولية)</p>

    <div class="row g-3">
      <div class="col-12 col-md-4">
        <div class="card p-3">
          <div class="fw-bold">نسبة الحضور اليوم</div>
          <div class="display-6">--%</div>
        </div>
      </div>
      <div class="col-12 col-md-4">
        <div class="card p-3">
          <div class="fw-bold">عدد الغياب</div>
          <div class="display-6">--</div>
        </div>
      </div>
      <div class="col-12 col-md-4">
        <div class="card p-3">
          <div class="fw-bold">أعلى الصفوف التزامًا</div>
          <ul class="small text-muted mb-0"><li>سيضاف لاحقًا</li></ul>
        </div>
      </div>
    </div>

    <div class="mt-3">
      <a class="btn btn-outline-secondary me-2" :href="backendUrl('/data/')" target="_blank" rel="noopener noreferrer">قواعد البيانات (قديمة)</a>
      <a class="btn btn-outline-secondary" :href="backendUrl('/loads/')" target="_blank" rel="noopener noreferrer">لوحة الأنصبة (قديمة)</a>
    </div>
  </section>
</template>
<script setup lang="ts">
import { backendUrl } from '../../../shared/config';
</script>
<style scoped>
.card { box-shadow: 0 6px 24px rgba(0,0,0,.06); border-radius: .75rem; }
</style>