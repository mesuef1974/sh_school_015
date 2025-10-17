<template>
  <section>
    <div class="table-hero my-2 d-flex align-items-center gap-2">
      <img :src="expHead" alt="" style="height:40px" />
      <div>
        <div class="title">لوحة مشرف الجناح</div>
        <div class="muted">نظرة عامة على الحضور والانضباط لصفوف الجناح</div>
      </div>
      <span class="ms-auto"></span>
      <a class="btn btn-outline-secondary" :href="backendUrl('/wing/dashboard/')" target="_blank" rel="noopener noreferrer">فتح اللوحة القديمة</a>
    </div>

    <div class="row g-3">
      <div class="col-12 col-md-6">
        <div class="card p-3">
          <div class="d-flex justify-content-between align-items-center">
            <div>
              <div class="fw-bold">نسبة الحضور اليوم</div>
              <div class="text-muted small">Placeholder — سيتم توصيلها بواجهة API لاحقًا</div>
            </div>
            <div class="display-6">--%</div>
          </div>
        </div>
      </div>
      <div class="col-12 col-md-6">
        <div class="card p-3">
          <div class="fw-bold">أكثر الصفوف تأخرًا</div>
          <ul class="mb-0 small text-muted">
            <li>سيتم تحميلها لاحقًا من API</li>
          </ul>
        </div>
      </div>
    </div>
  </section>
</template>
<script setup lang="ts">
import { backendUrl } from '../../../shared/config';
// لاحقًا سنستهلك APIs خاصة بلوحة الجناح
</script>
<style scoped>
.card { box-shadow: 0 6px 24px rgba(0,0,0,.06); border-radius: .75rem; }
</style>