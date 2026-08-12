import { useQuery } from '@tanstack/react-query';
import { productsApi, ProductListParams } from '../api/products';

// Data updates every few days, so cache aggressively.
const STALE_TIME = 60 * 60 * 1000; // 1 hour
const CACHE_TIME = 4 * 60 * 60 * 1000; // 4 hours

export function useProducts(params: ProductListParams = {}) {
  return useQuery({
    queryKey: ['products', JSON.stringify(params)],
    queryFn: () => productsApi.getList(params),
    staleTime: STALE_TIME,
    gcTime: CACHE_TIME,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  });
}

export function useProductDetail(torobId: string) {
  return useQuery({
    queryKey: ['product', torobId],
    queryFn: () => productsApi.getDetail(torobId),
    staleTime: STALE_TIME,
    gcTime: CACHE_TIME,
    enabled: !!torobId,
  });
}

export function useProductSellers(torobId: string) {
  return useQuery({
    queryKey: ['product-sellers', torobId],
    queryFn: () => productsApi.getSellers(torobId),
    staleTime: STALE_TIME,
    gcTime: CACHE_TIME,
    enabled: !!torobId,
  });
}
