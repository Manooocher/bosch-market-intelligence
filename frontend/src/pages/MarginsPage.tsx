import { useState } from 'react';
import { useMargins } from '../hooks/useMargins';
import { Pagination } from '../components/ui/Pagination';
import { ErrorState } from '../components/ui/ErrorState';
import { EmptyState } from '../components/ui/EmptyState';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { formatNumber } from '../utils/format';
import { useNavigate } from 'react-router-dom';

const PAGE_SIZE = 25;

function marginPctBadge(pct: number | null) {
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

export function MarginsPage() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [onlyNegative, setOnlyNegative] = useState(false);
  const [sortBy, setSortBy] = useState<'margin_vs_min_pct' | 'margin_vs_median_pct'>('margin_vs_min_pct');

  const { data, isLoading, error, refetch } = useMargins({
    page,
    per_page: PAGE_SIZE,
    sort_by: sortBy,
    sort_dir: 'desc',
  });

  // Client-side "فقط منفیها" toggle (backend has no such param).
  const rows = onlyNegative
    ? (data?.items ?? []).filter((m) => m.margin_vs_min_pct < 0)
    : (data?.items ?? []);

  return (
    <div>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
        <h1 className="text-2xl font-bold text-slate-800">حاشیه سود</h1>
        <div className="flex items-center gap-3">
          <select
            value={sortBy}
            onChange={(e) => {
              setSortBy(e.target.value as typeof sortBy);
              setPage(1);
            }}
            className="px-3 py-2 rounded-lg border border-slate-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="margin_vs_min_pct">مرتب‌سازی: حاشیه نسبت به کمینه</option>
            <option value="margin_vs_median_pct">مرتب‌سازی: حاشیه نسبت به میانه</option>
          </select>
          <label className="inline-flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
            <input
              type="checkbox"
              checked={onlyNegative}
              onChange={(e) => {
                setOnlyNegative(e.target.checked);
                setPage(1);
              }}
              className="w-4 h-4 rounded text-indigo-600"
            />
            فقط منفی‌ها
          </label>
        </div>
      </div>

      {error ? (
        <ErrorState message={`خطا در دریافت داده‌ها: ${String(error)}`} onRetry={() => refetch()} />
      ) : (
        <Card padding="sm">
          <div className="flex items-center justify-between px-4 py-3 text-sm text-slate-500">
            <span>{(data?.total ?? 0).toLocaleString('fa-IR')} محصول</span>
            {isLoading && <span className="text-indigo-500">در حال بارگذاری…</span>}
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50">
                  <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500">محصول</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500">قیمت نبکاده</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500">کمینه بازار</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500">میانه بازار</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500">حاشیه کمینه</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500">حاشیه میانه</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500">وضعیت</th>
                </tr>
              </thead>
              <tbody>
                {isLoading
                  ? Array.from({ length: 8 }).map((_, i) => (
                      <tr key={i} className="border-b border-slate-100">
                        {Array.from({ length: 7 }).map((_, j) => (
                          <td key={j} className="px-4 py-3">
                            <div className="h-4 bg-slate-100 rounded animate-pulse" />
                          </td>
                        ))}
                      </tr>
                    ))
                  : rows.map((m) => (
                      <tr
                        key={m.sku ?? m.torob_product_id}
                        onClick={() => m.torob_product_id && navigate(`/products/${m.torob_product_id}`)}
                        className="border-b border-slate-100 hover:bg-slate-50 cursor-pointer transition-colors"
                      >
                        <td className="px-4 py-3">
                          <div className="font-medium text-slate-800 max-w-xs truncate" title={m.title ?? ''}>
                            {m.title ?? '—'}
                          </div>
                          <div className="text-xs text-slate-400" dir="ltr">{m.sku ?? '—'}</div>
                        </td>
                        <td className="px-4 py-3 text-sm text-slate-700" dir="ltr">
                          {formatNumber(m.nabkade_price_toman)}
                        </td>
                        <td className="px-4 py-3 text-sm text-slate-700" dir="ltr">
                          {formatNumber(m.market_min_price_toman)}
                        </td>
                        <td className="px-4 py-3 text-sm text-slate-700" dir="ltr">
                          {formatNumber(m.market_median_price_toman)}
                        </td>
                        <td className="px-4 py-3">{marginPctBadge(m.margin_vs_min_pct)}</td>
                        <td className="px-4 py-3">{marginPctBadge(m.margin_vs_median_pct)}</td>
                        <td className="px-4 py-3">
                          <Badge variant={m.is_profitable ? 'success' : 'danger'}>
                            {m.is_profitable ? 'سودآور' : 'زیان'}
                          </Badge>
                        </td>
                      </tr>
                    ))}
              </tbody>
            </table>
          </div>

          {!isLoading && rows.length === 0 && (
            <EmptyState
              title="موردی یافت نشد"
              description="هیچ محصولی با این فیلترها وجود ندارد."
            />
          )}

          {data && data.pages > 1 && (
            <Pagination currentPage={page} totalPages={data.pages} onPageChange={setPage} />
          )}
        </Card>
      )}
    </div>
  );
}