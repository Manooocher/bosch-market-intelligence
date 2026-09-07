/**
 * Date/time helpers shared across the frontend.
 */

/**
 * Hours elapsed since an ISO timestamp, rounded to the nearest whole hour.
 * Returns `null` when the input is missing or unparseable.
 *
 * @param iso ISO-8601 timestamp string (e.g. from the API), or null/empty.
 * @returns whole hours since the timestamp (never negative), or null.
 */
export function freshnessHours(iso: string | null): number | null {
  if (!iso) return null;
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return null;
  return Math.max(0, Math.round((Date.now() - t) / 3600000));
}