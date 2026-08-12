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
import { buildTorobUrl, inferCategory } from '../utils/categories';

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
 * Fields `category` and `torob_url` are DERIVED client-side because the backend
 * does not provide them. Margin fields are merged by SKU when available.
 */
export function mapProductItem(raw: RawProductItem, margin: RawMargin | null): ProductListItem {
  return {
    ...raw,
    category: inferCategory(raw.sku, raw.title),
    torob_url: buildTorobUrl(raw.torob_product_id),
    freshness_hours: freshnessHours(raw.last_fetched_at),
    margin_vs_min_pct: margin?.margin_vs_min_pct ?? null,
    margin_vs_min_rial: margin?.margin_vs_min_toman ?? null,
    is_profitable: margin?.is_profitable ?? null,
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
  };
}

/** Combine raw detail + sellers into a full UI detail object. */
export function mapProductDetail(raw: RawProductDetail, sellersRaw: RawSeller[]): ProductDetail {
  return {
    torob_product_id: raw.torob_product_id,
    sku: raw.sku,
    title: raw.title,
    category: inferCategory(raw.sku, raw.title),
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
