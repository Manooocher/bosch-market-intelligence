import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMargins } from '../hooks/useMargins';
import { ProductSearch } from '../components/products/ProductSearch';
import { CategoryFilter } from '../components/products/CategoryFilter';
import { ErrorState } from '../components/ui/ErrorState';
import { EmptyState } from '../components/ui/EmptyState';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { formatNumber } from '../utils/format';
import { getCategoryLabelFromKey } from '../utils/categories';

function marginBadge(pct: number | null) {
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
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');

  // Fetch ALL margins (server-side sort). Filtering is client-side.
  const { data, isLoading, error, refetch } = useMargins({ sort_by: 'margin_vs_min_pct', sort_dir: 'desc' });

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return (data?.items ?? []).filter((m) => {
      if (category && m.category !== category) return false;
      if (!q) return true;
      const hay = `${m.title ?? ''} ${m.sku ?? ''}`.toLowerCase();
      return hay.includes(q);
    });
  }, [data, search, category]);

  const availableCategories = useMemo(() => {
    const set = new Set<string>();
    (data?.items ?? []).forEach((m) => {
      if (m.category) set.add(m.category);
    });
    return Array.from(set);
  }, [data]);

  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-800 mb-6">حاشیه سود</h1>

      <div className="flex flex-col sm:flex-row gap-3 mb-4">
        <div className="flex-1">
          <ProductSearch value={search} onChange={setSearch} />
        </div>
        <CategoryFilter categories={availableCategories} value={category} onChange={setCategory} />
      </div>

      {error ? (
        <ErrorState message={`خطا در دریافت داده‌ها: ${String(error)}`} onRetry={() => refetch()} />
      ) : (
        <Card padding="sm">
          <div className="flex items-center justify-between px-4 py-3 text-sm text-slate-500">
            <span>{filtered.length.toLocaleString('fa-IR')} محصول</span>
            {isLoading && <span className="text-indigo-500">در حال بارگذاری…</span>}
          </div>

          {isLoading ? (
            <div className="space-y-2 p-4">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="h-10 bg-slate-100 rounded animate-pulse" />
              ))}
            </div>
          ) : (
            <div className="overflow-auto border-t border-slate-100" style={{ maxHeight: '70vh' }}>
              <table className="w-full">
                <thead className="bg-slate-50 sticky top-0 z-10">
                  <tr className="border-b border-slate-200">
                    <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500">محصول</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500">دسته</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500">قیمت نابکده</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500">کمینه بازار</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500">میانه بازار</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500">حاشیه (کمینه)</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500">حاشیه (میانه)</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500">وضعیت</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((m) => (
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
                      <td className="px-4 py-3 text-sm text-slate-600">
                        {getCategoryLabelFromKey(m.category) ?? '—'}
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
                      <td className="px-4 py-3">{marginBadge(m.margin_vs_min_pct)}</td>
                      <td className="px-4 py-3">{marginBadge(m.margin_vs_median_pct)}</td>
                      <td className="px-4 py-3">
                        <Badge variant={m.is_profitable ? 'success' : 'danger'}>
                          {m.is_profitable ? 'سودآور' : 'زیان‌ده'}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {!isLoading && filtered.length === 0 && (
            <EmptyState title="موردی یافت نشد" description="هیچ محصولی با این فیلترها وجود ندارد." />
          )}
        </Card>
      )}
    </div>
  );
}