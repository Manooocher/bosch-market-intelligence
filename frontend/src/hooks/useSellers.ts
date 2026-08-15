import { useQuery } from '@tanstack/react-query';
import { productsApi } from '../api/products';
import type { Seller } from '../api/types';

const STALE_TIME = 60 * 60 * 1000;
const CACHE_TIME = 4 * 60 * 60 * 1000;

export function useSellers(torobId: string) {
  return useQuery<Seller[]>({
    queryKey: ['product-sellers', torobId],
    queryFn: () => productsApi.getSellers(torobId),
    staleTime: STALE_TIME,
    gcTime: CACHE_TIME,
    enabled: !!torobId,
  });
}