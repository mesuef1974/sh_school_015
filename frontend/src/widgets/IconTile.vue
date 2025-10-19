<template>
  <component
    :is="to ? 'RouterLink' : 'a'"
    :to="to"
    :href="href"
    class="tile"
    :style="{ '--tile-color': color || '#7a6' }"
    target="_self"
    rel="noopener"
    :aria-label="title"
  >
    <div class="tile-icon">
      <Icon :icon="icon" />
    </div>
    <div class="tile-text">
      <div class="tile-title">{{ title }}</div>
      <div v-if="subtitle" class="tile-subtitle">{{ subtitle }}</div>
    </div>
    <div v-if="badge !== undefined && badge !== null" class="tile-badge">{{ badge }}</div>
  </component>
</template>

<script setup lang="ts">
defineProps<{ to?: string; href?: string; icon: string; title: string; subtitle?: string; color?: string; badge?: string | number }>();
</script>

<style scoped>
.tile {
  display:flex;
  flex-direction: column;
  gap:10px;
  align-items:center;
  justify-content: center;
  width: 75%; /* تصغير مساحة البوكس بنسبة 25% */
  margin-inline: auto; /* توسيط داخل العمود */
  aspect-ratio: 1 / 1; /* مربعة وليست مستطيلة */
  padding:16px;
  border-radius:16px;
  background: rgba(255,255,255,0.5); /* خلفية بيضاء بشفافية 50% */
  -webkit-backdrop-filter: blur(8px);
  backdrop-filter: blur(8px);
  border:1px solid rgba(0,0,0,0.06);
  position:relative;
  transition:transform .18s ease, box-shadow .18s ease;
  text-decoration:none; color:inherit;
  box-shadow: 0 6px 18px rgba(0,0,0,.05);
  overflow: hidden; /* لضمان بقاء الشكل مربع مع الحواف */
}
.tile:hover { transform: translateY(-3px); box-shadow: 0 10px 26px rgba(0,0,0,.08); }
.tile:focus-within { outline: 2px solid rgba(138,21,56,0.25); outline-offset: 2px; }
.tile-icon {
  width:72px; height:72px; display:grid; place-items:center; border-radius:18px; /* تكبير الحاضنة 50% */
  /* حاضنة الأيقونة بلون شفاف بنسبة 50% */
  background: color-mix(in oklab, var(--tile-color, #7a6) 50%, transparent 50%);
  color: var(--tile-color, #7a6);
  font-size: 36px; /* تكبير الأيقونة 50% */
}
.tile-text { text-align: center; max-width: 90%; }
.tile-title { font-weight:700; line-height: 1.2; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.tile-subtitle { font-size:.85rem; color:#666; line-height:1.2; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.tile-badge { position:absolute; inset-inline-end:10px; top:10px; background:#c62828; color:#fff; border-radius:999px; padding:2px 8px; font-size:.75rem; }
</style>