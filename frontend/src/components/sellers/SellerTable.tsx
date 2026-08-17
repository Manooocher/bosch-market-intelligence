import type { Seller } from '../../api/types';
import { SellerRow } from './SellerRow';
import { EmptyState } from '../ui/EmptyState';

interface SellerTableProps {
  sellers: Seller[];
  isLoading?: boolean;
}

/** Seller table sorted by price ascending; cheapest seller highlighted. */
export function SellerTable({ sellers, isLoading = false }: SellerTableProps) {
  if (isLoading) {
    return (
      <div className="space-y-2 p-4">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-10 bg-slate-100 rounded animate-pulse" />
        ))}
      </div>
    );
  }

  if (sellers.length === 0) {
    return (
      <EmptyState
        title="فروشنده‌ای یافت نشد"
        description="برای این محصول هنوز اطلاعات فروشنده‌ای ثبت نشده است."
      />
    );
  }

  // Cheapest = lowest price among in-stock, non-outlier sellers.
  const sorted = [...sellers].sort((a, b) => a.price_rial - b.price_rial);
  const cheapestId =
    sorted.find((s) => s.is_in_stock && !s.is_outlier)?.seller_id ??
    sorted.find((s) => !s.is_outlier)?.seller_id ??
    null;

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b border-slate-200 bg-slate-50">
            <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500">رتبه</th>
            <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500">فروشنده</th>
            <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500">شهر</th>
            <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500">قیمت (ریال)</th>
            <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500">امتیاز</th>
            <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500">موجودی</th>
            <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500">لینک</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((seller, i) => (
            <SellerRow
              key={seller.seller_id}
              seller={seller}
              rank={i + 1}
              isCheapest={seller.seller_id === cheapestId}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}