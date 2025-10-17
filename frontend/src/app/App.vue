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
        <RouterLink to="/">الرئيسية</RouterLink>
        <RouterLink v-if="isAssignedTeacher || isSuper" to="/attendance/teacher">تسجيل الغياب</RouterLink>
        <RouterLink v-if="isAssignedTeacher || isSuper" to="/timetable/teacher">جدولي</RouterLink>
        <RouterLink v-if="isAssignedTeacher || isSuper" to="/attendance/teacher/history">سجل الغياب</RouterLink>
        <RouterLink v-if="hasRole('wing_supervisor') || isSuper" to="/wing/dashboard">مشرف الجناح</RouterLink>
        <RouterLink v-if="hasRole('subject_coordinator') || isSuper" to="/subject/dashboard">منسق المادة</RouterLink>
        <RouterLink v-if="hasRole('principal') || isSuper" to="/principal/dashboard">مدير المدرسة</RouterLink>
        <RouterLink v-if="hasRole('academic_deputy') || isSuper" to="/academic/dashboard">المدير الأكاديمي</RouterLink>
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
import { useRouter } from 'vue-router';

const router = useRouter();
const logoSrc = '/assets/img/logo.png';
const schoolNameSrc = '/assets/img/school_name.png';

const auth = useAuthStore();
const hasRole = (r: string) => auth.roles.includes(r);
const isSuper = computed(() => !!auth.profile?.is_superuser);
const isAssignedTeacher = computed(() => !!auth.profile?.hasTeachingAssignments);

async function onLogout() {
  await logout();
  auth.clear();
  router.replace({ name: 'login' });
}
</script>

<style>
.container { max-width: 1200px; }
.flex-fill { flex: 1 1 auto; }
</style>