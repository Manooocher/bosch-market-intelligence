import { apiClient } from './client';
import {
  RawProductsResponse,
  RawProductDetail,
  RawSellersResponse,
  Paginated,
  ProductListItem,
  ProductDetail,
  Seller,
} from './types';
import { mapPagination, mapProductItem, mapProductDetail, mapSeller } from './mappers';

export interface ProductListParams {
  sort_by?: string;
  sort_dir?: 'asc' | 'desc';
  page?: number;
  per_page?: number;
  search?: string;
  category?: string;
}

export const productsApi = {
  /**
   * List products (server-side paginated). Margin fields, category, and torob_url
   * are now returned directly by the backend — no more client-side inference or
   * secondary margin fetch.
   */
  getList: async (params: ProductListParams = {}): Promise<Paginated<ProductListItem>> => {
    const res = await apiClient.get<RawProductsResponse>('/api/products', {
      params: {
        page: params.page ?? 1,
        per_page: params.per_page ?? 50,
        ...(params.sort_by ? { sort_by: params.sort_by } : {}),
        ...(params.sort_dir ? { sort_dir: params.sort_dir } : {}),
        ...(params.search ? { search: params.search } : {}),
        ...(params.category ? { category: params.category } : {}),
      },
    });

    const items = res.data.products.map(mapProductItem);
    return mapPagination(res.data.pagination, items);
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
};