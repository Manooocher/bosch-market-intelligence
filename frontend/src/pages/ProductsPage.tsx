import { useState } from 'react';
import type { SortingState, OnChangeFn, Updater } from '@tanstack/react-table';
import { useProducts } from '../hooks/useProducts';
import { useCategories } from '../hooks/useCategories';
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

  // Server-side filtering + sorting. The backend returns all matching products
  // (no pagination); search/category are applied server-side.
  const sort = sorting[0];
  const { data, isLoading, isFetching, error, refetch } = useProducts({
    sort_by: sort?.id ?? 'competition_score',
    sort_dir: sort?.desc ? 'desc' : 'asc',
    search: search || undefined,
    category: category || undefined,
  });

  // Category dropdown from the server-side categories endpoint.
  const { data: categories } = useCategories();
  const rows = data?.items ?? [];

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
          categories={categories ?? []}
          value={category}
          onChange={setCategory}
        />
      </div>

      {error ? (
        <ErrorState message={`خطا در دریافت محصولات: ${String(error)}`} onRetry={() => refetch()} />
      ) : (
        <Card padding="sm">
          <div className="flex items-center justify-between px-4 py-3 text-sm text-slate-500">
            <span>{rows.length.toLocaleString('fa-IR')} محصول</span>
            {isFetching && <span className="text-indigo-500">در حال بارگذاری…</span>}
          </div>

          <ProductTable
            data={rows}
            isLoading={isLoading}
            sorting={sorting}
            onSortingChange={onSortingChange}
          />

          {!isLoading && rows.length === 0 && (
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