import { useQuery } from '@tanstack/react-query';
import { marketApi } from '../../api/market';
import { formatPrice } from '../../utils/format';
import { Clock, DollarSign } from 'lucide-react';

export function Header() {
  const { data: rate, isLoading } = useQuery({
    queryKey: ['exchange-rate'],
    queryFn: () => marketApi.getExchangeRate(),
    staleTime: 60 * 60 * 1000,
    gcTime: 4 * 60 * 60 * 1000,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  });

  return (
    <header className="bg-white border-b border-slate-200 px-6 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-6">
          {isLoading ? (
            <div className="h-8 w-48 bg-slate-200 rounded animate-pulse" />
          ) : rate ? (
            <div className="flex items-center gap-2 text-sm">
              <DollarSign className="w-4 h-4 text-emerald-600" />
              <span className="text-slate-600">نرخ دلار:</span>
              <span className="font-semibold text-slate-800">
                {formatPrice(rate.rate)} ریال
              </span>
            </div>
          ) : null}
        </div>
        <div className="flex items-center gap-2 text-sm text-slate-500">
          <Clock className="w-4 h-4" />
          <span>آپدیت هر ۴ روز</span>
        </div>
      </div>
    </header>
  );
}