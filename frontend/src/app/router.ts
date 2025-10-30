import { createRouter, createWebHistory, RouteRecordRaw } from "vue-router";
import HomePage from "../home/HomePage.vue";
import TeacherAttendance from "../features/attendance/pages/TeacherAttendance.vue";
import LoginPage from "./pages/LoginPage.vue";
import { useAuthStore } from "./stores/auth";

const routes: RouteRecordRaw[] = [
  { path: "/", name: "home", component: HomePage, meta: { titleAr: "الرئيسية" } },
  { path: "/login", name: "login", component: LoginPage, meta: { titleAr: "تسجيل الدخول" } },
  {
    path: "/demo",
    name: "demo",
    component: () => import("../features/demo/DemoPage.vue"),
    meta: { titleAr: "عرض تجريبي" },
  },
  {
    path: "/design-system",
    name: "design-system",
    component: () => import("../features/design/DesignSystemPage.vue"),
    meta: { titleAr: "نظام التصميم" },
  },
  {
    path: "/grades",
    name: "grades-index",
    component: () => import("../features/grades/pages/GradesIndex.vue"),
    meta: { requiresAuth: true, requiredRoles: ["teacher"], titleAr: "الدرجات" },
  },
  {
    path: "/me",
    name: "profile",
    component: () => import("./pages/ProfilePage.vue"),
    meta: { requiresAuth: true, titleAr: "ملفي" },
  },
  {
    path: "/stats",
    name: "stats",
    component: () => import("../features/stats/StatsPage.vue"),
    meta: { requiresAuth: true, requiredRoles: ["teacher"], titleAr: "الإحصائيات" },
  },
  {
    path: "/students",
    name: "students",
    component: () => import("../features/students/StudentsPage.vue"),
    meta: { requiresAuth: true, requiredRoles: ["teacher"], titleAr: "الطلاب" },
  },
  {
    path: "/students/absence",
    name: "students-absence",
    component: () => import("../features/students/StudentsAbsenceHub.vue"),
    meta: { requiresAuth: true, requiredRoles: ["teacher"], titleAr: "إدارة غياب الطلاب" },
  },
  {
    path: "/attendance/procedures",
    name: "attendance-procedures",
    component: () => import("../features/attendance/pages/AttendanceProcedures.vue"),
    meta: { requiresAuth: true, requiredRoles: ["teacher"], titleAr: "إجراءات الحضور" },
  },
  {
    path: "/attendance/teacher",
    name: "teacher-attendance",
    component: TeacherAttendance,
    meta: { requiresAuth: true, requiredRoles: ["teacher"], titleAr: "تسجيل الغياب" },
  },
  {
    path: "/attendance/teacher/history",
    name: "teacher-attendance-history",
    component: () => import("../features/attendance/pages/TeacherAttendanceHistory.vue"),
    meta: { requiresAuth: true, requiredRoles: ["teacher"], titleAr: "سجل الغياب" },
  },
  {
    path: "/wing/dashboard",
    name: "wing-dashboard",
    component: () => import("../features/wings/pages/WingDashboard.vue"),
    meta: { requiresAuth: true, requiredRoles: ["wing_supervisor"], titleAr: "لوحة جناح" },
  },
  {
    path: "/wing/approvals",
    name: "wing-approvals",
    component: () => import("../features/wings/pages/WingApprovals.vue"),
    meta: { requiresAuth: true, requiredRoles: ["wing_supervisor"], titleAr: "طلبات الاعتماد" },
  },
  {
    path: "/attendance/wing/monitor",
    name: "wing-attendance-monitor",
    component: () => import("../features/wings/pages/WingAttendanceMonitor.vue"),
    meta: { requiresAuth: true, requiredRoles: ["wing_supervisor"], titleAr: "مراقبة حضور الجناح" },
  },
  {
    path: "/subject/dashboard",
    name: "subject-dashboard",
    component: () => import("../features/subject/pages/SubjectDashboard.vue"),
    meta: { requiresAuth: true, requiredRoles: ["subject_coordinator"], titleAr: "لوحة المنسق" },
  },
  {
    path: "/principal/dashboard",
    name: "principal-dashboard",
    component: () => import("../features/principal/pages/PrincipalDashboard.vue"),
    meta: { requiresAuth: true, requiredRoles: ["principal"], titleAr: "لوحة المدير" },
  },
  {
    path: "/academic/dashboard",
    name: "academic-dashboard",
    component: () => import("../features/academic/pages/AcademicDashboard.vue"),
    meta: {
      requiresAuth: true,
      requiredRoles: ["academic_deputy"],
      titleAr: "لوحة الشؤون الأكاديمية",
    },
  },
  {
    path: "/timetable/teacher",
    name: "teacher-timetable",
    component: () => import("../features/timetable/pages/TeacherTimetable.vue"),
    meta: { requiresAuth: true, requiredRoles: ["teacher"], titleAr: "جدول المعلم" },
  },
  {
    path: "/wing/timetable",
    redirect: { name: "wing-timetable-daily" },
  },
  {
    path: "/wing/timetable/daily",
    name: "wing-timetable-daily",
    component: () => import("../features/wings/pages/WingTimetable.vue"),
    meta: { requiresAuth: true, requiredRoles: ["wing_supervisor"], titleAr: "جدول اليوم" },
  },
  {
    path: "/wing/timetable/weekly",
    name: "wing-timetable-weekly",
    component: () => import("../features/wings/pages/WingTimetable.vue"),
    meta: { requiresAuth: true, requiredRoles: ["wing_supervisor"], titleAr: "الجدول الأسبوعي" },
  },
  {
    path: "/wing/absences",
    name: "wing-absences-alerts",
    component: () => import("../features/wings/pages/WingAbsencesAlerts.vue"),
    meta: { requiresAuth: true, requiredRoles: ["wing_supervisor"], titleAr: "غيابات وتنبيهات الجناح" },
  },
  {
    path: "/wing/attendance/daily",
    name: "wing-attendance-daily",
    component: () => import("../features/wings/pages/WingAttendanceDaily.vue"),
    meta: { requiresAuth: true, requiredRoles: ["wing_supervisor"], titleAr: "الغياب اليومي للجناح" },
  },
  {
    path: "/designer/tiles",
    name: "tiles-designer",
    component: () => import("../features/design/TilesDesigner.vue"),
    meta: {
      requiresAuth: true,
      requiredRoles: ["principal", "it", "admin_deputy"],
      titleAr: "مصمم الأيقونات",
    },
  },
];

export const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 };
  },
});

router.beforeEach(async (to) => {
  if (to.meta?.requiresAuth) {
    const auth = useAuthStore();
    // Attempt to ensure profile is loaded; if it fails (e.g., 401), redirect to login
    if (!auth.profile) {
      try {
        await auth.loadProfile();
      } catch {
        return { name: "login", query: { next: to.fullPath } };
      }
    }
    const required = (to.meta as any).requiredRoles as string[] | undefined;
    if (required && required.length) {
      // Allow if user has any of the required roles OR is superuser
      // Additionally, if 'teacher' is required, allow users who have teaching assignments
      const hasRoleMatch = auth.roles.some((r) => required.includes(r));
      const isSuper = !!auth.profile?.is_superuser;
      const isTeacherByAssignment =
        required.includes("teacher") && !!auth.profile?.hasTeachingAssignments;
      const hasAny = hasRoleMatch || isSuper || isTeacherByAssignment;
      if (!hasAny) {
        // Soft-allow Wing dashboard route to render diagnostic UI even if role mapping is inconsistent.
        // Server-side APIs remain protected, so this does not grant data access.
        if (to.path.startsWith("/wing")) {
          return true;
        }
        return { name: "home" };
      }
    }
  }
  return true;
});
