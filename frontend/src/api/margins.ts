import { apiClient } from './client';
import { RawMarginsResponse, Margin, Paginated } from './types';
import { mapMargin, mapPagination } from './mappers';

export interface MarginsParams {
  sort_by?: string;
  sort_dir?: 'asc' | 'desc';
  search?: string;
  category?: string;
  per_page?: number; // optional, only for backward compat
}

export const marginsApi = {
  /**
   * By default returns ALL margins in one response (dashboard filters
   * client-side). pass per_page only for legacy server-side pagination.
   */
  getList: async (params: MarginsParams = {}): Promise<Paginated<Margin>> => {
    const res = await apiClient.get<RawMarginsResponse>('/api/margins', {
      params: {
        ...(params.sort_by ? { sort_by: params.sort_by } : {}),
        ...(params.sort_dir ? { sort_dir: params.sort_dir } : {}),
        ...(params.search ? { search: params.search } : {}),
        ...(params.category ? { category: params.category } : {}),
        ...(params.per_page ? { per_page: params.per_page } : {}),
      },
    });
    const items = res.data.margins.map(mapMargin);
    return mapPagination(res.data.pagination, items);
  },
};