<template>
  <section class="d-grid gap-3">
    <header class="auto-card p-3 d-flex align-items-center gap-3">
      <img :src="logoSrc" alt="" style="height:54px" />
      <div>
        <div class="fw-bold">{{ salutation }}، {{ name }}</div>
      </div>
      <span class="ms-auto"></span>
    </header>

    <div class="row g-3 tile-grid">
      <div v-for="t in visibleTiles" :key="t.id" class="col-6 col-md-4 col-xl-3">
        <IconTile :to="t.to" :href="t.href" :icon="t.icon" :title="t.title" :subtitle="t.subtitle" :color="t.color" :badge="t.kpiKey ? (kpiMap as any)[t.kpiKey] : undefined" />
      </div>
    </div>
  </section>
</template>
<script setup lang="ts">
import { computed } from 'vue';
import { useAuthStore } from '../app/stores/auth';
import IconTile from '../widgets/IconTile.vue';
import { tiles } from './icon-tiles.config';

const auth = useAuthStore();
const name = computed(() => auth.profile?.full_name || auth.profile?.username || '');
const roles = computed(() => auth.profile?.roles || []);
const hasRole = (r: string) => roles.value.includes(r);
const isSuper = computed(() => !!auth.profile?.is_superuser);
const isTeacher = computed(() => hasRole('teacher'));
const logoSrc = '/assets/img/logo.png';

// Arabic salutation based on current hour
const hour = new Date().getHours();
const salutation = computed(() => hour < 12 ? 'صباح الخير' : hour < 17 ? 'نهارك سعيد' : 'مساء الخير');

// Visible tiles based on roles/permissions
const roleSet = computed(() => new Set(auth.profile?.roles || []));
const permSet = computed(() => new Set(auth.profile?.permissions || []));
const canSee = (t: any) => {
  const okRole = !t.roles?.length || t.roles.some((r: string) => roleSet.value.has(r));
  const okPerm = !t.permissions?.length || t.permissions.some((p: string) => permSet.value.has(p));
  return okRole && okPerm;
};
const visibleTiles = computed(() => tiles.filter(canSee));

// KPI badge placeholders from profile if available (extensible)
const kpiMap = computed(() => ({
  absentToday:  (auth as any).profile?.kpis?.absentToday ?? undefined,
  presentPct:   (auth as any).profile?.kpis?.presentPct ?? undefined,
  pendingApprovals: (auth as any).profile?.kpis?.pendingApprovals ?? undefined,
}));
</script>
<style scoped>
.tile-grid .col-6,.tile-grid .col-md-4,.tile-grid .col-xl-3 { position: relative; }
/* تعزيز الإحساس بالعوم عبر مسافة وظل خفيفين تأتي من مكون IconTile */
</style>