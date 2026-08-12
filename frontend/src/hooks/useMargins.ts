import { useQuery } from '@tanstack/react-query';
import { marginsApi } from '../api/margins';

const STALE_TIME = 60 * 60 * 1000;
const CACHE_TIME = 4 * 60 * 60 * 1000;

export function useMargins() {
  return useQuery({
    queryKey: ['margins'],
    queryFn: () => marginsApi.getList(),
    staleTime: STALE_TIME,
    gcTime: CACHE_TIME,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  });
}
