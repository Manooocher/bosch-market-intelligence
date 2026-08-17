import type { Seller } from '../../api/types';
import { formatPrice } from '../../utils/format';
import { Badge } from '../ui/Badge';
import { Star, CheckCircle2, XCircle, Megaphone, AlertTriangle } from 'lucide-react';

interface SellerRowProps {
  seller: Seller;
  rank: number;
  isCheapest: boolean;
}

/** Render a seller score (0-5) as filled/empty stars. */
function ScoreStars({ score }: { score: number | null }) {
  if (score == null) return <span className="text-slate-400">—</span>;
  const full = Math.round(score);
  return (
    <span className="inline-flex items-center gap-0.5" dir="ltr" title={`${score} از ۵`}>
      {Array.from({ length: 5 }).map((_, i) => (
        <Star
          key={i}
          className={`w-3.5 h-3.5 ${i < full ? 'text-amber-400 fill-amber-400' : 'text-slate-200'}`}
        />
      ))}
    </span>
  );
}

export function SellerRow({ seller, rank, isCheapest }: SellerRowProps) {
  // Outlier rows are greyed out and never marked cheapest.
  const isOutlier = seller.is_outlier === true;
  const rowClass = isOutlier
    ? 'bg-slate-50 opacity-60'
    : isCheapest
      ? 'bg-emerald-50/50'
      : '';

  return (
    <tr className={`border-b border-slate-100 ${rowClass}`}>
      <td className="px-4 py-3">
        <div className={`flex items-center justify-center w-7 h-7 rounded-full text-sm font-semibold ${
          isCheapest && !isOutlier ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-600'
        }`}>
          {rank}
        </div>
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="font-medium text-slate-800">{seller.seller_name ?? '—'}</span>
          {!isOutlier && isCheapest && <Badge variant="success">ارزان‌ترین</Badge>}
          {isOutlier && (
            <Badge variant="danger">
              <AlertTriangle className="w-3 h-3" /> قیمت نامعتبر
            </Badge>
          )}
          {!isOutlier && seller.is_advertisement && (
            <Badge variant="warning">
              <Megaphone className="w-3 h-3" /> تبلیغ
            </Badge>
          )}
        </div>
        {isOutlier && seller.outlier_reason && (
          <div className="text-xs text-slate-400 mt-0.5" title={seller.outlier_reason}>
            {seller.outlier_reason}
          </div>
        )}
      </td>
      <td className="px-4 py-3 text-sm text-slate-600">{seller.shop_city ?? '—'}</td>
      <td className="px-4 py-3 text-sm text-slate-700 font-medium" dir="ltr">
        {formatPrice(seller.price_rial)}
      </td>
      <td className="px-4 py-3">
        <ScoreStars score={seller.shop_score} />
      </td>
      <td className="px-4 py-3">
        {seller.is_outlier ? (
          <span className="inline-flex items-center gap-1 text-slate-400 text-sm">
            <XCircle className="w-4 h-4" /> ناموجود
          </span>
        ) : seller.is_in_stock ? (
          <span className="inline-flex items-center gap-1 text-emerald-600 text-sm">
            <CheckCircle2 className="w-4 h-4" /> موجود
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 text-red-500 text-sm">
            <XCircle className="w-4 h-4" /> ناموجود
          </span>
        )}
      </td>
    </tr>
  );
}