import { useQuery } from '@tanstack/react-query';
import { productsApi } from '../api/products';

const STALE_TIME = 60 * 60 * 1000;
const CACHE_TIME = 4 * 60 * 60 * 1000;

export function useProductDetail(torobId: string) {
  return useQuery({
    queryKey: ['product', torobId],
    queryFn: () => productsApi.getDetail(torobId),
    staleTime: STALE_TIME,
    gcTime: CACHE_TIME,
    enabled: !!torobId,
  });
}