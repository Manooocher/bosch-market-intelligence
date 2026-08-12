import { apiClient } from './client';
import { RawMarketOverview, RawHealth, MarketOverview, ExchangeRate } from './types';

export const marketApi = {
  getOverview: async (): Promise<MarketOverview> => {
    const { data } = await apiClient.get<RawMarketOverview>('/api/market/overview');
    return {
      total_products: data.total_products,
      products_with_sellers: data.products_with_sellers,
      avg_sellers_per_product: data.avg_sellers_per_product,
      avg_competition_score: data.avg_competition_score,
      usd_irt_rate: data.usd_irt_rate,
      // Backend exposes the exchange-rate values inside /overview (no
      // /api/exchange-rate endpoint), so we derive a freshness timestamp here.
      last_updated_at: data.last_monitor_run?.finished_at ?? data.usd_irt_updated_at,
      last_monitor_run: data.last_monitor_run,
    };
  },

  /** Derived from /api/market/overview because no dedicated /api/exchange-rate exists. */
  getExchangeRate: async (): Promise<ExchangeRate> => {
    const { data } = await apiClient.get<RawMarketOverview>('/api/market/overview');
    return {
      rate: data.usd_irt_rate,
      source: data.usd_irt_source,
      fetched_at: data.usd_irt_updated_at,
    };
  },

  getHealth: async (): Promise<RawHealth> => {
    const res = await apiClient.get<RawHealth>('/api/system/health');
    return res.data;
  },
};
