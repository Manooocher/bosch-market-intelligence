import { useQuery } from '@tanstack/react-query';
import { shipmentsApi } from '../api/shipments';

const STALE_TIME = 60 * 1000;
const CACHE_TIME = 5 * 60 * 1000;

export function useShipments() {
  return useQuery({
    queryKey: ['shipments'],
    queryFn: () => shipmentsApi.list(),
    staleTime: STALE_TIME,
    gcTime: CACHE_TIME,
  });
}

export function useShipment(id: number | null) {
  return useQuery({
    queryKey: ['shipment', id],
    queryFn: () => shipmentsApi.get(id as number),
    staleTime: STALE_TIME,
    gcTime: CACHE_TIME,
    enabled: id != null && id > 0,
  });
}