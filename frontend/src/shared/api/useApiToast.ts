import { useToast } from "vue-toastification";
import { normalizeApiError, type ApiError } from "./client";

/**
 * Extract a human-friendly error message from any error-like object.
 * - Prefers unified ApiError shape from our Axios interceptor
 * - Falls back to generic message or JSON-stringified payload
 */
export function getErrorMessage(err: unknown, fallback = "حدث خطأ غير متوقع"): string {
  try {
    const norm = normalizeApiError(err as any) as ApiError | null;
    if (norm) {
      if (norm.message) return norm.message;
      if (norm.details && typeof norm.details === "object") return JSON.stringify(norm.details);
    }
    const msg = (err as any)?.message || (typeof err === "string" ? err : "");
    return msg || fallback;
  } catch {
    return fallback;
  }
}

/**
 * Show an error toast using a normalized message. Intended for catch blocks.
 * Example:
 *   try { await load(); } catch (e) { showApiErrorToast(e, 'تعذّر تحميل البيانات'); }
 */
export function showApiErrorToast(err: unknown, fallback?: string) {
  const toast = useToast();
  const msg = getErrorMessage(err, fallback);
  toast.error(msg, { timeout: 6000, closeOnClick: true });
}

/**
 * Helper to wrap an async function with consistent API error handling and toast.
 * It rethrows the original error after showing the toast (so callers can still handle it if needed).
 */
export async function withApiToast<T>(fn: () => Promise<T>, fallback?: string): Promise<T> {
  try {
    return await fn();
  } catch (e) {
    showApiErrorToast(e, fallback);
    throw e;
  }
}
