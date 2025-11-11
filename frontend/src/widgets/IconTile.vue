<template>
  <RouterLink v-if="to" :to="to" class="tile" :class="[compact ? 'tile--compact' : '']" :style="{ '--tile-color': color || '#7a6' }" :aria-label="title">
    <div class="tile-icon">
      <Icon :icon="icon" />
    </div>
    <div class="tile-text">
      <div class="tile-title">{{ title }}</div>
      <div v-if="subtitle" class="tile-subtitle">{{ subtitle }}</div>
    </div>
    <div v-if="badge !== undefined && badge !== null" class="tile-badge">{{ badge }}</div>
  </RouterLink>
  <a v-else :href="href || 'javascript:void(0)'" class="tile" :class="[compact ? 'tile--compact' : '']" :style="{ '--tile-color': color || '#7a6' }" :aria-label="title">
    <div class="tile-icon">
      <Icon :icon="icon" />
    </div>
    <div class="tile-text">
      <div class="tile-title">{{ title }}</div>
      <div v-if="subtitle" class="tile-subtitle">{{ subtitle }}</div>
    </div>
    <div v-if="badge !== undefined && badge !== null" class="tile-badge">{{ badge }}</div>
  </a>
</template>

<script setup lang="ts">
defineProps<{
  to?: string;
  href?: string;
  icon: string;
  title: string;
  subtitle?: string;
  color?: string;
  badge?: string | number;
  compact?: boolean;
}>();
</script>

<style scoped>
:root {
  --tile-fallback: #7a6;
}

.tile {
  --tc: var(--tile-color, var(--tile-fallback));
  display: flex;
  flex-direction: column;
  gap: 10px;
  align-items: center;
  justify-content: center;
  width: 70%; /* Further shrink by ~10% as requested */
  margin-inline: auto; /* center within grid cell */
  aspect-ratio: 1 / 1; /* مربعة */
  padding: 16px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.55);
  -webkit-backdrop-filter: blur(10px) saturate(1.1);
  backdrop-filter: blur(10px) saturate(1.1);
  border: 1px solid rgba(0, 0, 0, 0.06);
  position: relative;
  transition:
    transform 0.18s ease,
    box-shadow 0.18s ease;
  text-decoration: none;
  color: inherit;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.06);
  overflow: hidden;
}
.tile:hover {
  transform: translateY(-3px);
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.1);
}
.tile:active {
  transform: translateY(-1px) scale(0.995);
}
.tile:focus-visible {
  outline: 2px solid rgba(138, 21, 56, 0.25);
  outline-offset: 2px;
}

.tile-icon {
  width: 76px;
  height: 76px;
  display: grid;
  place-items: center;
  border-radius: 20px;
  background: rgba(0, 0, 0, 0.04);
  color: var(--tc);
  border: 1px solid rgba(0, 0, 0, 0.06);
  font-size: 36px;
}

/* نمط مضغوط */
.tile--compact {
  padding: 10px;
  border-radius: 14px;
  gap: 8px;
}
.tile--compact .tile-icon {
  width: 56px;
  height: 56px;
  font-size: 28px;
  border-radius: 16px;
}
.tile--compact .tile-title {
  font-size: 0.95rem;
}
.tile--compact .tile-subtitle {
  font-size: 0.8rem;
}

.tile-text {
  text-align: center;
  max-width: 92%;
}
.tile-title {
  font-weight: 800;
  line-height: 1.15;
  letter-spacing: 0.1px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.tile-subtitle {
  font-size: 0.86rem;
  color: #667085;
  line-height: 1.2;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* شارة KPI بلون البلاطة */
.tile-badge {
  position: absolute;
  inset-inline-end: 10px;
  top: 10px;
  background: var(--tc);
  color: #fff;
  border-radius: 999px;
  padding: 2px 8px;
  font-size: 0.75rem;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.12);
}

/* تحسينات استجابة */
@media (max-width: 576px) {
  .tile {
    width: 74%;
    padding: 14px;
  }
  .tile-icon {
    width: 68px;
    height: 68px;
    font-size: 32px;
    border-radius: 18px;
  }
}
@media (min-width: 1400px) {
  .tile {
    width: 63%;
  }
}
</style>
