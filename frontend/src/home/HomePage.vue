<template>
  <section class="d-grid gap-3">
    <header
      v-motion
      :initial="{ opacity: 0, y: -50 }"
      :enter="{ opacity: 1, y: 0, transition: { duration: 500 } }"
      class="auto-card p-3 d-flex align-items-center gap-3"
    >
      <img :src="logoSrc" alt="" style="height:54px; filter: brightness(0) saturate(100%) invert(15%) sepia(50%) saturate(2500%) hue-rotate(330deg) brightness(90%) contrast(90%);" />
      <div class="fw-bold" style="white-space: nowrap;">{{ salutation }}، {{ name }}</div>
      <span class="ms-auto"></span>
      <!-- مثال بسيط على استخدام Lottie عبر vue3-lottie: يظهر على الشاشات المتوسطة فما فوق -->
      <Vue3Lottie
        class="d-none d-md-block"
        path="https://cdn.lordicon.com/egiwmiit.json"
        :loop="true"
        :autoplay="true"
        :speed="1"
        style="height:54px"
        aria-label="Animated greeting"
      />
    </header>

    <div class="row g-3 tile-grid">
      <div
        v-for="(t, index) in visibleTiles"
        :key="t.id"
        class="col-6 col-md-4 col-xl-3"
        v-motion
        :initial="{ opacity: 0, scale: 0.8 }"
        :enter="{
          opacity: 1,
          scale: 1,
          transition: {
            delay: 100 + (index * 50),
            duration: 400
          }
        }"
      >
        <IconTile :to="t.to" :href="t.href" :icon="t.icon" :title="t.title" :subtitle="t.subtitle" :color="t.color" :badge="t.kpiKey ? (kpiMap as any)[t.kpiKey] : undefined" />
      </div>
    </div>
  </section>
</template>
<script setup lang="ts">
import { computed, ref, onMounted } from 'vue';
import { useAuthStore } from '../app/stores/auth';
import IconTile from '../widgets/IconTile.vue';
import DsButton from '../components/ui/DsButton.vue';
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

// Intro overlay state (show once per session; optionally never again)
const INTRO_KEY_FOREVER = 'homeIntroNeverShow';
const INTRO_KEY_SESSION = 'homeIntroSeen';
const prefersReduced = typeof window !== 'undefined' && window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;
const reducedMotion = ref<boolean>(prefersReduced ? prefersReduced.matches : false);
const showIntro = ref<boolean>(false);
// Motion override and animation state
const allowMotion = ref<boolean>(false);
const failed = ref<boolean>(false);
const primaryPath = 'https://assets10.lottiefiles.com/packages/lf20_1pxqjqps.json';
const backupPath = 'https://cdn.lordicon.com/egiwmiit.json';
const currentPath = ref<string>(primaryPath);
const shouldAnimate = computed(() => (!reducedMotion.value || allowMotion.value) && !failed.value);

onMounted(() => {
  try {
    if (prefersReduced) {
      const handler = (e: MediaQueryListEvent) => { reducedMotion.value = e.matches; };
      // @ts-ignore - addEventListener not in older TS dom lib types
      prefersReduced.addEventListener ? prefersReduced.addEventListener('change', handler) : prefersReduced.addListener(handler);
    }
  } catch {}
  try {
    const never = localStorage.getItem(INTRO_KEY_FOREVER) === '1';
    const seenSession = sessionStorage.getItem(INTRO_KEY_SESSION) === '1';
    showIntro.value = !never && !seenSession;
  } catch {
    showIntro.value = true;
  }
  try {
    allowMotion.value = localStorage.getItem('homeIntroAllowMotion') === '1';
  } catch {}
});

function dismissIntro() {
  showIntro.value = false;
  try { sessionStorage.setItem(INTRO_KEY_SESSION, '1'); } catch {}
}
function dismissIntroForever() {
  showIntro.value = false;
  try { localStorage.setItem(INTRO_KEY_FOREVER, '1'); sessionStorage.setItem(INTRO_KEY_SESSION, '1'); } catch {}
}

function enableMotionOverride() {
  allowMotion.value = true;
  failed.value = false;
  try { localStorage.setItem('homeIntroAllowMotion','1'); } catch {}
}
function retryAnimation() {
  failed.value = false;
  currentPath.value = currentPath.value === primaryPath ? backupPath : primaryPath;
}
</script>
<style scoped>
.tile-grid .col-6,.tile-grid .col-md-4,.tile-grid .col-xl-3 { position: relative; }
/* تعزيز الإحساس بالعوم عبر مسافة وظل خفيفين تأتي من مكون IconTile */

/* أنماط شاشة الترحيب */
.intro-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1050; /* فوق الهيدر والبلاطات */
  padding: 16px;
}
.intro-card {
  max-width: 720px;
  width: 100%;
  position: relative;
}
.intro-close {
  position: absolute;
  top: 8px;
  inset-inline-start: 8px; /* RTL-friendly */
}
.intro-media { display: flex; justify-content: center; }
</style>