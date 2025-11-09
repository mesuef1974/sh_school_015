import { backendUrl } from "../shared/config";

export type Tile = {
  id: string;
  title: string;
  subtitle?: string;
  to?: string;
  href?: string;
  icon: string;
  color?: string;
  roles?: string[];
  permissions?: string[];
  kpiKey?: "absentToday" | "presentPct" | "pendingApprovals";
};

export const tiles: Tile[] = [
  // Teacher tiles
  {
    id: "teacher_timetable",
    title: "جدولي",
    subtitle: "جدولي الدراسي",
    to: "/timetable/teacher",
    icon: "solar:calendar-bold-duotone",
    color: "#1565c0",
    roles: ["teacher"],
  },
  {
    id: "attendance_register",
    title: "تسجيل الغياب",
    subtitle: "تسجيل حضور وغياب اليوم",
    to: "/attendance/teacher",
    icon: "solar:clipboard-check-bold-duotone",
    color: "#8a1538",
    roles: ["teacher"],
  },
  {
    id: "attendance_history",
    title: "سجل الغياب",
    subtitle: "عرض سجلات الغياب",
    to: "/attendance/teacher/history",
    icon: "solar:history-bold-duotone",
    color: "#8a1538",
    roles: ["teacher"],
  },
  {
    id: "attendance_procedures",
    title: "إجراءات الغياب",
    subtitle: "تنبيهات ومتابعة الحالات",
    to: "/attendance/procedures",
    icon: "solar:document-text-bold-duotone",
    color: "#6a1b9a",
    roles: ["teacher"],
  },
  {
    id: "teacher_stats",
    title: "الإحصائيات",
    subtitle: "نسب وتحليلات تفصيلية",
    to: "/stats",
    icon: "solar:chart-2-bold-duotone",
    color: "#1976d2",
    roles: ["teacher"],
  },
  // Discipline tiles (Teacher)
  {
    id: "discipline_incidents_my",
    title: "وقائع الانضباط",
    subtitle: "سجلاتي والإرسال",
    to: "/discipline/incidents/simple",
    icon: "solar:document-bold-duotone",
    color: "#2e86c1",
    roles: ["teacher"],
  },
  {
    id: "discipline_incident_new",
    title: "تسجيل واقعة",
    subtitle: "واقعة سلوكية",
    to: "/discipline/incidents/new",
    icon: "solar:add-square-bold-duotone",
    color: "#27ae60",
    roles: ["teacher"],
  },

  // Subject Coordinator tiles
  {
    id: "subject_dashboard",
    title: "لوحة المنسق",
    subtitle: "مؤشرات وأدوات المادة",
    to: "/subject/dashboard",
    icon: "solar:graph-new-bold-duotone",
    color: "#2e7d32",
    roles: ["subject_coordinator"],
  },

  // Principal tiles
  {
    id: "principal_dashboard",
    title: "لوحة المدير",
    subtitle: "مؤشرات الأداء الشاملة",
    to: "/principal/dashboard",
    icon: "solar:speedometer-bold-duotone",
    color: "#6a1b9a",
    roles: ["principal"],
  },

  // Academic Deputy tiles
  {
    id: "academic_dashboard",
    title: "الشؤون الأكاديمية",
    subtitle: "الجداول والاختبارات والمناهج",
    to: "/academic/dashboard",
    icon: "solar:calendar-bold-duotone",
    color: "#1e88e5",
    roles: ["academic_deputy"],
  },

  // Wing supervisor tiles (new)
  {
    id: "wing_dashboard",
    title: "لوحة الجناح",
    subtitle: "مؤشرات اليوم",
    to: "/wing/dashboard",
    icon: "solar:layers-minimalistic-bold-duotone",
    color: "#66aa66",
    roles: ["wing_supervisor"],
  },
  {
    id: "wing_monitor",
    title: "مراقبة حضور الجناح",
    subtitle: "عرض مباشر للحصص",
    to: "/attendance/wing/monitor",
    icon: "solar:radar-2-bold-duotone",
    color: "#0d47a1",
    roles: ["wing_supervisor"],
  },
  {
    id: "wing_absences_alerts",
    title: "الغيابات والتنبيهات",
    subtitle: "حساب O/X وإصدار التنبيه",
    to: "/wing/absences",
    icon: "solar:bell-bing-bold-duotone",
    color: "#8a1538",
    roles: ["wing_supervisor"],
  },
  {
    id: "wing_missing",
    title: "حصص بلا إدخال",
    subtitle: "معالجة فورية",
    to: "/wing/attendance/missing",
    icon: "solar:shield-warning-bold-duotone",
    color: "#f39c12",
    roles: ["wing_supervisor"],
  },
  {
    id: "wing_exits",
    title: "أذونات الخروج",
    subtitle: "بدء/إيقاف وتتبع",
    to: "/wing/exits",
    icon: "solar:exit-bold-duotone",
    color: "#8e44ad",
    roles: ["wing_supervisor"],
  },
  {
    id: "wing_incidents",
    title: "البلاغات",
    subtitle: "انضباط ومعالجة",
    to: "/wing/incidents",
    icon: "solar:shield-warning-bold-duotone",
    color: "#c0392b",
    roles: ["wing_supervisor"],
  },
  {
    id: "wing_approvals",
    title: "طلبات الاعتماد",
    subtitle: "مراجعة واعتماد",
    to: "/wing/approvals",
    icon: "solar:shield-check-bold-duotone",
    color: "#2e7d32",
    roles: ["wing_supervisor"],
  },
  {
    id: "wing_classes",
    title: "صفوف وطلبة",
    subtitle: "إدارة صفوف الجناح",
    to: "/wing/classes",
    icon: "solar:home-2-bold-duotone",
    color: "#34495e",
    roles: ["wing_supervisor"],
  },
  {
    id: "wing_reports",
    title: "تقارير",
    subtitle: "تقارير الجناح",
    to: "/wing/reports",
    icon: "solar:graph-new-bold-duotone",
    color: "#1abc9c",
    roles: ["wing_supervisor"],
  },
  {
      id: "wing_timetable_daily",
      title: "جدول اليوم",
      subtitle: "عرض مجمّع يومي",
      to: "/wing/timetable/daily",
      icon: "solar:clock-circle-bold-duotone",
      color: "#5dade2",
      roles: ["wing_supervisor"],
    },
  {
    id: "wing_timetable_weekly",
    title: "الجدول الأسبوعي",
    subtitle: "عرض أسبوعي للفصول",
    to: "/wing/timetable/weekly",
    icon: "solar:calendar-bold-duotone",
    color: "#1e88e5",
    roles: ["wing_supervisor"],
  },
  {
    id: "wing_notifications",
    title: "التنبيهات",
    subtitle: "مركز الإشعارات",
    to: "/wing/notifications",
    icon: "solar:bell-bing-bold-duotone",
    color: "#d35400",
    roles: ["wing_supervisor"],
  },
  {
    id: "wing_settings",
    title: "إعدادات الجناح",
    subtitle: "ضبط الإعدادات",
    to: "/wing/settings",
    icon: "solar:settings-bold-duotone",
    color: "#7f8c8d",
    roles: ["wing_supervisor"],
  },
  // Wing diagnostics (visible to Wing Supervisor)
  {
    id: "debug_subject_icons",
    title: "تشخيص الأيقونات",
    subtitle: "المواد بلا أيقونات",
    to: "/debug/subject-icons",
    icon: "solar:bookmark-square-bold-duotone",
    color: "#9b59b6",
    roles: ["wing_supervisor"],
  },

  // Admin tiles
  {
    id: "admin",
    title: "Django Admin",
    href: backendUrl("/admin/"),
    icon: "solar:settings-bold-duotone",
    color: "#446688",
    roles: ["admin"],
  },
  {
    id: "rq",
    title: "مهام الخلفية (RQ)",
    href: backendUrl("/django-rq/"),
    icon: "solar:clipboard-list-bold-duotone",
    color: "#888855",
    roles: ["admin"],
  },
];