// Shared date formatting utilities
// Goal: Display all user-visible dates as DD:MM:YYYY while keeping API payloads in ISO when needed.

export type DateInput = string | number | Date | null | undefined;

/**
 * Formats a variety of date inputs to DD:MM:YYYY (day:month:year) using Latin digits.
 * - Pass-through for already formatted DD:MM:YYYY
 * - Supports ISO YYYY-MM-DD
 * - Supports slash formats MM/DD/YYYY and DD/MM/YYYY with deterministic heuristic
 * - Falls back to Date parsing if possible; otherwise returns the original string
 */
export function formatDateDMY(input: DateInput): string {
  if (input == null) return '';
  const raw = String(input).trim();
  if (!raw) return '';
  // 1) Already in DD:MM:YYYY
  if (/^\d{2}:\d{2}:\d{4}$/.test(raw)) return raw;
  // 2) ISO YYYY-MM-DD
  let m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(raw);
  if (m) {
    const [, y, mo, d] = m;
    return `${d}:${mo}:${y}`;
  }
  // 3) Slash-separated (MM/DD/YYYY or DD/MM/YYYY)
  m = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(raw);
  if (m) {
    let [_, a, b, y] = m;
    let d = a, mo = b;
    if (parseInt(a, 10) <= 12 && parseInt(b, 10) > 12) {
      // US style MM/DD
      d = b; mo = a;
    } else if (parseInt(a, 10) > 12 && parseInt(b, 10) <= 12) {
      // EU style DD/MM
      d = a; mo = b;
    } else {
      // ambiguous (both <= 12): default to MM/DD
      d = b; mo = a;
    }
    return `${d.padStart(2,'0')}:${mo.padStart(2,'0')}:${y}`;
  }
  // 4) Fallback: try JS Date
  const dt = new Date(raw);
  if (!isNaN(dt.getTime())) {
    const dd = String(dt.getDate()).padStart(2, '0');
    const mm = String(dt.getMonth() + 1).padStart(2, '0');
    const yyyy = dt.getFullYear();
    return `${dd}:${mm}:${yyyy}`;
  }
  return raw;
}

/** Convert Date to ISO YYYY-MM-DD string. */
export function toIsoDate(d: Date): string {
  return d.toISOString().slice(0, 10);
}