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
