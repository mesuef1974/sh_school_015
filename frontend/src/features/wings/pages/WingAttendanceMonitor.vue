<template>
  <section>
    <h1 class="h5 page-header">متابعة الغياب — مشرف الجناح</h1>
    <p class="text-muted">هذه الصفحة ستعرض حالة الغياب اليومية لجميع الصفوف في الجناح مع مؤشرات فورية. الإصدار الحالي تمهيدي.</p>

    <div class="alert alert-info d-flex align-items-center gap-2">
      <i class="bi bi-box-arrow-up-right"></i>
      <span>يمكنك مؤقتًا استخدام الصفحة القديمة:</span>
      <a :href="backendUrl('/wing/dashboard/')" target="_blank" rel="noopener noreferrer">/wing/dashboard/</a>
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
  </section>
</template>
<script setup lang="ts">
import { backendUrl } from '../../../shared/config';
// لاحقًا: استدعاء API لمراقبة غياب الدور
</script>
<style scoped>
.table-card { margin-top: .5rem; }
</style>