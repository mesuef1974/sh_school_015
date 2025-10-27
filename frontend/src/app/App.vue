<template>
  <div class="page-container">
    <header class="navbar-maronia">
      <nav class="container d-flex align-items-center gap-3 py-2">
        <div class="brand-images d-flex align-items-center">
          <img src="https://127.0.0.1:8443/static/img/logo02.png?v=20251027-01" alt="شعار" style="height:44px; width:auto; display:block;" />
        </div>
        <span class="flex-fill"></span>
        <RouterLink v-if="!isHome" :to="{ name: 'home' }" class="btn btn-glass-home" aria-label="العودة إلى الرئيسية">
          <Icon icon="fa6-solid:house" />
        </RouterLink>
        <div class="dropdown" v-if="auth.profile">
          <button class="btn btn-sm btn-light dropdown-toggle" data-bs-toggle="dropdown" type="button">
            <i class="bi bi-person-circle"></i>
            {{ auth.profile?.full_name || auth.profile?.username }}
          </button>
          <ul class="dropdown-menu dropdown-menu-end">
            <li v-if="isAssignedTeacher || isSuper"><h6 class="dropdown-header">صفحات المعلم</h6></li>
            <li v-if="isAssignedTeacher || isSuper"><RouterLink class="dropdown-item" to="/">الرئيسية</RouterLink></li>
            <li v-if="isAssignedTeacher || isSuper"><RouterLink class="dropdown-item" to="/attendance/teacher">تسجيل الغياب</RouterLink></li>
            <li v-if="isAssignedTeacher || isSuper"><RouterLink class="dropdown-item" to="/timetable/teacher">جدولي</RouterLink></li>
            <li v-if="isAssignedTeacher || isSuper"><RouterLink class="dropdown-item" to="/attendance/teacher/history">سجل الغياب</RouterLink></li>
            <li><hr class="dropdown-divider" /></li>
            <li><RouterLink class="dropdown-item" to="/me">ملفي</RouterLink></li>
            <li><hr class="dropdown-divider" /></li>
            <li><a class="dropdown-item text-danger" href="#" @click.prevent="onLogout">تسجيل الخروج</a></li>
          </ul>
        </div>
        <RouterLink v-else to="/login">دخول</RouterLink>
      </nav>
    </header>
    <main class="page-main container" :class="{ 'wide-wing': isWing, 'is-login': isLogin, 'py-3': !isLogin }">
      <div class="d-flex justify-content-between align-items-center mb-2" dir="rtl" v-if="!isHome && !isLogin">
        <div class="flex-fill"></div>
        <BreadcrumbRtl />
      </div>
      <RouterView />
    </main>
    <footer class="page-footer py-3 bg-maroon">
      <div class="container d-flex justify-content-between small">
        <span class="text-gold-metal text-center w-100">©2025 - جميع الحقوق محفوظة - مدرسة الشحانية الاعدادية الثانوية بنين - تطوير( المعلم/ سفيان مسيف s.mesyef0904@education.qa )</span>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useAuthStore } from './stores/auth';
import { logout } from '../shared/api/client';
import { useRouter, useRoute } from 'vue-router';
import BreadcrumbRtl from '../components/BreadcrumbRtl.vue';

const router = useRouter();
const route = useRoute();
// Append a version query to ensure updated image is not served from browser cache
const SCHOOL_ASSETS_VERSION = '20251027-02';
const logoSrc = `/assets/img/logo.png?v=${SCHOOL_ASSETS_VERSION}`;
const schoolNameSrc = `/assets/img/school_name.png?v=${SCHOOL_ASSETS_VERSION}`;

const auth = useAuthStore();
const hasRole = (r: string) => auth.roles.includes(r);
const isSuper = computed(() => !!auth.profile?.is_superuser);
const isTeacher = computed(() => auth.roles.includes('teacher'));
const isHome = computed(() => route.name === 'home');
const isLogin = computed(() => route.name === 'login');
const hideSchoolName = computed(() => route.path?.startsWith('/supervisor'));
const isWing = computed(() => route.path?.startsWith('/wing'));


async function onLogout() {
  await logout();
  auth.clear();
  router.replace({ name: 'login' });
}
</script>

<style>
:root {
  /* Fixed heights to compute viewport without scroll on special pages like login */
  --app-header-h: 64px;
  --app-footer-h: 56px;
}

/* Use up to 98% of viewport width across the app */
.container { max-width: var(--page-w); margin-inline: auto; }
/* Wing pages also respect the 98% rule */
.page-main.wide-wing.container { max-width: var(--page-w); }
.flex-fill { flex: 1 1 auto; }

/* Make the app fill ~98% of the viewport height */
.page-container { min-height: 98vh; display: flex; flex-direction: column; }
.page-main { flex: 1 1 auto; }
/* Login-specific layout tweaks: keep footer fully visible and center content */
.page-main.is-login { height: calc(100vh - var(--app-header-h) - var(--app-footer-h)); height: calc(100dvh - var(--app-header-h) - var(--app-footer-h)); display: flex; align-items: center; justify-content: center; overflow: hidden; }

/* Ensure header/footer occupy stable space to allow calc(100vh - ...) layouts */
.navbar-maronia { height: var(--app-header-h); display: flex; align-items: center; }
.navbar-maronia > nav { height: 100%; padding-top: 0; padding-bottom: 0; }
.page-footer { height: var(--app-footer-h); display: flex; align-items: center; padding-top: 0; padding-bottom: 0; }

/* زر الرجوع للرئيسية بأسلوب زجاجي دائري */
.btn-glass-home {
  display: inline-grid;
  place-items: center;
  width: 36px; height: 36px;
  border-radius: 50%;
  background: rgba(255,255,255,0.65);
  -webkit-backdrop-filter: blur(8px);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(0,0,0,0.06);
  box-shadow: 0 6px 18px rgba(0,0,0,.06);
  color: #8a1538; /* maroon */
  text-decoration: none;
}
.btn-glass-home:hover { transform: translateY(-1px); box-shadow: 0 10px 26px rgba(0,0,0,.08); }
.btn-glass-home:focus { outline: 2px solid rgba(138,21,56,0.3); outline-offset: 2px; }
.btn-glass-home :deep(svg) { font-size: 18px; }
</style>
