<template>
  <div class="d-flex align-items-center gap-2 flex-wrap legend" dir="rtl">
    <span class="att-chip att-status present">حاضر</span>
    <span class="att-chip att-status late">متأخر</span>
    <span class="att-chip att-status excused">إذن خروج/بعذر (حصة)</span>
    <span class="att-chip att-status absent">غائب (حصة)</span>
    <span class="att-chip att-status runaway">هروب</span>
    <span class="att-chip att-status left_early">انصراف مبكر</span>
    <span class="att-chip day-state excused">بعذر (يوم كامل)</span>
    <span class="att-chip day-state unexcused">بدون عذر (يوم كامل)</span>
    <span class="att-chip day-state none">غير محسوب (يوم)</span>
  </div>
</template>

<script setup lang="ts">
// purely presentational
</script>

<style scoped>
.legend :deep(.att-chip) {
  font-weight: 600;
}
</style>
