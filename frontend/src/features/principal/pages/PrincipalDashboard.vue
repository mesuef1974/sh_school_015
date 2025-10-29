<template>
  <section class="d-grid gap-3">
    <DsCard
      v-motion
      :initial="{ opacity: 0, y: -30 }"
      :enter="{ opacity: 1, y: 0, transition: { duration: 400 } }"
      :animate="false"
    >
      <div class="d-flex align-items-center gap-3">
        <Icon
          icon="solar:crown-bold-duotone"
          class="text-4xl"
          style="color: var(--maron-primary)"
        />
        <div>
          <div class="text-xl font-bold">لوحة مدير المدرسة</div>
          <div class="text-muted text-sm">مؤشرات عامة للحضور والانضباط، وروابط للتقارير</div>
        </div>
      </div>
    </DsCard>

    <div class="row g-3">
      <div class="col-12 col-md-4">
        <DsCard
          v-motion
          :initial="{ opacity: 0, scale: 0.8 }"
          :enter="{ opacity: 1, scale: 1, transition: { duration: 400, delay: 100 } }"
          :animate="false"
          :interactive="true"
        >
          <div class="text-center">
            <Icon
              icon="solar:chart-2-bold-duotone"
              class="text-4xl mb-3"
              style="color: var(--color-success)"
            />
            <div class="fw-bold mb-2">نسبة الحضور اليوم</div>
            <div class="display-6 fw-bold" style="color: var(--color-success)">--%</div>
            <DsBadge variant="info" class="mt-2">قريباً</DsBadge>
          </div>
        </DsCard>
      </div>

      <div class="col-12 col-md-4">
        <DsCard
          v-motion
          :initial="{ opacity: 0, scale: 0.8 }"
          :enter="{ opacity: 1, scale: 1, transition: { duration: 400, delay: 200 } }"
          :animate="false"
          :interactive="true"
        >
          <div class="text-center">
            <Icon
              icon="solar:user-cross-bold-duotone"
              class="text-4xl mb-3"
              style="color: var(--color-danger)"
            />
            <div class="fw-bold mb-2">عدد الغياب</div>
            <div class="display-6 fw-bold" style="color: var(--color-danger)">--</div>
            <DsBadge variant="info" class="mt-2">قريباً</DsBadge>
          </div>
        </DsCard>
      </div>

      <div class="col-12 col-md-4">
        <DsCard
          v-motion
          :initial="{ opacity: 0, scale: 0.8 }"
          :enter="{ opacity: 1, scale: 1, transition: { duration: 400, delay: 300 } }"
          :animate="false"
          :interactive="true"
        >
          <div class="text-center">
            <Icon
              icon="solar:cup-star-bold-duotone"
              class="text-4xl mb-3"
              style="color: var(--maron-accent)"
            />
            <div class="fw-bold mb-2">أعلى الصفوف التزامًا</div>
            <ul class="list-unstyled small text-muted mb-0 mt-3">
              <li>سيضاف لاحقًا</li>
            </ul>
            <DsBadge variant="info" class="mt-2">قريباً</DsBadge>
          </div>
        </DsCard>
      </div>
    </div>

    <DsCard
      v-motion
      :initial="{ opacity: 0, y: 30 }"
      :enter="{ opacity: 1, y: 0, transition: { duration: 400, delay: 400 } }"
      title="روابط سريعة"
      :animate="false"
    >
      <div class="d-flex gap-3 flex-wrap">
        <DsButton
          variant="outline"
          icon="solar:database-bold-duotone"
          :href="backendUrl('/data/')"
          target="_blank"
        >
          قواعد البيانات (قديمة)
        </DsButton>
        <DsButton
          variant="outline"
          icon="solar:document-text-bold-duotone"
          :href="backendUrl('/loads/')"
          target="_blank"
        >
          لوحة الأنصبة (قديمة)
        </DsButton>
      </div>
    </DsCard>
  </section>
</template>

<script setup lang="ts">
import { backendUrl } from "../../../shared/config";
import DsButton from "../../../components/ui/DsButton.vue";
import DsCard from "../../../components/ui/DsCard.vue";
import DsBadge from "../../../components/ui/DsBadge.vue";
</script>
