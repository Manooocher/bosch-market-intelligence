import { useState, useMemo } from 'react';
import type { SortingState, OnChangeFn, Updater } from '@tanstack/react-table';
import { useProducts } from '../hooks/useProducts';
import { ProductTable } from '../components/products/ProductTable';
import { ProductSearch } from '../components/products/ProductSearch';
import { CategoryFilter } from '../components/products/CategoryFilter';
import { ErrorState } from '../components/ui/ErrorState';
import { EmptyState } from '../components/ui/EmptyState';
import { Card } from '../components/ui/Card';

export function ProductsPage() {
  const [sorting, setSorting] = useState<SortingState>([{ id: 'seller_count', desc: true }]);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');

  // Fetch ALL products (server-side sorting only). The list is virtualized
  // client-side — no pagination.
  const sort = sorting[0];
  const { data, isLoading, isFetching, error, refetch } = useProducts({
    sort_by: sort?.id ?? 'competition_score',
    sort_dir: sort?.desc ? 'desc' : 'asc',
    per_page: 1000, // backend cap; returns everything
  });

  // Client-side filtering (search + category) over the full fetched list.
  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return (data?.items ?? []).filter((p) => {
      if (category && p.category !== category) return false;
      if (!q) return true;
      const hay = `${p.title ?? ''} ${p.sku ?? ''}`.toLowerCase();
      return hay.includes(q);
    });
  }, [data, search, category]);

  // Derive available categories from the raw (unfiltered) list.
  const availableCategories = useMemo(() => {
    const set = new Set<string>();
    (data?.items ?? []).forEach((p) => {
      if (p.category) set.add(p.category);
    });
    return Array.from(set);
  }, [data]);

  const onSortingChange: OnChangeFn<SortingState> = (updaterOrValue: Updater<SortingState>) => {
    const next = typeof updaterOrValue === 'function' ? updaterOrValue(sorting) : updaterOrValue;
    setSorting(next);
  };

  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-800 mb-6">محصولات</h1>

      {/* Toolbar */}
      <div className="flex flex-col sm:flex-row gap-3 mb-4">
        <div className="flex-1">
          <ProductSearch value={search} onChange={setSearch} />
        </div>
        <CategoryFilter
          categories={availableCategories}
          value={category}
          onChange={setCategory}
        />
      </div>

      {error ? (
        <ErrorState message={`خطا در دریافت محصولات: ${String(error)}`} onRetry={() => refetch()} />
      ) : (
        <Card padding="sm">
          <div className="flex items-center justify-between px-4 py-3 text-sm text-slate-500">
            <span>{filtered.length.toLocaleString('fa-IR')} محصول</span>
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
        </Card>
      )}
    </div>
  );
}