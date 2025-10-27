// Minimal attendance API adapter for offline queue flush and teacher bulk save
// Aligns with backend AttendanceViewSet.bulk_save

export type BulkRecord = { student_id: number; status: string; note?: string | null };

export async function postBulkSave(params: {
  class_id: number;
  date: string; // YYYY-MM-DD
  records: BulkRecord[];
  period_number?: number | null;
}): Promise<{ saved: number }> {
  const url = "/api/attendance/bulk-save";
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
    credentials: "include",
  });
  if (!resp.ok) {
    const txt = await resp.text();
    throw new Error(`bulk-save failed: ${resp.status} ${txt}`);
  }
  return resp.json();
}

import { api } from "../shared/api/client";

export async function postSubmit(params: {
  class_id: number;
  date: string; // YYYY-MM-DD
  period_number?: number | null;
}): Promise<{ submitted: number; class_id: number; date: string; period_number?: number | null }> {
  // Use shared Axios client to ensure Authorization header and token refresh logic are applied
  const res = await api.post('/attendance/submit/', params);
  return res.data as { submitted: number; class_id: number; date: string; period_number?: number | null };
}