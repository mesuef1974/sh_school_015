<template>
  <div class="page-container">
    <header class="navbar-maronia">
      <nav class="container d-flex align-items-center gap-3 py-2">
        <div class="brand-images d-flex align-items-center">
          <img :src="logoSrc" alt="شعار" />
          <span class="brand-divider"></span>
          <img :src="schoolNameSrc" alt="مدرسة الشحانية" />
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
    <main class="page-main container py-3">
      <RouterView />
    </main>
    <footer class="page-footer py-3 bg-maroon">
      <div class="container d-flex justify-content-between small">
        <span class="text-white text-center w-100">©2025 - جميع الحقوق محفوظة - مدرسة الشحانية الاعدادية الثانوية بنين - تطوير( المعلم/ سفيان مسيف s.mesyef0904@education.qa )</span>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useAuthStore } from './stores/auth';
import { logout } from '../shared/api/client';
import { useRouter, useRoute } from 'vue-router';

const router = useRouter();
const route = useRoute();
const logoSrc = '/assets/img/logo.png';
const schoolNameSrc = '/assets/img/school_name.png';

const auth = useAuthStore();
const hasRole = (r: string) => auth.roles.includes(r);
const isSuper = computed(() => !!auth.profile?.is_superuser);
const isTeacher = computed(() => auth.roles.includes('teacher'));
const isHome = computed(() => route.name === 'home');

async function onLogout() {
  await logout();
  auth.clear();
  router.replace({ name: 'login' });
}
</script>

<style>
.container { max-width: 1200px; }
.flex-fill { flex: 1 1 auto; }

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