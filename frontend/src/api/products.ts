import { apiClient } from './client';
import {
  RawProductsResponse,
  RawProductDetail,
  RawSellersResponse,
  RawMarginsResponse,
  RawMargin,
  Paginated,
  ProductListItem,
  ProductDetail,
  Seller,
  Margin,
} from './types';
import { mapPagination, mapProductItem, mapProductDetail, mapSeller, mapMargin } from './mappers';

export interface ProductListParams {
  sort_by?: string;
  sort_dir?: 'asc' | 'desc';
  page?: number;
  per_page?: number;
}

export const productsApi = {
  /**
   * List products (server-side paginated). The adapter merges margin data from
   * /api/margins (matched by SKU) into each row for the UI.
   */
  getList: async (params: ProductListParams = {}): Promise<Paginated<ProductListItem>> => {
    const [prodRes, marginRes] = await Promise.all([
      apiClient.get<RawProductsResponse>('/api/products', {
        params: {
          page: params.page ?? 1,
          per_page: params.per_page ?? 20,
          ...(params.sort_by ? { sort_by: params.sort_by } : {}),
          ...(params.sort_dir ? { sort_dir: params.sort_dir } : {}),
        },
      }),
      // Margins are secondary; if they fail we still render the product list.
      apiClient.get<RawMarginsResponse>('/api/margins').catch(() => null),
    ]);

    const bySku = new Map<string, RawMargin>();
    (marginRes?.data?.margins ?? []).forEach((m) => {
      if (m.sku) bySku.set(m.sku, m);
    });
    const items = prodRes.data.products.map((p) =>
      mapProductItem(p, p.sku ? bySku.get(p.sku) ?? null : null),
    );
    return mapPagination(prodRes.data.pagination, items);
  },

  getDetail: async (torobId: string): Promise<ProductDetail> => {
    const [d, s] = await Promise.all([
      apiClient.get<RawProductDetail>(`/api/products/${torobId}`),
      apiClient.get<RawSellersResponse>(`/api/products/${torobId}/sellers`),
    ]);
    return mapProductDetail(d.data, s.data.sellers);
  },

  getSellers: async (torobId: string): Promise<Seller[]> => {
    const res = await apiClient.get<RawSellersResponse>(`/api/products/${torobId}/sellers`);
    return res.data.sellers.map(mapSeller);
  },

  getMargins: async (): Promise<Margin[]> => {
    const res = await apiClient.get<RawMarginsResponse>('/api/margins');
    return res.data.margins.map(mapMargin);
  },
};
