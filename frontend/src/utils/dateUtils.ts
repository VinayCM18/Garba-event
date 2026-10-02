/**
 * Centralized Timezone & Date Formatting Utilities for NAVRANG 2026 Management Portal.
 *
 * All management-facing timestamps MUST be displayed in:
 * - IST: India Standard Time
 * - IANA Timezone: 'Asia/Kolkata'
 * - UTC Offset: UTC+05:30
 *
 * Standard Display Format:
 * DD MMM YYYY, hh:mm A (e.g., "02 Oct 2026, 12:47 PM")
 *
 * Works identically across:
 * - Local Development
 * - Vercel Frontend
 * - Railway Backend
 * - Desktop and Mobile Browsers
 * Independent of user browser, OS, or server system timezone.
 */

export const IST_TIMEZONE = 'Asia/Kolkata';

export interface FormatDateTimeOptions {
  includeSeconds?: boolean;
  fallback?: string;
}

/**
 * Safely parses any date representation (ISO string, epoch seconds, epoch ms, Date) into a valid Date object.
 *
 * CRITICAL RULE:
 * If an ISO date-time string does NOT include a timezone offset (Z, +, or -),
 * it originated as a UTC-naive timestamp from the backend/database.
 * We normalize it by appending 'Z' so JavaScript Date ALWAYS parses it as UTC,
 * preventing browser-local timezone drift.
 */
export function parseToDate(input: string | number | Date | null | undefined): Date | null {
  if (input === null || input === undefined) return null;

  if (input instanceof Date) {
    return isNaN(input.getTime()) ? null : input;
  }

  if (typeof input === 'number') {
    // If integer looks like Unix seconds (< 10,000,000,000), multiply by 1000 to ms
    const ms = input < 10000000000 ? input * 1000 : input;
    const d = new Date(ms);
    return isNaN(d.getTime()) ? null : d;
  }

  if (typeof input === 'string') {
    let s = input.trim();
    if (!s) return null;

    // Check if numeric string (e.g. unix epoch in string form)
    if (/^\d+$/.test(s)) {
      const num = Number(s);
      const ms = num < 10000000000 ? num * 1000 : num;
      const d = new Date(ms);
      return isNaN(d.getTime()) ? null : d;
    }

    // Check if ISO string lacks timezone indicator (e.g. "2026-10-02T07:17:00" or "2026-10-02 07:17:00")
    if (/^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2}(\.\d+)?)?$/.test(s)) {
      s = s.replace(' ', 'T') + 'Z';
    }

    const d = new Date(s);
    return isNaN(d.getTime()) ? null : d;
  }

  return null;
}

/**
 * Formats a timestamp into standard IST date & time.
 * Example output: "02 Oct 2026, 12:47 PM"
 * With includeSeconds: "02 Oct 2026, 12:47:00 PM"
 */
export function formatDateTimeIST(
  input: string | number | Date | null | undefined,
  options: FormatDateTimeOptions = {}
): string {
  const d = parseToDate(input);
  if (!d) return options.fallback ?? '—';

  const formatter = new Intl.DateTimeFormat('en-IN', {
    timeZone: IST_TIMEZONE,
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: options.includeSeconds ? '2-digit' : undefined,
    hour12: true,
  });

  return formatter.format(d).replace(/(\b[ap]m\b)/gi, (m) => m.toUpperCase());
}

/**
 * Formats a timestamp into standard IST date only.
 * Example output: "02 Oct 2026"
 */
export function formatDateIST(
  input: string | number | Date | null | undefined,
  options: { fallback?: string } = {}
): string {
  const d = parseToDate(input);
  if (!d) return options.fallback ?? '—';

  const formatter = new Intl.DateTimeFormat('en-IN', {
    timeZone: IST_TIMEZONE,
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });

  return formatter.format(d);
}

/**
 * Formats a timestamp into standard IST 12-hour time only.
 * Example output: "12:47 PM"
 * With includeSeconds: "12:47:00 PM"
 */
export function formatTimeIST(
  input: string | number | Date | null | undefined,
  options: { includeSeconds?: boolean; fallback?: string } = {}
): string {
  const d = parseToDate(input);
  if (!d) return options.fallback ?? '—';

  const formatter = new Intl.DateTimeFormat('en-IN', {
    timeZone: IST_TIMEZONE,
    hour: '2-digit',
    minute: '2-digit',
    second: options.includeSeconds ? '2-digit' : undefined,
    hour12: true,
  });

  return formatter.format(d).replace(/(\b[ap]m\b)/gi, (m) => m.toUpperCase());
}

/**
 * Returns current live time in IST.
 * Useful for navbar live clocks.
 * Example output: "12:47:00 PM"
 */
export function getCurrentISTTimeString(includeSeconds = true): string {
  return formatTimeIST(new Date(), { includeSeconds });
}
