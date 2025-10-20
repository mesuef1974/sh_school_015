import { backendUrl } from '../shared/config';

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
  kpiKey?: 'absentToday' | 'presentPct' | 'pendingApprovals';
};

export const tiles: Tile[] = [
  { id: 'students', title: 'الطلبة', subtitle: 'إدارة شؤون الطلبة', to: '/students', icon: 'solar:users-group-rounded-bold-duotone', color: '#2e7d32', roles: ['teacher'] },
  { id: 'teacher_timetable', title: 'جدولي', subtitle: 'جدولي الدراسي', to: '/timetable/teacher', icon: 'solar:calendar-bold-duotone', color: '#1565c0', roles: ['teacher'] },
  { id: 'wing_dashboard', title: 'لوحة الجناح', to: '/wing/dashboard', icon: 'solar:layers-minimalistic-bold-duotone', color: '#66aa66', roles: ['wing_supervisor'] },
  { id: 'admin', title: 'Django Admin', href: backendUrl('/admin/'), icon: 'solar:settings-bold-duotone', color: '#446688', roles: ['admin'] },
  { id: 'rq', title: 'مهام الخلفية (RQ)', href: backendUrl('/django-rq/'), icon: 'solar:clipboard-list-bold-duotone', color: '#888855', roles: ['admin'] },
];