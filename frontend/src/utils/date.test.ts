import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { freshnessHours } from './date';

describe('freshnessHours', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-09-08T12:00:00Z'));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('returns null for null input', () => {
    expect(freshnessHours(null)).toBeNull();
  });

  it('returns null for empty-string input', () => {
    expect(freshnessHours('')).toBeNull();
  });

  it('returns null for an invalid date', () => {
    expect(freshnessHours('not-a-date')).toBeNull();
  });

  it('returns the whole-hour difference for a valid ISO date', () => {
    expect(freshnessHours('2026-09-08T06:00:00Z')).toBe(6);
  });

  it('never returns a negative value for future timestamps', () => {
    expect(freshnessHours('2026-09-09T00:00:00Z')).toBe(0);
  });
});