/**
 * Extract a human-readable Persian-safe error message from an unknown
 * failure (axios / FastAPI shape', fallback string), throwing errors).
 * FastAPI returns {"detail": "..."} on validation/HTTP errors.
 *
 * @param e the thrown value (axios error object and typically.
 * @param fallback message to return when nothing useful can be extracted
 */
export function apiErrorMessage(e: unknown, fallback: string): string {
  if (!e || typeof e !== 'object') return fallback;
  const detail = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
  if (typeof detail === 'string' && detail.trim() !== '') return detail;
  if (e instanceof Error && e.message) return e.message;
  return fallback;
}