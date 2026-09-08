import { Menu, Clock, DollarSign } from 'lucide-react';
import { useExchangeRate } from '../../hooks/useMarket';
import { formatPrice } from '../../utils/format';

interface HeaderProps {
  /** Opens the mobile sidebar drawer (hamburger menu). */
  onMenuClick: () => void;
}

/** Top bar — hamburger menu on mobile plus the exchange-rate chip. */
export function Header({ onMenuClick }: HeaderProps) {
  const { data: rate, isLoading } = useExchangeRate();

  return (
    <header className="bg-white border-b border-slate-200 px-4 py-4 md:px-6">
      <div className="flex items-center justify-between">
        {/* Exchange rate chip — FIRST flex child → RIGHT in RTL. */}
        <div className="flex items-center gap-4">
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
                {rate.source && (
                  <span className="text-xs text-slate-400">
                    ({rate.source === 'tabdeal-live' ? 'لحظه‌ای' : rate.source === 'tabdeal-cached' ? 'کش' : 'آفلاین'})
                  </span>
                )}
              </div>
            ) : null}
          </div>
        </div>

        {/* Hamburger menu — LAST flex child → LEFT in RTL (mobile only). */}
        <button
          onClick={onMenuClick}
          className="md:hidden p-2 -ml-2 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors"
          aria-label="باز کردن منو"
        >
          <Menu className="w-6 h-6" />
        </button>

        <div className="flex items-center gap-2 text-sm text-slate-500">
          <Clock className="w-4 h-4" />
          <span>آپدیت هر ۴ روز</span>
        </div>
      </div>
    </header>
  );
}