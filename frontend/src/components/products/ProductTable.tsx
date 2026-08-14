import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  createColumnHelper,
  type SortingState,
  type OnChangeFn,
} from '@tanstack/react-table';
import type { ProductListItem } from '../../api/types';
import { ProductRow } from './ProductRow';
import { TableSkeleton } from '../ui/Loading';
import { ArrowUpDown } from 'lucide-react';
import { formatPrice, formatNumber } from '../../utils/format';
import { getCategoryLabelFromKey } from '../../utils/categories';

const columnHelper = createColumnHelper<ProductListItem>();

const columns = [
  columnHelper.accessor('title', {
    header: 'محصول',
    cell: (info) => (
      <div>
        <div className="font-medium text-slate-800 max-w-xs truncate" title={info.getValue() ?? ''}>
          {info.getValue() ?? '—'}
        </div>
        <div className="text-xs text-slate-400" dir="ltr">
          {info.row.original.sku ?? '—'}
        </div>
      </div>
    ),
    enableSorting: false,
  }),
  columnHelper.accessor('category', {
    header: 'دسته',
    enableSorting: false,
    cell: (info) => <span className="text-slate-600">{getCategoryLabelFromKey(info.getValue())}</span>,
  }),
  columnHelper.accessor('seller_count', {
    header: 'فروشنده',
    cell: (info) => <span dir="ltr">{formatNumber(info.getValue())}</span>,
  }),
  columnHelper.accessor('min_price_rial', {
    header: 'حداقل قیمت',
    cell: (info) => <span dir="ltr">{formatPrice(info.getValue())}</span>,
  }),
  columnHelper.accessor('median_price_rial', {
    header: 'قیمت میانه',
    cell: (info) => <span dir="ltr">{formatPrice(info.getValue())}</span>,
  }),
  columnHelper.accessor('margin_vs_min_pct', {
    header: 'حاشیه %',
    enableSorting: false,
    cell: (info) => {
      const v = info.getValue();
      if (v == null) return <span>—</span>;
      return (
        <span
          className={`px-2 py-0.5 rounded-full text-xs font-medium ${
            v > 10
              ? 'bg-emerald-100 text-emerald-700'
              : v >= 0
                ? 'bg-amber-100 text-amber-700'
                : 'bg-red-100 text-red-700'
          }`}
        >
          {v > 0 ? '+' : ''}
          {v.toFixed(1)}٪
        </span>
      );
    },
  }),
];

interface ProductTableProps {
  data: ProductListItem[];
  isLoading: boolean;
  sorting: SortingState;
  onSortingChange: OnChangeFn<SortingState>;
}

/** TanStack Table v8 with server-side sorting; row click navigates to detail. */
export function ProductTable({ data, isLoading, sorting, onSortingChange }: ProductTableProps) {
  const table = useReactTable({
    data,
    columns,
    state: { sorting },
    onSortingChange,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    manualSorting: true,
  });

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          {table.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id} className="border-b border-slate-200 bg-slate-50">
              {headerGroup.headers.map((header) => (
                <th
                  key={header.id}
                  className="px-4 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wide whitespace-nowrap"
                >
                  {header.isPlaceholder ? null : header.column.getCanSort() ? (
                    <button
                      className="inline-flex items-center gap-1 hover:text-indigo-600"
                      onClick={header.column.getToggleSortingHandler()}
                    >
                      {flexRender(header.column.columnDef.header, header.getContext())}
                      <ArrowUpDown className="w-3.5 h-3.5" />
                    </button>
                  ) : (
                    flexRender(header.column.columnDef.header, header.getContext())
                  )}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        {isLoading ? (
          <TableSkeleton cols={6} rows={10} />
        ) : (
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <ProductRow key={row.id} row={row} />
            ))}
          </tbody>
        )}
      </table>
    </div>
  );
}