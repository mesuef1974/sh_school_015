import axios from 'axios';

export const TOKEN_STORAGE_KEY = 'sh_school_token';

export const api = axios.create({
  baseURL: '/api',
  withCredentials: true,
  timeout: 8000 // fail fast in dev if backend is down
});

// Attach Authorization header if token exists
api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_STORAGE_KEY);
  if (token) {
    config.headers = config.headers || {};
    (config.headers as any)['Authorization'] = `Bearer ${token}`;
  }
  return config;
});

// Simple 401 handler: redirect to /login
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err?.response?.status === 401 && location.pathname !== '/login') {
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

export async function getAttendanceStudents(params: { class_id: number; date?: string }) {
  const res = await api.get('/v1/attendance/students/', { params });
  return res.data as { students: any[]; date: string; class_id: number };
}

export async function getAttendanceRecords(params: { class_id: number; date?: string }) {
  const res = await api.get('/v1/attendance/records/', { params });
  return res.data as { records: { student_id: number; status: string; note?: string | null }[]; date: string; class_id: number };
}

export async function getAttendanceSummary(params: { scope?: 'teacher'|'wing'|'school'; date?: string; class_id?: number; wing_id?: number } = {}) {
  const res = await api.get('/v1/attendance/summary/', { params });
  return res.data as { date: string; scope: string; kpis: { present_pct: number; absent: number; late: number; excused: number }; top_classes: { class_id: number; present_pct: number }[]; worst_classes: { class_id: number; present_pct: number }[] };
}

export async function getTeacherClasses() {
  const res = await api.get('/v1/attendance/teacher/classes/');
  return res.data as { classes: { id: number; name?: string }[] };
}

export async function getTeacherTimetableToday(params: { date?: string } = {}) {
  const res = await api.get('/v1/attendance/timetable/teacher/today/', { params });
  return res.data as { date: string; periods: { period_number: number; classroom_id: number; classroom_name?: string; subject_id: number; subject_name?: string; start_time?: string; end_time?: string }[] };
}

export async function getTeacherTimetableWeekly() {
  const res = await api.get('/v1/attendance/timetable/teacher/weekly/');
  return res.data as { days: Record<string, { period_number: number; classroom_id: number; classroom_name?: string; subject_id: number; subject_name?: string; start_time?: string; end_time?: string }[]>; meta: any };
}

export async function postAttendanceBulkSave(payload: { class_id: number; date: string; records: { student_id: number; status: string; note?: string | null }[] }) {
  const res = await api.post('/v1/attendance/bulk_save/', payload);
  return res.data as { saved: number };
}

export async function login(username: string, password: string) {
  const res = await axios.post('/api/token/', { username, password });
  const data = res.data as { access: string; refresh: string };
  localStorage.setItem(TOKEN_STORAGE_KEY, data.access);
  localStorage.setItem('sh_school_refresh', data.refresh);
  return data;
}

export async function logout() {
  try {
    const refresh = localStorage.getItem('sh_school_refresh');
    if (refresh) {
      await api.post('/logout/', { refresh });
    }
  } catch {
    // ignore errors on logout to be resilient
  } finally {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    localStorage.removeItem('sh_school_refresh');
  }
}

export async function changePassword(payload: { current_password: string; new_password1: string; new_password2: string }) {
  const res = await api.post('/change_password/', payload);
  return res.data as { detail: string };
}

export async function getMe() {
  const res = await api.get('/me/');
  return res.data as { id: number; username: string; full_name: string; is_superuser: boolean; is_staff: boolean; roles: string[]; permissions: string[]; hasTeachingAssignments: boolean; capabilities?: { can_manage_timetable?: boolean; can_view_general_timetable?: boolean; can_take_attendance?: boolean } };
}