import { useQuery } from '@tanstack/react-query';
import { marginsApi, type MarginsParams } from '../api/margins';

const STALE_TIME = 60 * 60 * 1000;
const CACHE_TIME = 4 * 60 * 60 * 1000;

export function useMargins(params: MarginsParams = {}) {
  return useQuery({
    queryKey: ['margins', JSON.stringify(params)],
    queryFn: () => marginsApi.getList(params),
    staleTime: STALE_TIME,
    gcTime: CACHE_TIME,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  });
}