// Shared date formatting utilities
// Goal: Display all user-visible dates as DD/MM/YYYY while keeping API payloads in ISO when needed.

export type DateInput = string | number | Date | null | undefined;

/**
 * Formats a variety of date inputs to DD/MM/YYYY (day/month/year) using Latin digits.
 * - Pass-through for already formatted DD/MM/YYYY
 * - Supports ISO YYYY-MM-DD
 * - Supports slash formats MM/DD/YYYY and DD/MM/YYYY with deterministic heuristic
 * - Falls back to Date parsing if possible; otherwise returns the original string
 */
export function formatDateDMY(input: DateInput): string {
  if (input == null) return "";
  const raw = String(input).trim();
  if (!raw) return "";
  // 1) Already in DD/MM/YYYY
  if (/^\d{2}\/\d{2}\/\d{4}$/.test(raw)) return raw;
  // 2) ISO YYYY-MM-DD
  let m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(raw);
  if (m) {
    const [, y, mo, d] = m;
    return `${d}/${mo}/${y}`;
  }
  // 3) Slash-separated (MM/DD/YYYY or DD/MM/YYYY)
  m = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(raw);
  if (m) {
    let [_, a, b, y] = m;
    let d = a,
      mo = b;
    if (parseInt(a, 10) <= 12 && parseInt(b, 10) > 12) {
      // US style MM/DD
      d = b;
      mo = a;
    } else if (parseInt(a, 10) > 12 && parseInt(b, 10) <= 12) {
      // EU style DD/MM
      d = a;
      mo = b;
    } else {
      // ambiguous (both <= 12): default to MM/DD
      d = b;
      mo = a;
    }
    return `${String(d).padStart(2, "0")}/${String(mo).padStart(2, "0")}/${y}`;
  }
  // 4) Fallback: try JS Date
  const dt = new Date(raw);
  if (!isNaN(dt.getTime())) {
    const dd = String(dt.getDate()).padStart(2, "0");
    const mm = String(dt.getMonth() + 1).padStart(2, "0");
    const yyyy = dt.getFullYear();
    return `${dd}/${mm}/${yyyy}`;
  }
  return raw;
}

/** Strictly validate DD/MM/YYYY (1-31/1-12/4-digit year) and logical date. */
export function isValidDMY(s: string | null | undefined): boolean {
  if (!s) return false;
  const m = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(String(s).trim());
  if (!m) return false;
  const d = parseInt(m[1], 10);
  const mo = parseInt(m[2], 10);
  const y = parseInt(m[3], 10);
  if (mo < 1 || mo > 12 || d < 1 || d > 31) return false;
  const dt = new Date(y, mo - 1, d);
  return dt.getFullYear() === y && dt.getMonth() === mo - 1 && dt.getDate() === d;
}

/** Convert DD/MM/YYYY to ISO YYYY-MM-DD. Returns null if invalid. */
export function parseDMYtoISO(s: string | null | undefined): string | null {
  if (!isValidDMY(s || "")) return null;
  const [d, m, y] = (s as string).split("/");
  return `${y}-${m.padStart(2, "0")}-${d.padStart(2, "0")}`;
}

/** Format ISO YYYY-MM-DD to DD/MM/YYYY. Returns empty string if invalid. */
export function formatISOtoDMY(s: string | null | undefined): string {
  if (!s) return "";
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(s).trim());
  if (!m) return "";
  const [, y, mo, d] = m;
  return `${d}/${mo}/${y}`;
}

/** Convert Date to ISO YYYY-MM-DD string. */
export function toIsoDate(d: Date): string {
  return d.toISOString().slice(0, 10);
}
