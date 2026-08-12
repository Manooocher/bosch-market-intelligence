import { useQuery } from '@tanstack/react-query';
import { marketApi } from '../api/market';

const STALE_TIME = 60 * 60 * 1000;
const CACHE_TIME = 4 * 60 * 60 * 1000;

export function useMarketOverview() {
  return useQuery({
    queryKey: ['market-overview'],
    queryFn: () => marketApi.getOverview(),
    staleTime: STALE_TIME,
    gcTime: CACHE_TIME,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  });
}

export function useExchangeRate() {
  return useQuery({
    queryKey: ['exchange-rate'],
    queryFn: () => marketApi.getExchangeRate(),
    staleTime: STALE_TIME,
    gcTime: CACHE_TIME,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  });
}
