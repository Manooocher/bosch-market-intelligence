import { useMarketOverview } from '../hooks/useMarket';
import { useProducts } from '../hooks/useProducts';
import { formatNumber, formatDate } from '../utils/format';
import { freshnessHours } from '../utils/date';
import { getFreshnessColor } from '../utils/colors';
import { ErrorState } from '../components/ui/ErrorState';
import { SkeletonCard } from '../components/ui/Loading';
import { Card } from '../components/ui/Card';
import { Package, TrendingUp, Users, Gauge, Clock } from 'lucide-react';
import { useMemo } from 'react';

const freshnessLabels: Array<[number, string]> = [
  [24, 'تازه'],
  [96, 'قابل قبول'],
];

function freshnessLabel(hours: number): string {
  for (const [threshold, label] of freshnessLabels) {
    if (hours < threshold) return label;
  }
  return 'قدیمی';
}

export function MarketOverviewPage() {
  const { data: overview, isLoading, error, refetch } = useMarketOverview();
  // Pull products to build the margin histogram (no dedicated margin endpoint in overview).
  const { data: productsData } = useProducts({ page: 1, per_page: 100 });

  const marginBuckets = useMemo(() => {
    const buckets: Record<string, number> = {};
    const defs: Array<[string, (p: number | null) => boolean]> = [
      ['منفی (صفر-)', (p) => p != null && p < 0],
      ['۰ تا ۱۰٪', (p) => p != null && p >= 0 && p <= 10],
      ['بیش از ۱۰٪', (p) => p != null && p > 10],
      ['بدون داده', (p) => p == null],
    ];
    defs.forEach(([label]) => (buckets[label] = 0));
    (productsData?.items ?? []).forEach((p) => {
      const hit = defs.find(([, fn]) => fn(p.margin_vs_min_pct));
      if (hit) buckets[hit[0]] += 1;
    });
    return buckets;
  }, [productsData]);

  if (isLoading) {
    return (
      <div>
        <h1 className="text-2xl font-bold text-slate-800 mb-6">نمای کلی بازار</h1>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[0, 1, 2, 3].map((i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <h1 className="text-2xl font-bold text-slate-800 mb-6">نمای کلی بازار</h1>
        <ErrorState message={`خطا در دریافت داده‌های بازار: ${String(error)}`} onRetry={() => refetch()} />
      </div>
    );
  }

  const hours = freshnessHours(overview?.last_updated_at ?? null);
  const freshnessDot = hours != null ? getFreshnessColor(hours) : 'bg-slate-400';

  const stats = [
    {
      label: 'کل محصولات نظارت‌شده',
      value: overview?.total_products ?? 0,
      icon: Package,
      iconClass: 'bg-indigo-100 text-indigo-600',
    },
    {
      label: 'محصولات دارای فروشنده',
      value: overview?.products_with_sellers ?? 0,
      icon: TrendingUp,
      iconClass: 'bg-emerald-100 text-emerald-600',
    },
    {
      label: 'میانگین تعداد فروشنده',
      value: overview?.avg_sellers_per_product ?? 0,
      icon: Users,
      iconClass: 'bg-blue-100 text-blue-600',
    },
    {
      label: 'میانگین امتیاز رقابت',
      value: overview?.avg_competition_score ?? 0,
      icon: Gauge,
      iconClass: 'bg-amber-100 text-amber-600',
    },
  ];

  const maxBucket = Math.max(1, ...Object.values(marginBuckets));

  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-800 mb-6">نمای کلی بازار</h1>

      {/* Freshness banner */}
      {hours != null && (
        <div className="flex items-center gap-2 bg-white border border-slate-200 rounded-xl px-5 py-3 mb-6 shadow-sm">
          <span className={`w-3 h-3 rounded-full ${freshnessDot}`} />
          <span className="text-sm text-slate-600">وضعیت داده‌ها: {freshnessLabel(hours)}</span>
          {overview?.last_updated_at && (
            <span className="text-sm text-slate-400 ml-auto">
              آخرین به‌روزرسانی: {formatDate(overview.last_updated_at)}
            </span>
          )}
        </div>
      )}

      {/* Stat cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {stats.map((s) => (
          <Card key={s.label} className="flex items-center gap-4">
            <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${s.iconClass}`}>
              <s.icon className="w-6 h-6" />
            </div>
            <div>
              <p className="text-sm text-slate-500">{s.label}</p>
              <p className="text-2xl font-bold text-slate-800">{formatNumber(s.value)}</p>
            </div>
          </Card>
        ))}
      </div>

      {/* Margin histogram */}
      <Card className="mb-4">
        <h2 className="text-lg font-semibold text-slate-800 mb-4 flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-indigo-600" />
          توزیع حاشیه سود
        </h2>
        <div className="flex gap-4">
          {Object.entries(marginBuckets).map(([label, count]) => (
            <div key={label} className="flex-1">
              <div className="flex items-end h-36 bg-slate-50 rounded-lg overflow-hidden">
                <div
                  className={`w-full rounded-t-lg transition-all ${
                    label.startsWith('منفی')
                      ? 'bg-red-400'
                      : label.startsWith('۰')
                        ? 'bg-amber-400'
                        : label.startsWith('بیش')
                          ? 'bg-emerald-400'
                          : 'bg-slate-300'
                  }`}
                  style={{ height: `${(count / maxBucket) * 100}%` }}
                />
              </div>
              <p className="text-center text-sm font-medium text-slate-700 mt-2">{count}</p>
              <p className="text-center text-xs text-slate-500">{label}</p>
            </div>
          ))}
        </div>
        {Object.values(marginBuckets).every((v) => v === 0) && (
          <p className="text-sm text-slate-400 text-center py-6 flex items-center justify-center gap-2">
            <Clock className="w-4 h-4" /> هنوز داده‌ای برای حاشیه سود ثبت نشده است
          </p>
        )}
      </Card>
    </div>
  );
}