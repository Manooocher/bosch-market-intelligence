import { useState, useMemo } from 'react';
import type { SortingState, OnChangeFn, Updater } from '@tanstack/react-table';
import { useProducts } from '../hooks/useProducts';
import { ProductTable } from '../components/products/ProductTable';
import { ProductSearch } from '../components/products/ProductSearch';
import { CategoryFilter } from '../components/products/CategoryFilter';
import { Pagination } from '../components/ui/Pagination';
import { ErrorState } from '../components/ui/ErrorState';
import { EmptyState } from '../components/ui/EmptyState';
import { Card } from '../components/ui/Card';

const PAGE_SIZE = 25;

export function ProductsPage() {
  const [page, setPage] = useState(1);
  const [sorting, setSorting] = useState<SortingState>([{ id: 'seller_count', desc: true }]);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');

  // Server-side sorts/paginates; search & category are applied client-side on the
  // fetched page because the backend currently ignores those query params.
  const sort = sorting[0];
  const { data, isLoading, isFetching, error, refetch } = useProducts({
    page,
    per_page: PAGE_SIZE,
    sort_by: sort?.id ?? 'competition_score',
    sort_dir: sort?.desc ? 'desc' : 'asc',
  });

  // Client-side filtering (search + category) over the current page's items.
  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return (data?.items ?? []).filter((p) => {
      if (category && p.category !== category) return false;
      if (!q) return true;
      const hay = `${p.title ?? ''} ${p.sku ?? ''}`.toLowerCase();
      return hay.includes(q);
    });
  }, [data, search, category]);

  // Derive available categories from the raw (unfiltered) page so the dropdown
  // stays populated even while filtering.
  const availableCategories = useMemo(() => {
    const set = new Set<string>();
    (data?.items ?? []).forEach((p) => {
      if (p.category) set.add(p.category);
    });
    return Array.from(set);
  }, [data]);

  const onSortingChange: OnChangeFn<SortingState> = (updaterOrValue: Updater<SortingState>) => {
    // TanStack's updater may be a value or a function of the previous state.
    const next = typeof updaterOrValue === 'function' ? updaterOrValue(sorting) : updaterOrValue;
    setSorting(next);
    setPage(1);
  };

  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-800 mb-6">محصولات</h1>

      {/* Toolbar */}
      <div className="flex flex-col sm:flex-row gap-3 mb-4">
        <div className="flex-1">
          <ProductSearch value={search} onChange={(v) => { setSearch(v); setPage(1); }} />
        </div>
        <CategoryFilter
          categories={availableCategories}
          value={category}
          onChange={(c) => { setCategory(c); setPage(1); }}
        />
      </div>

      {error ? (
        <ErrorState message={`خطا در دریافت محصولات: ${String(error)}`} onRetry={() => refetch()} />
      ) : (
        <Card padding="sm">
          <div className="flex items-center justify-between px-4 py-3 text-sm text-slate-500">
            <span>{(data?.total ?? 0).toLocaleString('fa-IR')} محصول</span>
            {isFetching && <span className="text-indigo-500">در حال بارگذاری…</span>}
          </div>

          <ProductTable
            data={filtered}
            isLoading={isLoading}
            sorting={sorting}
            onSortingChange={onSortingChange}
          />

          {!isLoading && filtered.length === 0 && (
            <EmptyState
              title="محصولی یافت نشد"
              description="تنظیمات جستجو یا فیلتر را تغییر دهید."
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