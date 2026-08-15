import { apiClient } from './client';
import { RawMarginsResponse, Margin, Paginated } from './types';
import { mapMargin, mapPagination } from './mappers';

export interface MarginsParams {
  page?: number;
  per_page?: number;
  sort_by?: string;
  sort_dir?: 'asc' | 'desc';
}

export const marginsApi = {
  getList: async (params: MarginsParams = {}): Promise<Paginated<Margin>> => {
    const res = await apiClient.get<RawMarginsResponse>('/api/margins', {
      params: {
        page: params.page ?? 1,
        per_page: params.per_page ?? 50,
        ...(params.sort_by ? { sort_by: params.sort_by } : {}),
        ...(params.sort_dir ? { sort_dir: params.sort_dir } : {}),
      },
    });
    const items = res.data.margins.map(mapMargin);
    return mapPagination(res.data.pagination, items);
  },
};