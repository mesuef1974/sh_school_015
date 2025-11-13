import { api } from "../../shared/api/client";

export async function listBehaviorLevels(params: any = {}) {
  const res = await api.get("/v1/discipline/behavior-levels/", { params });
  return res.data;
}

export async function listViolations(params: any = {}) {
  const res = await api.get("/v1/discipline/violations/", { params });
  return res.data;
}

export async function listIncidents(params: any = {}, opts: any = {}) {
  const res = await api.get("/v1/discipline/incidents/", { params, ...(opts || {}) });
  return res.data;
}

export async function getIncident(id: string) {
  const res = await api.get(`/v1/discipline/incidents/${id}/`);
  return res.data;
}

export async function createIncident(payload: any) {
  const res = await api.post("/v1/discipline/incidents/", payload);
  return res.data;
}

export async function submitIncident(id: string) {
  const res = await api.post(`/v1/discipline/incidents/${id}/submit/`);
  return res.data;
}

export async function reviewIncident(id: string) {
  const res = await api.post(`/v1/discipline/incidents/${id}/review/`);
  return res.data;
}

export async function addIncidentAction(id: string, payload: any) {
  const res = await api.post(`/v1/discipline/incidents/${id}/add-action/`, payload);
  return res.data;
}

export async function addIncidentSanction(id: string, payload: any) {
  const res = await api.post(`/v1/discipline/incidents/${id}/add-sanction/`, payload);
  return res.data;
}

export async function escalateIncident(id: string) {
  const res = await api.post(`/v1/discipline/incidents/${id}/escalate/`);
  return res.data;
}

export async function notifyGuardian(id: string, payload: any = { channel: "internal" }) {
  const res = await api.post(`/v1/discipline/incidents/${id}/notify-guardian/`, payload);
  return res.data;
}

export async function closeIncident(id: string) {
  const res = await api.post(`/v1/discipline/incidents/${id}/close/`);
  return res.data;
}

export async function appealIncident(id: string, payload: { reason?: string } = {}) {
  const res = await api.post(`/v1/discipline/incidents/${id}/appeal/`, payload);
  return res.data;
}

export async function reopenIncident(id: string, payload: { note?: string } = {}) {
  const res = await api.post(`/v1/discipline/incidents/${id}/reopen/`, payload);
  return res.data;
}

export async function getKanban(params: any = {}) {
  const res = await api.get("/v1/discipline/incidents/kanban/", { params });
  return res.data;
}

export async function getIncidentsMine(params: any = {}, opts: any = {}) {
  const res = await api.get("/v1/discipline/incidents/mine/", { params, ...(opts || {}) });
  return res.data;
}

export async function getIncidentsVisible(params: any = {}) {
  const res = await api.get("/v1/discipline/incidents/visible/", { params });
  return res.data;
}

export async function getIncidentsSummary(params: any = {}) {
  const res = await api.get("/v1/discipline/incidents/summary/", { params });
  return res.data as {
    total: number;
    by_status: { open: number; under_review: number; closed: number };
    by_severity: Record<string, number>;
  };
}

export async function getIncidentsOverview(params: { days?: 7 | 30 } = {}) {
  // نظرة عامة اختيارية للمشرفين: إجماليات وتجاوزات ومخالفات متكررة. لا تؤثر على /summary/.
  const res = await api.get("/v1/discipline/incidents/overview/", { params });
  return res.data as {
    since: string;
    totals: { all: number };
    by_status: { open: number; under_review: number; closed: number };
    by_severity: Record<string, number>;
    top_violations: Array<{ code: string; category?: string | null; count: number }>;
    overdue: { review: number; notify: number };
  };
}

export async function countIncidentsByStudent(params: { student?: string[]; student_ids?: string }) {
  // DRF expects either repeated ?student=1&student=2 or a CSV via ?student_ids=1,2.
  // Axios serializes arrays as student[]=1&student[]=2 by default, which DRF won't read with getlist('student').
  // To be robust, convert any incoming array to a CSV under student_ids.
  const idsArr = Array.isArray(params?.student)
    ? (params.student as string[])
    : (typeof params?.student_ids === 'string' && params.student_ids
        ? params.student_ids.split(',').map((s) => s.trim()).filter(Boolean)
        : []);
  const csv = idsArr.length ? idsArr.join(',') : (params?.student_ids || '');
  const finalParams: any = {};
  if (csv) finalParams.student_ids = csv;
  const res = await api.get("/v1/discipline/incidents/count-by-student/", { params: finalParams });
  return res.data as Record<string, number>;
}

export async function getCommitteeSuggest(
  incidentId: string,
  params: { member_count?: number; exclude?: string } = {}
) {
  const res = await api.get(`/v1/discipline/incidents/${incidentId}/committee-suggest/`, { params });
  return res.data as {
    panel: {
      chair: { id: number; username?: string; full_name?: string; staff_full_name?: string } | null;
      members: Array<{ id: number; username?: string; full_name?: string; staff_full_name?: string }>;
      recorder: { id: number; username?: string; full_name?: string; staff_full_name?: string } | null;
    };
    pools: { chairs: number; members: number; recorders: number };
    algorithm: string;
    access_caps?: {
      can_schedule?: boolean;
      can_decide?: boolean;
      is_committee_member?: boolean;
      is_staff?: boolean;
      is_superuser?: boolean;
    };
    role_powers?: Record<string, string[]>;
    candidates?: Array<{ id: number; username?: string; full_name?: string; staff_full_name?: string }>;
  };
}
