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
      <div className="flex items-center justify-between gap-3">
        {/* ── FIRST child → RIGHT in RTL — hamburger, mobile only ── */}
        <button
          onClick={onMenuClick}
          className="md:hidden p-2 -ml-2 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
          aria-label="باز کردن منو"
        >
          <Menu className="w-6 h-6" />
        </button>

        {/* ── LAST child → LEFT in RTL ──────────────────────────────── */}
        <div className="flex flex-col gap-1">
          {/* Exchange rate (always visible) */}
          <div className="flex items-center gap-2 text-sm">
            <DollarSign className="w-4 h-4 text-emerald-600 shrink-0" />
            <span className="text-slate-600">نرخ دلار:</span>
            {isLoading ? (
              <span className="h-4 w-16 bg-slate-200 rounded animate-pulse" />
            ) : rate ? (
              <span className="font-semibold text-slate-800" dir="ltr">
                {formatPrice(rate.rate)}
                <span className="text-xs text-slate-500 ml-1">ریال</span>
              </span>
            ) : (
              <span className="text-slate-400">—</span>
            )}
            {rate?.source && (
              <span className="text-xs text-slate-400 hidden sm:inline">
                ({rate.source === 'tabdeal-live' ? 'لحظه‌ای' : rate.source === 'tabdeal-cached' ? 'کش' : 'آفلاین'})
              </span>
            )}
          </div>

          {/* Update info — only visible on desktop */}
          <div className="hidden md:flex items-center gap-2 text-xs text-slate-500">
            <Clock className="w-3.5 h-3.5" />
            <span>آپدیت هر ۴ روز</span>
          </div>
        </div>
      </div>
    </header>
  );
}