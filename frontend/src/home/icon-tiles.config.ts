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
  { id: 'students', title: 'الطلبة', subtitle: 'إدارة شؤون الطلبة', to: '/students', icon: 'fa6-solid:users', color: '#2e7d32', roles: ['teacher'] },
  { id: 'teacher_timetable', title: 'جدولي', subtitle: 'جدولي الدراسي', to: '/timetable/teacher', icon: 'fa6-solid:calendar-week', color: '#1565c0', roles: ['teacher'] },
  { id: 'wing_dashboard', title: 'لوحة الجناح', to: '/wing/dashboard', icon: 'fa6-solid:layer-group', color: '#6a6', roles: ['wing_supervisor'] },
  { id: 'admin', title: 'Django Admin', href: backendUrl('/admin/'), icon: 'fa6-solid:gauge-high', color: '#468', roles: ['admin'] },
  { id: 'rq', title: 'مهام الخلفية (RQ)', href: backendUrl('/django-rq/'), icon: 'fa6-solid:list-check', color: '#885', roles: ['admin'] },
];