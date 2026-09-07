import { describe, expect, it } from 'vitest';
import { formatPrice, formatNumber, formatPercent, formatDate } from './format';

describe('formatPrice', () => {
  it('formats null as dash', () => {
    expect(formatPrice(null)).toBe('—');
  });

  it('formats undefined as dash', () => {
    expect(formatPrice(undefined)).toBe('—');
  });

  it('formats zero as Persian zero (non-dash)', () => {
    expect(formatPrice(0)).toBe('۰');
  });

  it('applies fa-IR digit grouping', () => {
    expect(formatPrice(1234567)).toBe('۱٬۲۳۴٬۵۶۷');
  });
});

describe('formatNumber alias', () => {
  it('behaves identically to formatPrice for a price', () => {
    expect(formatNumber(123456)).toBe(formatPrice(123456));
  });

  it('returns dash for null like formatPrice', () => {
    expect(formatNumber(null)).toBe(formatPrice(null));
  });
});

describe('formatPercent', () => {
  it('returns dash for null', () => {
    expect(formatPercent(null)).toBe('—');
  });

  it('formats zero as 0.0%', () => {
    expect(formatPercent(0)).toBe('0.0%');
  });

  it('prefixes positive values with + and rounds to 1 decimal', () => {
    expect(formatPercent(12.345)).toBe('+12.3%');
  });

  it('keeps negatives signed and rounds to 1 decimal', () => {
    expect(formatPercent(-5.67)).toBe('-5.7%');
  });
});

describe('formatDate', () => {
  it('returns dash for null', () => {
    expect(formatDate(null)).toBe('—');
  });

  it('returns dash for an unparseable date', () => {
    expect(formatDate('not-a-date')).toBe('—');
  });

  it('formats a valid date to a non-empty string', () => {
    const out = formatDate('2026-09-08T12:00:00Z');
    expect(out).toBeTruthy();
    expect(out).not.toBe('—');
  });
});