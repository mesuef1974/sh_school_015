<template>
  <section class="container py-4">
    <h1 data-testid="grades-index" class="h3 mb-3">الدرجات</h1>
    <p class="text-muted" data-testid="grades-empty">لا توجد بيانات درجات للعرض حاليًا.</p>
    <div class="mt-3">
      <button data-testid="grades-add" class="btn btn-primary" type="button" @click="openDialog = true">
        إدخال درجة
      </button>
    </div>

    <dialog v-if="openDialog" data-testid="grades-dialog" class="grades-dialog">
      <div class="p-3">
        <h2 class="h5 mb-3">إدخال درجة (تجريبي)</h2>
        <p class="mb-3">هذه نافذة تجريبية بدون ربط بالخلفية.
          أُضيفت لأغراض البدء السريع بالـ E2E.</p>
        <div class="d-flex gap-2 justify-content-end">
          <button class="btn btn-secondary" @click="openDialog = false">إغلاق</button>
        </div>
      </div>
    </dialog>
  </section>
</template>

<script setup lang="ts">
import { ref } from "vue";
const openDialog = ref(false);
</script>

<style scoped>
.grades-dialog {
  border: none;
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.18);
}
</style>
