import axios from "axios";
import {
  enqueueAttendance,
  flushAttendanceQueue,
  initOfflineQueue,
  type AttendanceBulkItem,
} from "../offline/queue";

// Backward-compat key (kept for a transitional period). Avoid using localStorage for access tokens.

// In-memory access token holder (preferred over localStorage)
let accessToken: string | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
}

export const api = axios.create({
  baseURL: "/api",
  withCredentials: true,
  timeout: 8000, // fail fast in dev if backend is down
});

export type ApiError = {
  status?: number;
  code?: string;
  message: string;
  details?: any;
  original?: any;
};

export function normalizeApiError(err: any): ApiError | null {
  try {
    const status = err?.response?.status;
    const data = err?.response?.data;
    if (data?.error) {
      const code = data.error.code || undefined;
      const message = (data.error.message as string) || err?.message || "Request failed";
      const details = data.error.details;
      return { status, code, message, details, original: err };
    }
    // Axios/network error (no HTTP response or generic network/timeout)
    if (
      !err?.response ||
      err?.code === 'ERR_NETWORK' ||
      err?.code === 'ECONNABORTED' ||
      /timeout/i.test(err?.message || '') ||
      (typeof err?.message === 'string' && err.message.includes('Network Error'))
    ) {
      return {
        status: undefined,
        code: 'NETWORK_ERROR',
        message: err?.message || 'تعذّر الاتصال بالخادم',
        details: null,
        original: err,
      };
    }
    // Fallback: construct from status/text
    const message = err?.message || `HTTP ${status || ''}`.trim();
    return { status, code: undefined, message, details: data, original: err };
  } catch {
    return { message: 'Unknown error', details: null } as ApiError;
  }
}

// Initialize offline queue to auto-flush queued attendance on connectivity regain
initOfflineQueue(async (p: AttendanceBulkItem) => {
  await api.post("/v1/attendance/bulk_save/", p);
});

// Attach Authorization header if token exists (in-memory only)
api.interceptors.request.use((config) => {
  const token = accessToken;
  if (token) {
    config.headers = config.headers || {};
    (config.headers as any)["Authorization"] = `Bearer ${token}`;
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
      (original as any)._retry = true;
      try {
        refreshing = refreshing ?? refreshAccessToken();
        const newToken = await refreshing.finally(() => (refreshing = null));
        if (newToken) {
          setAccessToken(newToken);
          original.headers = original.headers || {};
          (original.headers as any)["Authorization"] = `Bearer ${newToken}`;
          return api(original);
        }
      } catch {}
    }
    if (status === 401 && location.pathname !== "/login") {
      // Could not refresh → redirect to login
      window.location.href = "/login";
    }
    // Normalize backend error envelope { error: { code, message, details } }
    const payload = err?.response?.data as any;
    const normalized = normalizeApiError(err);
    return Promise.reject(normalized ?? payload ?? err);
  }
);

async function refreshAccessToken(): Promise<string | null> {
  try {
    // Prefer HttpOnly cookie on server. If not available yet, fallback to stored refresh (temporary)
    const storedRefresh = localStorage.getItem("sh_school_refresh");
    const body = storedRefresh ? { refresh: storedRefresh } : {};
    const res = await axios.post("/api/token/refresh/", body, { withCredentials: true });
    const data = res.data as { access?: string };
    if (data?.access) {
      return data.access;
    }
    return null;
  } catch {
    return null;
  }
}

export async function getAttendanceStudents(params: { class_id: number; date?: string }) {
  const res = await api.get("/v1/attendance/students/", { params });
  return res.data as { students: any[]; date: string; class_id: number };
}

export async function getAttendanceRecords(params: {
  class_id: number;
  date?: string;
  period_number?: number | null;
}) {
  const res = await api.get("/v1/attendance/records/", { params });
  return res.data as {
    records: {
      student_id: number;
      status: string;
      note?: string | null;
      exit_reasons?: string | string[] | null;
    }[];
    date: string;
    class_id: number;
    period_number?: number | null;
  };
}

export async function getAttendanceHistory(params: {
  class_id: number;
  from?: string;
  to?: string;
  page?: number;
  page_size?: number;
}) {
  // Use strict history endpoint to ensure results are only from the selected class
  const res = await api.get("/v1/attendance/history-strict/", { params });
  return res.data as {
    count: number;
    page: number;
    page_size: number;
    from: string;
    to: string;
    class_id: number;
    results: {
      date: string;
      student_id: number;
      student_name?: string | null;
      status: string;
      note?: string | null;
    }[];
  };
}

export async function getAttendanceSummary(
  params: {
    scope?: "teacher" | "wing" | "school";
    date?: string;
    class_id?: number;
    wing_id?: number;
  } = {}
) {
  const res = await api.get("/v1/attendance/summary/", { params });
  return res.data as {
    date: string;
    scope: string;
    kpis: {
      present_pct: number;
      absent_pct?: number;
      effective_total?: number;
      absent: number;
      late: number;
      excused: number;
      exit_events_total?: number;
      exit_events_open?: number;
      present?: number;
      total?: number;
    };
    top_classes: { class_id: number; class_name?: string | null; present_pct: number }[];
    worst_classes: { class_id: number; class_name?: string | null; present_pct: number }[];
  };
}

export async function getTeacherClasses() {
  const res = await api.get("/v1/attendance/teacher/classes/");
  return res.data as { classes: { id: number; name?: string }[] };
}

export async function getTeacherTimetableToday(params: { date?: string } = {}) {
  const res = await api.get("/v1/attendance/timetable/teacher/today/", { params });
  return res.data as {
    date: string;
    periods: {
      period_number: number;
      classroom_id: number;
      classroom_name?: string;
      subject_id: number;
      subject_name?: string;
      start_time?: string;
      end_time?: string;
    }[];
  };
}

export async function getTeacherTimetableWeekly() {
  const res = await api.get("/v1/attendance/timetable/teacher/weekly/");
  return res.data as {
    days: Record<
      string,
      {
        period_number: number;
        classroom_id: number;
        classroom_name?: string;
        subject_id: number;
        subject_name?: string;
        start_time?: string;
        end_time?: string;
      }[]
    >;
    meta: any;
  };
}

export async function getWingTimetable(
  params: { wing_id?: number; date?: string; mode?: "daily" | "weekly" } = {}
) {
  const res = await api.get("/v1/wing/timetable/", { params });
  return res.data as
    | {
        mode: "daily";
        date: string;
        dow: number;
        term_id?: number;
        wing_id: number;
        items: {
          class_id: number;
          class_name?: string | null;
          period_number: number;
          subject_id: number;
          subject_name?: string | null;
          teacher_id: number;
          teacher_name?: string | null;
          color?: string;
        }[];
      }
    | {
        mode: "weekly";
        term_id?: number;
        wing_id: number;
        days: Record<
          string,
          {
            class_id: number;
            class_name?: string | null;
            period_number: number;
            subject_id: number;
            subject_name?: string | null;
            teacher_id: number;
            teacher_name?: string | null;
            color?: string;
          }[]
        >;
      };
}

export async function postAttendanceBulkSave(payload: {
  class_id: number;
  date: string;
  period_number?: number;
  records: {
    student_id: number;
    status: string;
    note?: string | null;
    exit_reasons?: string | string[];
  }[];
}) {
  try {
    const res = await api.post("/v1/attendance/bulk_save/", payload);
    return res.data as { saved: number };
  } catch (e: any) {
    // Network-level failure → queue for later sync (offline-first behavior)
    const hasResponse = !!e?.response;
    if (!hasResponse) {
      try {
        enqueueAttendance(payload as AttendanceBulkItem);
      } catch {}
      return { saved: payload.records.length, queued: true } as any;
    }
    throw e;
  }
}

export async function flushAttendanceQueueNow() {
  return flushAttendanceQueue(async (p) => (await api.post("/v1/attendance/bulk_save/", p)).data);
}

export async function login(username: string, password: string) {
  const res = await axios.post("/api/token/", { username, password }, { withCredentials: true });
  const data = res.data as { access: string; refresh?: string };
  // Store access in-memory (preferred)
  setAccessToken(data.access);
  // Transitional: keep refresh if backend still returns it and cookie not yet configured
  if (data.refresh) {
    try {
      localStorage.setItem("sh_school_refresh", data.refresh);
    } catch {}
  }
  return data;
}

export async function logout() {
  try {
    const refresh = localStorage.getItem("sh_school_refresh");
    const body = refresh ? { refresh } : {};
    await api.post("/logout/", body);
  } catch {
    // ignore errors on logout to be resilient
  } finally {
    // Clear in-memory token and any stored refresh
    setAccessToken(null);
    try {
      localStorage.removeItem("sh_school_refresh");
    } catch {}

    // Clear wing-specific UI caches/preferences
    try {
      localStorage.removeItem("wing_selected_classes");
    } catch {}
    try {
      localStorage.removeItem("wing_approvals_prefs");
    } catch {}
    try {
      localStorage.removeItem("wing_tt_weekly_col_widths");
    } catch {}

    // Clear wing context singleton and query caches
    try {
      const wc = await import("../composables/useWingContext");
      if (wc && typeof (wc as any).clearWingContext === "function") {
        (wc as any).clearWingContext();
      }
    } catch {}
    try {
      const qc = await import("../queryClient");
      const queryClient = (qc as any).queryClient;
      if (queryClient && typeof queryClient.clear === "function") {
        queryClient.clear();
      }
    } catch {}

    // Clear authenticated state in Pinia (if store is initialized)
    try {
      const mod = await import("../../app/stores/auth");
      const useAuthStore = (mod as any).useAuthStore as () => { clear: () => void };
      if (useAuthStore) {
        try {
          useAuthStore().clear();
        } catch {}
      }
    } catch {}

    // Best-effort: navigate to login and replace history to reduce back-navigation to protected routes
    try {
      const r = await import("../../app/router");
      const router = (r as any).router as any;
      if (router && typeof router.replace === "function") {
        await router.replace({ name: "login" });
      } else {
        window.location.href = "/login";
      }
    } catch {
      window.location.href = "/login";
    }
  }
}

export async function changePassword(payload: {
  current_password: string;
  new_password1: string;
  new_password2: string;
}) {
  const res = await api.post("/change_password/", payload);
  return res.data as { detail: string };
}

export async function getMe() {
  const res = await api.get("/me/");
  return res.data as {
    id: number;
    username: string;
    full_name: string;
    is_superuser: boolean;
    is_staff: boolean;
    roles: string[];
    permissions: string[];
    hasTeachingAssignments: boolean;
    capabilities?: {
      can_manage_timetable?: boolean;
      can_view_general_timetable?: boolean;
      can_take_attendance?: boolean;
    };
  };
}

// --- Exit Events API ---
export async function getOpenExitEvents(params: {
  class_id?: number;
  date?: string;
  student_id?: number;
  wing_id?: number;
}) {
  const res = await api.get("/v1/attendance/exit-events/open/", { params });
  return res.data as {
    id: number;
    student_id: number;
    student_name?: string | null;
    started_at: string;
    reason: string;
  }[];
}

export async function postExitEvent(payload: {
  student_id: number;
  class_id?: number;
  date: string;
  period_number?: number | null;
  reason: "admin" | "wing" | "nurse" | "restroom";
  note?: string | null;
}) {
  // Backend accepts student/student_id and class_id/classroom
  const res = await api.post("/v1/attendance/exit-events/", payload);
  return res.data as { id: number; started_at: string };
}

export async function patchExitReturn(id: number) {
  const res = await api.patch(`/v1/attendance/exit-events/${id}/return/`, {});
  return res.data as { id: number; returned_at: string; duration_seconds: number };
}

export async function postExitDecide(payload: { action: "approve" | "reject"; ids: number[]; comment?: string }) {
  const res = await api.post("/v1/attendance/exit-events/decide/", payload);
  return res.data as { updated: number; action: "approve" | "reject" };
}

export async function getExitEvents(params: {
  date?: string;
  class_id?: number;
  student_id?: number;
  review_status?: "submitted" | "approved" | "rejected";
  wing_id?: number;
}) {
  const res = await api.get("/v1/attendance/exit-events/", { params });
  const data = res.data as any;
  const items = Array.isArray(data) ? data : (data?.results ?? []);
  return items as {
    id: number;
    student_id: number;
    student_name?: string | null;
    classroom_id?: number;
    date: string;
    started_at: string;
    returned_at?: string | null;
    duration_seconds?: number | null;
    reason?: string | null;
    review_status?: "submitted" | "approved" | "rejected" | null;
    review_comment?: string | null;
    period_number?: number | null;
    note?: string | null;
  }[];
}

// ---- Wing Supervisor APIs (use relative /api to leverage Vite proxy and avoid CORS) ----
export async function getWingMe() {
  const res = await api.get("/v1/wing/me/");
  return res.data as {
    user: any;
    roles: string[];
    staff: { id?: number; full_name?: string | null };
    wings: { ids: number[]; names: string[] };
    primary_wing?: { id?: number | null; name?: string | null; number?: number | null; supervisor_full_name?: string | null } | null;
    has_wing_supervisor_role: boolean;
  };
}

export async function getWingOverview(params: { date?: string; wing_id?: number }) {
  const res = await api.get("/v1/wing/overview/", { params });
  return res.data as {
    date: string;
    scope: string;
    kpis: {
      present_pct: number;
      absent: number;
      late: number;
      excused: number;
      runaway: number;
      present: number;
      total: number;
      exit_events_total: number;
      exit_events_open: number;
    };
    top_classes: any[];
    worst_classes: any[];
  };
}

export async function getWingMissing(params: { date?: string; wing_id?: number }) {
  const res = await api.get("/v1/wing/missing/", { params });
  const data = res.data as any;
  // Normalize to stable shape { date?, count?, items: [] }
  const items = Array.isArray(data)
    ? data
    : Array.isArray(data?.items)
    ? data.items
    : Array.isArray(data?.results)
    ? data.results
    : [];
  const out = {
    date: (data && typeof data === "object" ? data.date : undefined) || (params?.date as any) || "",
    count: typeof data?.count === "number" ? data.count : undefined,
    items: items as {
      class_id: number;
      class_name?: string;
      period_number: number;
      subject_id: number;
      subject_name?: string;
      teacher_id: number;
      teacher_name?: string;
    }[],
  };
  return out;
}

// Classes that have attendance already entered (per period) for the wing
export async function getWingEntered(params: { date?: string; wing_id?: number }) {
  // Primary endpoint (new style under /wing)
  try {
    const res = await api.get("/v1/wing/entered/", { params });
    const data = res.data as any;
    const items = Array.isArray(data)
      ? data
      : Array.isArray(data?.items)
      ? data.items
      : Array.isArray(data?.results)
      ? data.results
      : [];
    return {
      date: (data && typeof data === "object" ? data.date : undefined) || (params?.date as any) || "",
      count: typeof data?.count === "number" ? data.count : undefined,
      items: items as any[],
    };
  } catch (e: any) {
    // Fallbacks for deployments exposing the endpoint under /v1
    const candidates = ["/v1/attendance/wing/entered/", "/v1/attendance/entered/"];
    for (const url of candidates) {
      try {
        const res = await api.get(url, { params });
        const data: any = res.data || {};
        // Normalize different shapes: some backends return { results: [...] }
        if (!data.items && Array.isArray(data.results)) {
          data.items = data.results;
          if (typeof data.count !== "number") data.count = data.results.length;
        }
        return data as {
          date: string;
          count?: number;
          items: {
            class_id: number;
            class_name?: string;
            period_number: number;
            subject_id: number;
            subject_name?: string;
            teacher_id: number;
            teacher_name?: string;
          }[];
        };
      } catch {
        // try next
      }
    }
    // None worked → rethrow original error to let caller handle gracefully
    throw e;
  }
}

// Approvals workflow (pending list and decisions)
export async function getWingPending(params: { date?: string; class_id?: number; wing_id?: number }) {
  const res = await api.get("/v1/wing/pending/", { params });
  return res.data as {
    date: string;
    count: number;
    items: {
      id: number;
      student_id: number;
      student_name?: string | null;
      class_id?: number;
      class_name?: string | null;
      period_number?: number | null;
      status: string;
      note?: string | null;
      subject_name?: string | null;
      teacher_name?: string | null;
    }[];
  };
}

export async function postWingDecide(payload: {
  action: "approve" | "reject";
  ids: number[];
  comment?: string;
}) {
  const res = await api.post("/v1/wing/decide/", payload);
  return res.data as { updated: number; action: "approve" | "reject" };
}

export async function postWingSetExcused(payload: {
  ids: number[];
  comment?: string;
  evidenceFile?: File | null;
  evidenceNote?: string;
}) {
  // When evidence file provided → send as multipart/form-data; else JSON
  if (payload.evidenceFile) {
    const fd = new FormData();
    // DRF parsers expect simple repeated fields or JSON string for arrays.
    // We'll send JSON string for ids to keep it simple.
    fd.append("ids", JSON.stringify(payload.ids));
    if (payload.comment) fd.append("comment", payload.comment);
    if (payload.evidenceNote) fd.append("evidence_note", payload.evidenceNote);
    fd.append("evidence", payload.evidenceFile);
    const res = await api.post("/v1/wing/set-excused/", fd, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return res.data as { updated: number; action: "set_excused"; evidence_saved?: number };
  } else {
    const { evidenceFile, evidenceNote, ...json } = payload as any;
    const res = await api.post("/v1/wing/set-excused/", json);
    return res.data as { updated: number; action: "set_excused" };
  }
}

// ---- UI Tiles Designer API ----
export async function getUiTilesEffective() {
  try {
    const res = await api.get("/ui/tiles/effective");
    return res.data as { version?: number; updated_by?: string | null; tiles: any[] };
  } catch {
    return { tiles: [] } as any;
  }
}

export async function postUiTilesSave(payload: { version?: number; tiles: any[] }) {
  const res = await api.post("/ui/tiles/save", payload);
  return res.data as { saved: number; version?: number };
}


// ---- Absence Alerts & Compute APIs ----
export async function getWingDailyAbsences(params: { date?: string; class_id?: number; wing_id?: number }) {
  const res = await api.get("/v1/wing/daily-absences/", { params });
  return res.data as {
    date: string;
    counts: { excused: number; unexcused: number; none: number };
    items: {
      student_id: number;
      student_name?: string | null;
      class_id?: number | null;
      class_name?: string | null;
      state: "excused" | "unexcused" | "none";
      p1?: string | null;
      p2?: string | null;
    }[];
  };
}

// ---- Absence Alerts & Compute APIs ----
export async function computeAbsenceDays(params: { student: number; from: string; to: string }) {
  const res = await api.get("/attendance/absence/compute-days/", { params });
  return res.data as { excused_days: number; unexcused_days: number; student: number; from: string; to: string };
}

export type AbsenceAlert = {
  id: number;
  number: number;
  academic_year: string;
  student: number;
  student_name?: string;
  class_name?: string;
  parent_name?: string;
  parent_mobile?: string;
  period_start: string;
  period_end: string;
  excused_days: number;
  unexcused_days: number;
  notes?: string;
  status: string;
  wing?: number | null;
  created_at: string;
  updated_at: string;
};

export async function createAbsenceAlert(payload: {
  student: number;
  period_start: string;
  period_end: string;
  notes?: string;
}) {
  const res = await api.post("/absence-alerts/", payload);
  return res.data as AbsenceAlert;
}

export function getAbsenceAlertDocxHref(id: number) {
  return api.getUri({ url: `/absence-alerts/${id}/docx/` });
}

export function getAbsenceAlertDocxPersistHref(id: number) {
  // server will generate and persist then return the file directly
  return api.getUri({ url: `/absence-alerts/${id}/docx/`, params: { persist: 1 } });
}

export function getAbsenceAlertDocxLatestHref(id: number) {
  return api.getUri({ url: `/absence-alerts/${id}/docx/latest/` });
}

// ---- Wing-scoped classes ----
export async function getWingClasses(params: { q?: string; wing_id?: number } = {}) {
  const res = await api.get("/v1/wing/classes/", { params });
  return res.data as {
    items: { id: number; name?: string | null; grade?: number | null; section?: string | null; wing_id?: number | null; wing_name?: string | null; students_count?: number | null }[];
  };
}

// ---- Wing-scoped students (picker) ----
export async function getWingStudents(params: { q?: string; class_id?: number; wing_id?: number }) {
  const res = await api.get("/v1/wing/students/", { params });
  return res.data as {
    items: {
      id: number;
      sid?: string | null;
      full_name?: string | null;
      class_id?: number | null;
      class_name?: string | null;
      parent_name?: string | null;
      parent_phone?: string | null;
      extra_phone_no?: string | null;
      phone_no?: string | null;
      active?: boolean | null;
      needs?: boolean | null;
    }[];
  };
}

// ---- Authenticated file downloads (Word exports) ----
export async function downloadFileWithAuth(url: string, params?: Record<string, any>, fallbackName?: string) {
  const res = await api.get(url, { params, responseType: "blob" });
  // Try to extract filename from Content-Disposition
  let filename = fallbackName || "download.docx";
  try {
    const cd = (res.headers as any)["content-disposition"] || (res.headers as any)["Content-Disposition"];
    if (cd) {
      const m = /filename\*=UTF-8''([^;]+)|filename="?([^";]+)"?/i.exec(cd);
      const name = decodeURIComponent(m?.[1] || m?.[2] || "");
      if (name) filename = name;
    }
  } catch {}
  const blob = res.data as Blob;
  const urlObj = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = urlObj;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(urlObj);
}

export async function downloadWingStudentsWord(params: { q?: string; class_id?: number; wing_id?: number }) {
  // Try multiple stable aliases to avoid any router/proxy quirks across environments
  const candidates = [
    backendUrl("/api/v1/wing/students/export.docx/"),
    backendUrl("/api/v1/wing/students/export.docx"),
    backendUrl("/api/v1/wing/students/export-docx/"),
    backendUrl("/api/v1/wing/students/export-docx"),
    // Dev-only extra tolerance (when /api/ is exposed alongside /api/v1/)
    backendUrl("/api/wing/students/export.docx/"),
    backendUrl("/api/wing/students/export.docx"),
  ];
  let lastErr: any = null;
  for (const url of candidates) {
    try {
      await downloadFileWithAuth(url, params, "wing-students.docx");
      return; // success
    } catch (e) {
      lastErr = e;
      // Try next alias
    }
  }
  // If all attempts failed, rethrow the last error to display a meaningful message upstream
  throw lastErr || new Error("فشل تنزيل ملف Word لقائمة الطلبة");
}

// ---- List Absence Alerts with filters ----
export async function listAbsenceAlerts(params: { student?: number; status?: string; from?: string; to?: string }) {
  const res = await api.get("/absence-alerts/", { params });
  return res.data as any; // DRF default list format
}
