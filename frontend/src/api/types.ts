// ═══════════════════════════════════════════════════════════════════════
// RAW BACKEND CONTRACTS (source of truth — verified live from the FastAPI)
// These match the actual JSON returned by the 6 real endpoints.
// ═══════════════════════════════════════════════════════════════════════

export interface RawPagination {
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
}

export interface RawProductItem {
  nabkade_product_id: string;
  torob_product_id: string;
  sku: string | null;
  title: string | null;
  last_fetched_at: string | null;
  seller_count: number;
  min_price_rial: number;
  max_price_rial: number;
  avg_price_rial: number;
  median_price_rial: number;
  min_price_usd: number;
  max_price_usd: number;
  avg_price_usd: number;
  median_price_usd: number;
  competition_score: number;
  updated_at: string | null;
}

export interface RawProductsResponse {
  pagination: RawPagination;
  products: RawProductItem[];
}

export interface RawMarketStats {
  seller_count: number;
  min_price_rial: number;
  max_price_rial: number;
  avg_price_rial: number;
  median_price_rial: number;
  competition_score: number;
  fetched_at: string | null;
  freshness: string; // 'fresh' | 'acceptable' | 'stale' | 'unknown'
}

export interface RawPriceBucket {
  range: string;
  count: number;
}

export interface RawProductDetail {
  torob_product_id: string;
  sku: string | null;
  title: string | null;
  market_stats: RawMarketStats;
  price_distribution: { buckets: RawPriceBucket[] };
}

export interface RawSeller {
  seller_id: string;
  seller_name: string | null;
  price_rial: number;
  seller_score: number | null;
  seller_city: string | null;
  is_in_stock: boolean;
  is_promoted: boolean;
}

export interface RawSellersResponse {
  torob_product_id: string;
  sellers: RawSeller[];
}

export interface RawMargin {
  sku: string | null;
  title: string | null;
  nabkade_price_toman: number;
  market_min_price_toman: number;
  margin_vs_min_toman: number;
  margin_vs_min_pct: number;
  is_profitable: boolean;
}

export interface RawMarginsResponse {
  margins: RawMargin[];
}

export interface RawLastMonitorRun {
  started_at: string | null;
  finished_at: string | null;
  products_succeeded: number;
  products_failed: number;
  status: string;
}

export interface RawMarketOverview {
  total_products: number;
  products_with_sellers: number;
  avg_sellers_per_product: number;
  avg_competition_score: number;
  usd_irt_rate: number;
  usd_irt_source: string;
  usd_irt_updated_at: string;
  last_monitor_run: RawLastMonitorRun | null;
}

export interface RawHealth {
  status: string;
  database: { connected: boolean };
  monitor: {
    last_run_finished_at?: string | null;
    last_run_status?: string | null;
    seconds_since_last_run?: number | null;
  };
  timestamp: string;
}

// ═══════════════════════════════════════════════════════════════════════
// MAPPED / UI CONTRACTS (what components consume — produced by the adapter)
// Fields the backend does NOT provide are derived here (see mappers.ts).
// ═══════════════════════════════════════════════════════════════════════

export interface ProductListItem extends RawProductItem {
  // Derived by the adapter (not present in raw backend payload)
  torob_url: string;
  category: string; // inferred from SKU/title — backend has no category field
  freshness_hours: number | null;
  margin_vs_min_pct: number | null;
  margin_vs_min_rial: number | null;
  is_profitable: boolean | null;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  pages: number;
}

export interface Seller {
  seller_id: string;
  seller_name: string | null;
  price_rial: number;
  shop_city: string | null; // mapped from raw.seller_city
  shop_score: number | null; // mapped from raw.seller_score
  is_in_stock: boolean;
  is_advertisement: boolean; // mapped from raw.is_promoted
}

export interface ProductDetail {
  torob_product_id: string;
  sku: string | null;
  title: string | null;
  category: string; // inferred
  market_stats: RawMarketStats & { freshness_hours: number | null };
  price_distribution: { buckets: RawPriceBucket[] };
  sellers: Seller[];
}

export interface Margin {
  sku: string | null;
  title: string | null;
  nabkade_price_toman: number;
  market_min_price_toman: number;
  margin_vs_min_toman: number;
  margin_vs_min_pct: number;
  is_profitable: boolean;
}

export interface MarketOverview {
  total_products: number;
  products_with_sellers: number;
  avg_sellers_per_product: number;
  avg_competition_score: number;
  usd_irt_rate: number;
  last_updated_at: string | null; // from last_monitor_run.finished_at
  last_monitor_run: RawLastMonitorRun | null;
}

export interface ExchangeRate {
  rate: number;
  source: string;
  fetched_at: string;
}

// FastAPI standard error shape: {"detail": "message"}
export interface ApiError {
  detail: string;
}
