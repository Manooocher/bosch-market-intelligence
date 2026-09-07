/**
 * Format a number as a Persian (fa-IR) localized string with digit grouping.
 * Returns an em-dash placeholder for null/undefined.
 */
export function formatPrice(amount: number | null | undefined): string {
  if (amount === null || amount === undefined) return '—';
  return new Intl.NumberFormat('fa-IR').format(amount);
}

/**
 * Alias of {@link formatPrice} kept for call-site readability (e.g. counts
 * vs. prices). Identical behavior.
 */
export const formatNumber = formatPrice;

export function formatPercent(value: number | null): string {
  if (value === null || value === undefined) return '—';
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(1)}%`;
}

export function formatDate(dateStr: string | null): string {
  if (!dateStr) return '—';
  const date = new Date(dateStr);
  if (Number.isNaN(date.getTime())) return '—';
  return new Intl.DateTimeFormat('fa-IR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}
