import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router';
import HomePage from '../home/HomePage.vue';
import TeacherAttendance from '../features/attendance/pages/TeacherAttendance.vue';
import LoginPage from './pages/LoginPage.vue';
import { useAuthStore } from './stores/auth';

const routes: RouteRecordRaw[] = [
  { path: '/', name: 'home', component: HomePage },
  { path: '/login', name: 'login', component: LoginPage },
  { path: '/me', name: 'profile', component: () => import('./pages/ProfilePage.vue'), meta: { requiresAuth: true } },
  { path: '/attendance/teacher', name: 'teacher-attendance', component: TeacherAttendance, meta: { requiresAuth: true, requiredRoles: ['teacher'] } },
  { path: '/attendance/teacher/history', name: 'teacher-attendance-history', component: () => import('../features/attendance/pages/TeacherAttendanceHistory.vue'), meta: { requiresAuth: true, requiredRoles: ['teacher'] } },
  { path: '/wing/dashboard', name: 'wing-dashboard', component: () => import('../features/wings/pages/WingDashboard.vue'), meta: { requiresAuth: true, requiredRoles: ['wing_supervisor'] } },
  { path: '/attendance/wing/monitor', name: 'wing-attendance-monitor', component: () => import('../features/wings/pages/WingAttendanceMonitor.vue'), meta: { requiresAuth: true, requiredRoles: ['wing_supervisor'] } },
  { path: '/subject/dashboard', name: 'subject-dashboard', component: () => import('../features/subject/pages/SubjectDashboard.vue'), meta: { requiresAuth: true, requiredRoles: ['subject_coordinator'] } },
  { path: '/principal/dashboard', name: 'principal-dashboard', component: () => import('../features/principal/pages/PrincipalDashboard.vue'), meta: { requiresAuth: true, requiredRoles: ['principal'] } },
  { path: '/academic/dashboard', name: 'academic-dashboard', component: () => import('../features/academic/pages/AcademicDashboard.vue'), meta: { requiresAuth: true, requiredRoles: ['academic_deputy'] } },
  { path: '/timetable/teacher', name: 'teacher-timetable', component: () => import('../features/timetable/pages/TeacherTimetable.vue'), meta: { requiresAuth: true, requiredRoles: ['teacher'] } }
];

export const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 };
  }
});

router.beforeEach(async (to) => {
  if (to.meta?.requiresAuth) {
    const auth = useAuthStore();
    // Attempt to ensure profile is loaded; if it fails (e.g., 401), redirect to login
    if (!auth.profile) {
      try {
        await auth.loadProfile();
      } catch {
        return { name: 'login', query: { next: to.fullPath } };
      }
    }
    const required = (to.meta as any).requiredRoles as string[] | undefined;
    if (required && required.length) {
      // Allow if user has any of the required roles OR is superuser
      // Additionally, if 'teacher' is required, allow users who have teaching assignments
      const hasRoleMatch = auth.roles.some(r => required.includes(r));
      const isSuper = !!auth.profile?.is_superuser;
      const isTeacherByAssignment = required.includes('teacher') && !!auth.profile?.hasTeachingAssignments;
      const hasAny = hasRoleMatch || isSuper || isTeacherByAssignment;
      if (!hasAny) {
        return { name: 'home' };
      }
    }
  }
  return true;
});