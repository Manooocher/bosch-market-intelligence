import { describe, expect, it } from 'vitest';
import {
  getCategoryGroup,
  getCategoryLabel,
  getCategoryLabelFromKey,
  CATEGORY_GROUPS,
} from './categories';

describe('getCategoryGroup', () => {
  it('maps a known key to its group', () => {
    expect(getCategoryGroup('dishwasher')).toBe('Washing');
    expect(getCategoryGroup('refrigerator')).toBe('Cooling');
    expect(getCategoryGroup('microwave')).toBe('Cooking');
  });

  it('returns Other for an unknown key', () => {
    expect(getCategoryGroup('unknown_thing')).toBe('Other');
  });

  it('returns Other for null/undefined', () => {
    expect(getCategoryGroup(null)).toBe('Other');
    expect(getCategoryGroup(undefined)).toBe('Other');
  });
});

describe('getCategoryLabel', () => {
  it('returns the Persian label for a known key', () => {
    expect(getCategoryLabel('dishwasher')).toBe('ماشین ظرفشویی');
  });

  it('falls back to the raw key for unknown categories', () => {
    expect(getCategoryLabel('custom_thing')).toBe('custom_thing');
  });

  it('returns an ungrouped placeholder for null', () => {
    expect(getCategoryLabel(null)).toBe('دسته‌بندی نشده');
    expect(getCategoryLabel(undefined)).toBe('دسته‌بندی نشده');
  });
});

describe('getCategoryLabelFromKey', () => {
  it('delegates to getCategoryLabel', () => {
    expect(getCategoryLabelFromKey('iron')).toBe(getCategoryLabel('iron'));
  });
});

describe('CATEGORY_GROUPS', () => {
  it('contains a sane set of known keys across groups', () => {
    const groups = new Set(Object.values(CATEGORY_GROUPS).map((c) => c.group));
    for (const g of ['Cooking', 'Cooling', 'Washing', 'Small', 'Parts']) {
      expect(groups).toContain(g);
    }
  });

  it('provides a non-empty label for every entry', () => {
    for (const info of Object.values(CATEGORY_GROUPS)) {
      expect(info.label.length).toBeGreaterThan(0);
    }
  });
});