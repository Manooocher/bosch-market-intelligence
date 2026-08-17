import {
  RawProductItem,
  RawMargin,
  RawSeller,
  RawProductDetail,
  Paginated,
  ProductListItem,
  Seller,
  ProductDetail,
  Margin,
  RawPagination,
} from './types';

/** Hours between a timestamp and now (null if unparseable). */
export function freshnessHours(iso: string | null): number | null {
  if (!iso) return null;
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return null;
  return Math.max(0, Math.round((Date.now() - t) / 3600000));
}

/** Map backend pagination to the normalized Paginated<T> shape. */
export function mapPagination<T>(pagination: RawPagination, items: T[]): Paginated<T> {
  return {
    items,
    total: pagination.total,
    page: pagination.page,
    pages: Math.max(1, pagination.total_pages),
  };
}

/**
 * Transform a raw product list item into the UI shape.
 * category, torob_url, and margin fields now come directly from the backend.
 */
export function mapProductItem(raw: RawProductItem): ProductListItem {
  return {
    ...raw,
    category: raw.category ?? 'دسته‌بندی نشده',
    torob_url: raw.torob_url ?? '',
    freshness_hours: freshnessHours(raw.last_fetched_at),
    margin_vs_min_pct: raw.margin_vs_min_pct,
    margin_vs_min_rial: raw.margin_vs_min_rial,
    is_profitable: raw.margin_vs_min_rial != null && raw.margin_vs_min_rial > 0,
  };
}

/** Transform a raw seller into the UI shape (is_promoted -> is_advertisement). */
export function mapSeller(raw: RawSeller): Seller {
  return {
    seller_id: raw.seller_id,
    seller_name: raw.seller_name,
    price_rial: raw.price_rial,
    shop_city: raw.seller_city,
    shop_score: raw.seller_score,
    is_in_stock: raw.is_in_stock,
    is_advertisement: raw.is_promoted,
    seller_page_url: raw.seller_page_url,
    is_outlier: raw.is_outlier,
    outlier_reason: raw.outlier_reason,
  };
}

/** Combine raw detail + sellers into a full UI detail object. */
export function mapProductDetail(raw: RawProductDetail, sellersRaw: RawSeller[]): ProductDetail {
  return {
    ...mapProductItem(raw),
    market_stats: {
      ...raw.market_stats,
      freshness_hours: freshnessHours(raw.market_stats.fetched_at),
    },
    price_distribution: raw.price_distribution,
    sellers: sellersRaw.map(mapSeller),
  };
}

/** Pass-through margin (already in the shape components want). */
export function mapMargin(raw: RawMargin): Margin {
  return raw;
}