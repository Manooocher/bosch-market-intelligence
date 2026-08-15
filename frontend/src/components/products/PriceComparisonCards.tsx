import type { ProductDetail } from '../../api/types';
import { formatPrice, formatNumber } from '../../utils/format';
import { Badge } from '../ui/Badge';

interface PriceComparisonCardsProps {
  product: ProductDetail;
}

interface CardData {
  label: string;
  value: string;
  sub: React.ReactNode;
}

/** Compute the nabkade price (Toman) from margin vs min + market min (Toman). */
function deriveNabkadeToman(product: ProductDetail): number | null {
  const minRial = product.market_stats?.min_price_rial ?? 0;
  const marginMin = product.margin_vs_min_rial;
  if (marginMin == null || minRial <= 0) return null;
  // margin_vs_min_rial is in Toman; market min in Rial -> toman = rial / 10
  return marginMin + Math.floor(minRial / 10);
}

function marginBadge(pct: number | null): React.ReactNode {
  if (pct == null) return <Badge variant="neutral">—</Badge>;
  const sign = pct > 0 ? '+' : '';
  const variant = pct > 10 ? 'success' : pct >= 0 ? 'warning' : 'danger';
  return (
    <Badge variant={variant}>
      {sign}
      {pct.toFixed(1)}٪
    </Badge>
  );
}

export function PriceComparisonCards({ product }: PriceComparisonCardsProps) {
  const stats = product.market_stats;
  const nabkadeToman = deriveNabkadeToman(product);
  const marginMin = product.margin_vs_min_pct;
  const marginMedian = product.margin_vs_median_pct;

  const cards: CardData[] = [
    {
      label: 'قیمت نبکاده',
      value: nabkadeToman != null ? formatNumber(nabkadeToman) : '—',
      sub: (
        <span className="text-xs text-slate-500">
          {product.is_profitable != null && (
            <>
              وضعیت: {product.is_profitable ? 'سودآور' : 'زیان'} ·{' '}
            </>
          )}
          حاشیه: {marginBadge(marginMin)}
        </span>
      ),
    },
    {
      label: 'کمترین بازار',
      value: formatPrice(stats?.min_price_rial ?? null),
      sub: <span className="text-xs text-slate-500">حاشیه: {marginBadge(marginMin)}</span>,
    },
    {
      label: 'میانه بازار',
      value: formatPrice(stats?.median_price_rial ?? null),
      sub: <span className="text-xs text-slate-500">حاشیه: {marginBadge(marginMedian)}</span>,
    },
    {
      label: 'بیشترین بازار',
      value: formatPrice(stats?.max_price_rial ?? null),
      sub: <span className="text-xs text-slate-500">—</span>,
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {cards.map((card) => (
        <div
          key={card.label}
          className="bg-white rounded-xl border border-slate-200 shadow-sm p-5"
        >
          <p className="text-sm text-slate-500 mb-1">{card.label}</p>
          <p className="text-2xl font-bold text-slate-800" dir="ltr">
            {card.value}
          </p>
          <div className="mt-2">{card.sub}</div>
        </div>
      ))}
    </div>
  );
}