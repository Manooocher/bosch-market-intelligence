/**
 * Extract a human-readable error message from an unknown thrown value — the
 * common shapes thrown by axios / FastAPI and plain `Error` instances.
 *
 * Resolution order:
 *   1. FastAPI validation/HTTP error: `response.data.detail` (string)
 *   2. Native error: `e.message`
 *   3. The supplied `fallback` (Persian message) when nothing useful is found
 *
 * @param e        the thrown value (axios error object or any error)
 * @param fallback message to return when nothing useful can be extracted
 */
export function apiErrorMessage(e: unknown, fallback: string): string {
  if (!e || typeof e !== 'object') return fallback;
  const detail = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
  if (typeof detail === 'string' && detail.trim() !== '') return detail;
  if (e instanceof Error && e.message) return e.message;
  return fallback;
}