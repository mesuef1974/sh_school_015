<template>
  <section>
    <h1 class="h5 page-header">لوحة منسق المادة</h1>
    <p class="text-muted">
      توزيع الغياب حسب المادة/المعلم/الشعبة. هذه الصفحة تمهيدية للاستفادة من صفحات الباك-إند
      الموجودة.
    </p>

    <div class="alert alert-secondary">
      لعرض البيانات القديمة مؤقتًا يمكنك استخدام روابط الباك-إند:
      <ul class="mb-0">
        <li>
          <a :href="backendUrl('/loads/')" target="_blank" rel="noopener noreferrer"
            >/loads/ — لوحة الأنصبة</a
          >
        </li>
        <li>
          <a :href="backendUrl('/loads/matrix/')" target="_blank" rel="noopener noreferrer"
            >/loads/matrix/ — مصفوفة المعلم × الصف</a
          >
        </li>
      </ul>
    </div>

    <div class="row g-3">
      <div class="col-12 col-lg-4" v-for="i in 3" :key="i">
        <div class="card p-3">
          <div class="fw-bold">مؤشر تمهيدي #{{ i }}</div>
          <div class="text-muted small">سيتم ربط هذا المؤشر بواجهة API لاحقًا.</div>
        </div>
      </div>
    </div>
  </section>
</template>
<script setup lang="ts">
import { backendUrl } from "../../../shared/config";
</script>
<style scoped>
.card {
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.06);
  border-radius: 0.75rem;
}
</style>
