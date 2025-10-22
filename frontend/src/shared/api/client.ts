import axios from 'axios';
import { enqueueAttendance, flushAttendanceQueue, initOfflineQueue, type AttendanceBulkItem } from '../offline/queue';

// Backward-compat key (kept for a transitional period). Avoid using localStorage for access tokens.

// In-memory access token holder (preferred over localStorage)
let accessToken: string | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
}

export const api = axios.create({
  baseURL: '/api',
  withCredentials: true,
  timeout: 8000 // fail fast in dev if backend is down
});

// Initialize offline queue to auto-flush queued attendance on connectivity regain
initOfflineQueue(async (p: AttendanceBulkItem) => {
  await api.post('/v1/attendance/bulk_save/', p);
});

// Attach Authorization header if token exists (in-memory only)
api.interceptors.request.use((config) => {
  const token = accessToken;
  if (token) {
    config.headers = config.headers || {};
    (config.headers as any)['Authorization'] = `Bearer ${token}`;
  }
  return config;
});

// Automatic refresh on 401 (once), then redirect to /login on failure
let refreshing: Promise<string | null> | null = null;
api.interceptors.response.use(
  (res) => res,
  async (err) => {
    const status = err?.response?.status;
    const original = err?.config || {};
    if (status === 401 && !original._retry) {
      original._retry = true;
      try {
        refreshing = refreshing ?? refreshAccessToken();
        const newToken = await refreshing.finally(() => (refreshing = null));
        if (newToken) {
          setAccessToken(newToken);
          original.headers = original.headers || {};
          original.headers['Authorization'] = `Bearer ${newToken}`;
          return api(original);
        }
      } catch {}
    }
    if (status === 401 && location.pathname !== '/login') {
      // Could not refresh → redirect to login
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

async function refreshAccessToken(): Promise<string | null> {
  try {
    // Prefer HttpOnly cookie on server. If not available yet, fallback to stored refresh (temporary)
    const storedRefresh = localStorage.getItem('sh_school_refresh');
    const body = storedRefresh ? { refresh: storedRefresh } : {};
    const res = await axios.post('/api/token/refresh/', body, { withCredentials: true });
    const data = res.data as { access?: string };
    if (data?.access) { return data.access; }
    return null;
  } catch {
    return null;
  }
}

export async function getAttendanceStudents(params: { class_id: number; date?: string }) {
  const res = await api.get('/v1/attendance/students/', { params });
  return res.data as { students: any[]; date: string; class_id: number };
}

export async function getAttendanceRecords(params: { class_id: number; date?: string; period_number?: number | null }) {
  const res = await api.get('/v1/attendance/records/', { params });
  return res.data as { records: { student_id: number; status: string; note?: string | null; exit_reasons?: string | string[] | null }[]; date: string; class_id: number; period_number?: number | null };
}

export async function getAttendanceHistory(params: { class_id: number; from?: string; to?: string; page?: number; page_size?: number }) {
  // Use strict history endpoint to ensure results are only from the selected class
  const res = await api.get('/v1/attendance/history-strict/', { params });
  return res.data as { count: number; page: number; page_size: number; from: string; to: string; class_id: number; results: { date: string; student_id: number; student_name?: string | null; status: string; note?: string | null }[] };
}

export async function getAttendanceSummary(params: { scope?: 'teacher'|'wing'|'school'; date?: string; class_id?: number; wing_id?: number } = {}) {
  const res = await api.get('/v1/attendance/summary/', { params });
  return res.data as { date: string; scope: string; kpis: { present_pct: number; absent: number; late: number; excused: number }; top_classes: { class_id: number; class_name?: string | null; present_pct: number }[]; worst_classes: { class_id: number; class_name?: string | null; present_pct: number }[] };
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

export async function postAttendanceBulkSave(payload: { class_id: number; date: string; period_number?: number; records: { student_id: number; status: string; note?: string | null; exit_reasons?: string | string[] }[] }) {
  try {
    const res = await api.post('/v1/attendance/bulk_save/', payload);
    return res.data as { saved: number };
  } catch (e: any) {
    // Network-level failure → queue for later sync (offline-first behavior)
    const hasResponse = !!e?.response;
    if (!hasResponse) {
      try { enqueueAttendance(payload as AttendanceBulkItem); } catch {}
      return { saved: payload.records.length, queued: true } as any;
    }
    throw e;
  }
}

export async function flushAttendanceQueueNow() {
  return flushAttendanceQueue(async (p) => (await api.post('/v1/attendance/bulk_save/', p)).data);
}

export async function login(username: string, password: string) {
  const res = await axios.post('/api/token/', { username, password }, { withCredentials: true });
  const data = res.data as { access: string; refresh?: string };
  // Store access in-memory (preferred)
  setAccessToken(data.access);
  // Transitional: keep refresh if backend still returns it and cookie not yet configured
  if (data.refresh) {
    try { localStorage.setItem('sh_school_refresh', data.refresh); } catch {}
  }
  return data;
}

export async function logout() {
  try {
    const refresh = localStorage.getItem('sh_school_refresh');
    const body = refresh ? { refresh } : {};
    await api.post('/logout/', body);
  } catch {
    // ignore errors on logout to be resilient
  } finally {
    setAccessToken(null);
    try { localStorage.removeItem('sh_school_refresh'); } catch {}
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

// --- Exit Events API ---
export async function getOpenExitEvents(params: { class_id?: number; date?: string; student_id?: number }) {
  const res = await api.get('/v1/attendance/exit-events/open/', { params });
  return res.data as { id: number; student_id: number; started_at: string; reason: string }[];
}

export async function postExitEvent(payload: { student_id: number; class_id?: number; date: string; period_number?: number | null; reason: 'admin'|'wing'|'nurse'|'restroom'; note?: string | null }) {
  // Backend accepts student/student_id and class_id/classroom
  const res = await api.post('/v1/attendance/exit-events/', payload);
  return res.data as { id: number; started_at: string };
}

export async function patchExitReturn(id: number) {
  const res = await api.patch(`/v1/attendance/exit-events/${id}/return/`, {});
  return res.data as { id: number; returned_at: string; duration_seconds: number };
}

export async function getExitEvents(params: { date?: string; class_id?: number; student_id?: number }) {
  const res = await api.get('/v1/attendance/exit-events/', { params });
  return res.data as { id: number; student_id: number; classroom_id?: number; date: string; started_at: string; returned_at?: string | null; duration_seconds?: number | null; reason?: string | null }[];
}