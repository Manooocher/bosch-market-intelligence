import { useReactTable, getCoreRowModel, getSortedRowModel, flexRender, createColumnHelper } from '@tanstack/react-table';
import type { ProductListItem } from '../../api/types';
import { TableSkeleton } from '../ui/Loading';
import { ArrowUpDown } from 'lucide-react';
import { formatPrice, formatNumber } from '../../utils/format';
import { getCategoryLabelFromKey } from '../../utils/categories';
import { getMarginColor } from '../../utils/colors';
import type { SortingState, OnChangeFn } from '@tanstack/react-table';
import { useNavigate } from 'react-router-dom';

const columnHelper = createColumnHelper<ProductListItem>();

const columns = [
  columnHelper.accessor('title', {
    header: 'محصول',
    cell: (info) => (
      <div className="flex flex-col">
        <span className="font-medium text-slate-800">{info.getValue() ?? '—'}</span>
        {info.row.original.sku && (
          <span className="text-xs text-slate-500" dir="ltr">{info.row.original.sku}</span>
        )}
      </div>
    ),
  }),
  columnHelper.accessor('category', {
    header: 'دسته',
    enableSorting: false,
    cell: (info) => <span className="text-slate-600">{getCategoryLabelFromKey(info.getValue() as string)}</span>,
  }),
  columnHelper.accessor('seller_count', {
    header: 'فروشنده',
    cell: (info) => <span dir="ltr">{formatNumber(info.getValue() as number)}</span>,
  }),
  columnHelper.accessor('min_price_rial', {
    header: 'حداقل قیمت',
    cell: (info) => <span dir="ltr">{formatPrice(info.getValue() as number)}</span>,
  }),
  columnHelper.accessor('median_price_rial', {
    header: 'قیمت میانه',
    cell: (info) => <span dir="ltr">{formatPrice(info.getValue() as number)}</span>,
  }),
  columnHelper.accessor('margin_vs_min_pct', {
    header: 'حاشیه %',
    enableSorting: false,
    cell: (info) => {
      const v = info.getValue() as number | null;
      if (v == null) return <span>—</span>;
      return (
        <span className={`px-2 py-1 rounded text-xs font-medium ${getMarginColor(v)}`}>
          {v > 0 ? '+' : ''}{v.toFixed(1)}%
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

export function ProductTable({ data, isLoading, sorting, onSortingChange }: ProductTableProps) {
  const navigate = useNavigate();

  const table = useReactTable({
    data,
    columns,
    state: { sorting },
    onSortingChange,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    manualSorting: true,
  });

  if (isLoading) return <TableSkeleton />;
  if (!data || data.length === 0) {
    return (
      <div className="py-12 text-center text-slate-500">
        <p>محصولی یافت نشد</p>
      </div>
    );
  }

  return (
    <div className="overflow-auto border border-slate-200 rounded-lg" style={{ maxHeight: '75vh' }}>
      <table className="w-full border-collapse">
        <thead className="bg-slate-50 sticky top-0 z-10">
          {table.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <th
                  key={header.id}
                  className="px-4 py-3 text-right text-sm font-medium text-slate-600 cursor-pointer hover:bg-slate-100 transition-colors"
                  onClick={header.column.getToggleSortingHandler()}
                >
                  <div className="flex items-center gap-1">
                    {flexRender(header.column.columnDef.header, header.getContext())}
                    {header.column.getIsSorted() && (
                      <ArrowUpDown className="w-3 h-3 text-indigo-600" />
                    )}
                  </div>
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <tr
              key={row.id}
              className="border-b border-slate-100 hover:bg-slate-50 cursor-pointer transition-colors"
              onClick={() => navigate(`/products/${row.original.torob_product_id}`)}
            >
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id} className="px-4 py-3 text-sm">
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}