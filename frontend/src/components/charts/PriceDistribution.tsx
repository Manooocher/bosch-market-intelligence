import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  Cell,
  CartesianGrid,
} from 'recharts';
import type { Seller } from '../../api/types';
import { formatPrice } from '../../utils/format';

interface PriceDistributionProps {
  sellers: Seller[];
  /** Nabkade price in Rial (for the reference line). Null hides the line. */
  nabkadePriceRial: number | null;
  /** Optional height for the chart container. */
  height?: number;
}

interface ChartDatum {
  name: string;
  price: number;
  inStock: boolean;
}

function truncateName(name: string, max = 15): string {
  return name.length > max ? `${name.slice(0, max)}…` : name;
}

/** Horizontal-orientation-independent bar chart of seller prices. */
export function PriceDistribution({
  sellers,
  nabkadePriceRial,
  height = 320,
}: PriceDistributionProps) {
  const data: ChartDatum[] = sellers.map((s) => ({
    name: truncateName(s.seller_name ?? 'نامشخص'),
    price: s.price_rial,
    inStock: s.is_in_stock,
  }));

  if (data.length === 0) {
    return (
      <div className="py-12 text-center text-sm text-slate-400">
        اطلاعاتی برای نمودار قیمت وجود ندارد.
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 10, right: 10, left: 10, bottom: 40 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis
          dataKey="name"
          tick={{ fontSize: 11, fill: '#64748b' }}
          interval={0}
          angle={-20}
          textAnchor="end"
          height={60}
        />
        <YAxis
          tickFormatter={(v: number) => formatPrice(v)}
          tick={{ fontSize: 11, fill: '#64748b' }}
          width={90}
        />
        <Tooltip
          formatter={(value) => [`${formatPrice(Number(value))} ریال`, 'قیمت']}
          labelStyle={{ color: '#1e293b', fontWeight: 600 }}
          contentStyle={{
            direction: 'rtl',
            fontSize: 13,
            borderRadius: 8,
            border: '1px solid #e2e8f0',
          }}
        />
        {nabkadePriceRial != null && (
          <ReferenceLine
            y={nabkadePriceRial}
            stroke="#6366f1"
            strokeDasharray="5 5"
            label={{
              value: 'قیمت نبکاده',
              position: 'top',
              fill: '#6366f1',
              fontSize: 11,
            }}
          />
        )}
        <Bar dataKey="price" radius={[4, 4, 0, 0]}>
          {data.map((d, i) => (
            <Cell key={i} fill={d.inStock ? '#10b981' : '#94a3b8'} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}