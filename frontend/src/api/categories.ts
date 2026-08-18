import { apiClient } from './client';

export interface CategoryCount {
  category: string;
  count: number;
}

export const categoriesApi = {
  getList: async (): Promise<CategoryCount[]> => {
    const res = await apiClient.get<{ categories: CategoryCount[] }>('/api/products/categories');
    return res.data.categories;
  },
};