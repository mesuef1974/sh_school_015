// Simple offline queue for attendance POST requests (dev-friendly, zero deps)
// Stores items in localStorage and retries on 'online' event.
// NOTE: This is a lightweight Phase-1 scaffold; replace with IndexedDB for scale if needed.

export type AttendanceBulkItem = {
  class_id: number;
  date: string;
  records: { student_id: number; status: string; note?: string | null }[];
};

const KEY = 'attendance_offline_queue_v1';

function readQueue(): AttendanceBulkItem[] {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return [];
    const arr = JSON.parse(raw);
    return Array.isArray(arr) ? (arr as AttendanceBulkItem[]) : [];
  } catch {
    return [];
  }
}

function writeQueue(items: AttendanceBulkItem[]) {
  try {
    localStorage.setItem(KEY, JSON.stringify(items));
  } catch {
    // ignore
  }
}

export function getQueueLength(): number {
  return readQueue().length;
}

export function enqueueAttendance(item: AttendanceBulkItem) {
  const q = readQueue();
  q.push(item);
  writeQueue(q);
}

export async function flushAttendanceQueue(postFn: (p: AttendanceBulkItem) => Promise<any>): Promise<{ flushed: number; failed: number }> {
  const q = readQueue();
  if (q.length === 0) return { flushed: 0, failed: 0 };
  let flushed = 0;
  const remaining: AttendanceBulkItem[] = [];
  for (const item of q) {
    try {
      await postFn(item);
      flushed += 1;
    } catch {
      remaining.push(item);
    }
  }
  writeQueue(remaining);
  return { flushed, failed: remaining.length };
}

let initialized = false;

import { postBulkSave } from "../../api/attendance";

export function initOfflineQueue(postFn?: (p: AttendanceBulkItem) => Promise<any>) {
  if (initialized) return;
  initialized = true;
  const runner = async (item: AttendanceBulkItem) => {
    if (postFn) return postFn(item);
    // default implementation uses our API adapter
    const { class_id, date, records } = item;
    return postBulkSave({ class_id, date, records });
  };
  window.addEventListener('online', () => {
    flushAttendanceQueue(runner).catch(() => {});
  });
}