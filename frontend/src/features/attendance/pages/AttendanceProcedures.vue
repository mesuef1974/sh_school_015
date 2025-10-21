<template>
  <section class="d-grid gap-3 full-bleed">
    <header class="auto-card p-3 d-flex align-items-center gap-3">
      <Icon icon="fa6-solid:clipboard-list" style="font-size:28px;color:#6a1b9a" />
      <div>
        <div class="fw-bold">إجراءات الغياب</div>
        <div class="text-muted small">صفحة مبدئية لتجميع سياسات وتنبيهات ومتابعات الغياب</div>
      </div>
      <span class="ms-auto"></span>
    </header>

    <div class="auto-card p-3">
      <p class="mb-2">سيتم هنا لاحقًا عرض إجراءات الغياب مثل:</p>
      <ul class="mb-0">
        <li>تنبيهات أولية ورسائل لأولياء الأمور.</li>
        <li>رفع الحالات إلى الإدارة/المرشد الطلابي.</li>
        <li>تتبّع المخالفات وتاريخ الإجراءات.</li>
      </ul>
    </div>
  </section>
</template>

<script setup lang="ts">
</script>

<style scoped>
.full-bleed { width: 100vw; margin-inline: calc(50% - 50vw); }
</style>