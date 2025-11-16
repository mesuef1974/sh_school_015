<template>
  <section class="d-grid gap-3 use-98vw">
    <header class="auto-card frame p-3 d-flex align-items-center gap-3">
      <img :src="logoSrc" alt="" style="height: 48px" />
      <div class="fw-bold">لوحة منسق المادة</div>
      <span class="ms-auto small text-muted">على نمط لوحة المعلم</span>
    </header>

    <div class="cards-grid-7 tile-grid">
      <div v-for="t in tiles" :key="t.id">
        <IconTile
          :to="t.to"
          :href="t.href"
          :icon="t.icon"
          :title="t.title"
          :subtitle="t.subtitle"
          :color="t.color"
          compact
        />
      </div>
    </div>

    <div class="auto-card frame p-3">
      <div class="fw-bold mb-1">روابط مساندة (من الباك-إند)</div>
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
  </section>

</template>
<script setup lang="ts">
import IconTile from "../../../widgets/IconTile.vue";
import { backendUrl } from "../../../shared/config";

const logoSrc = "/assets/img/logo.png";

// بلاطات المنسق — مختارة لتخدم احتياجات المنسق مباشرة، بنفس نمط بلاطات المعلم
const tiles = [
  {
    id: "subject_loads",
    title: "لوحة الأنصبة",
    subtitle: "التوزيع حسب المادة/المعلم",
    href: backendUrl("/loads/"),
    icon: "solar:graph-new-bold-duotone",
    color: "#2e7d32",
  },
  {
    id: "subject_matrix",
    title: "مصفوفة المعلم × الصف",
    subtitle: "عرض تفصيلي للشُعب",
    href: backendUrl("/loads/matrix/"),
    icon: "solar:table-bold-duotone",
    color: "#1565c0",
  },
  {
    id: "eval_by_coordinator",
    title: "تقييمات المنسق",
    subtitle: "مؤشرات ومراجعات",
    href: backendUrl("/evaluations/coordinator"),
    icon: "solar:star-bold-duotone",
    color: "#8a1538",
  },
];
</script>
<style scoped>
/* محاذاة نمط البلاطات كما في الصفحة الرئيسية */
.tile-grid > div { position: relative; }
.tile-grid .tile { width: 70% !important; margin-inline: auto; border: 2px solid var(--maron-primary, #8a1538) !important; }
.tile-grid .tile-icon { border-color: var(--maron-primary, #8a1538) !important; background: rgba(138, 21, 56, 0.06); }
</style>
