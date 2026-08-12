import { apiClient } from './client';
import { RawMarginsResponse, Margin } from './types';
import { mapMargin } from './mappers';

export const marginsApi = {
  getList: async (): Promise<Margin[]> => {
    const res = await apiClient.get<RawMarginsResponse>('/api/margins');
    return res.data.margins.map(mapMargin);
  },
};
