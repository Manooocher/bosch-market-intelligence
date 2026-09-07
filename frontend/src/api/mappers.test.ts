import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import {
  mapPagination,
  mapProductItem,
  mapSeller,
  mapProductDetail,
  mapMargin,
} from './mappers';
import type {
  RawProductItem,
  RawProductDetail,
  RawSeller,
  RawMargin,
  RawPagination,
} from './types';

const SAMPLE_TIME = '2026-09-08T12:00:00Z';

function rawProduct(overrides: Partial<RawProductItem> = {}): RawProductItem {
  return {
    nabkade_product_id: '3877',
    torob_product_id: 'abc',
    sku: 'MFQ36460',
    title: 'همزن برقی بوش',
    category: null,
    torob_url: null,
    last_fetched_at: '2026-09-08T06:00:00Z',
    seller_count: 30,
    min_price_rial: 1000,
    max_price_rial: 32430041,
    avg_price_rial: 16688198,
    median_price_rial: 17105000,
    min_price_usd: 5,
    max_price_usd: 174634,
    avg_price_usd: 89865,
    median_price_usd: 92109,
    competition_score: 67,
    margin_vs_min_pct: 100,
    margin_vs_min_rial: 15499000,
    margin_vs_median_pct: -10.4,
    margin_vs_median_rial: -1605000,
    updated_at: '2026-09-08T12:00:00Z',
    ...overrides,
  };
}

function rawSeller(overrides: Partial<RawSeller> = {}): RawSeller {
  return {
    seller_id: 's1',
    seller_name: 'فروشگاه آ',
    price_rial: 15000000,
    seller_score: 5,
    seller_city: 'تهران',
    is_in_stock: true,
    is_promoted: true,
    seller_page_url: 'https://torob.com/seller/s1',
    is_outlier: false,
    outlier_reason: null,
    ...overrides,
  };
}

describe('mapPagination', () => {
  it('maps pagination and forces at least 1 page', () => {
    const pagination: RawPagination = { page: 2, per_page: 10, total: 25, total_pages: 3 };
    const out = mapPagination(pagination, ['a', 'b'] as unknown as string[]);
    expect(out.items).toHaveLength(2);
    expect(out.total).toBe(25);
    expect(out.page).toBe(2);
    expect(out.pages).toBe(3);
  });

  it('clamps zero total_pages to 1', () => {
    const pagination: RawPagination = { page: 1, per_page: 10, total: 0, total_pages: 0 };
    const out = mapPagination(pagination, []);
    expect(out.pages).toBe(1);
  });
});

describe('mapProductItem', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-09-08T12:00:00Z'));
  });
  afterEach(() => vi.useRealTimers());

  it('preserves identity fields', () => {
    const mapped = mapProductItem(rawProduct());
    expect(mapped.torob_product_id).toBe('abc');
    expect(mapped.sku).toBe('MFQ36460');
    expect(mapped.title).toContain('بوش');
    expect(mapped.seller_count).toBe(30);
  });

  it('defaults a missing category to the ungrouped label', () => {
    const mapped = mapProductItem(rawProduct({ category: null }));
    expect(mapped.category).toBe('دسته‌بندی نشده');
  });

  it('keeps a provided category and normalizes the URL', () => {
    const mapped = mapProductItem(rawProduct({ category: 'Washing', torob_url: 'https://t/p' }));
    expect(mapped.category).toBe('Washing');
    expect(mapped.torob_url).toBe('https://t/p');
    expect(mapped.torob_url).not.toBe('');
  });

  it('computes freshness_hours from last_fetched_at', () => {
    const mapped = mapProductItem(rawProduct({ last_fetched_at: '2026-09-08T06:00:00Z' }));
    expect(mapped.freshness_hours).toBe(6);
  });

  it('marks a positive margin as profitable', () => {
    const mapped = mapProductItem(rawProduct({ margin_vs_min_rial: 1000 }));
    expect(mapped.is_profitable).toBe(true);
  });

  it('marks a negative margin as not profitable', () => {
    const mapped = mapProductItem(rawProduct({ margin_vs_min_rial: -50 }));
    expect(mapped.is_profitable).toBe(false);
  });

  it('treats a null margin as not profitable', () => {
    const mapped = mapProductItem(rawProduct({ margin_vs_min_rial: null }));
    expect(mapped.is_profitable).toBe(false);
  });
});

describe('mapSeller', () => {
  it('renames promoted to advertisement and maps city/score', () => {
    const seller = mapSeller(rawSeller());
    expect(seller.is_advertisement).toBe(true);
    expect(seller.shop_city).toBe('تهران');
    expect(seller.shop_score).toBe(5);
    expect(seller.seller_id).toBe('s1');
  });

  it('passes through outlier fields and nullable values', () => {
    const mapped = mapSeller(rawSeller({ is_outlier: true, outlier_reason: 'low', seller_city: null }));
    expect(mapped.is_outlier).toBe(true);
    expect(mapped.outlier_reason).toBe('low');
    expect(mapped.shop_city).toBeNull();
  });
});

describe('mapProductDetail', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(SAMPLE_TIME));
  });
  afterEach(() => vi.useRealTimers());

  it('combines product item, market stats, distribution, and mapped sellers', () => {
    const raw: RawProductDetail = {
      ...rawProduct(),
      market_stats: {
        seller_count: 30,
        min_price_rial: 1000,
        max_price_rial: 32430041,
        avg_price_rial: 16688198,
        median_price_rial: 17105000,
        competition_score: 67,
        fetched_at: '2026-09-08T06:00:00Z',
        freshness: 'fresh',
      },
      price_distribution: { buckets: [{ range: '1M-10M', count: 3 }] },
    };
    const detail = mapProductDetail(raw, [rawSeller()]);
    expect(detail.market_stats.freshness_hours).toBe(6);
    expect(detail.price_distribution.buckets[0].count).toBe(3);
    expect(detail.sellers).toHaveLength(1);
    expect(detail.sellers[0].is_advertisement).toBe(true);
  });

  it('handles no sellers as empty array', () => {
    const raw: RawProductDetail = {
      ...rawProduct(),
      market_stats: {
        seller_count: 0,
        min_price_rial: 0,
        max_price_rial: 0,
        avg_price_rial: 0,
        median_price_rial: 0,
        competition_score: 0,
        fetched_at: null,
        freshness: 'unknown',
      },
      price_distribution: { buckets: [] },
    };
    const detail = mapProductDetail(raw, []);
    expect(detail.sellers).toEqual([]);
    expect(detail.market_stats.freshness_hours).toBeNull();
  });
});

describe('mapMargin', () => {
  it('passes margins through unchanged', () => {
    const raw: RawMargin = {
      sku: 'MFQ',
      torob_product_id: 'abc',
      title: 'همزن',
      category: 'Washing',
      torob_url: 'https://t/p',
      nabkade_price_toman: 100000,
      market_min_price_toman: 90000,
      market_median_price_toman: 95000,
      margin_vs_min_toman: 10000,
      margin_vs_median_toman: 5000,
      margin_vs_min_pct: 10,
      margin_vs_median_pct: 5,
      is_profitable: true,
    };
    expect(mapMargin(raw)).toEqual(raw);
  });
});