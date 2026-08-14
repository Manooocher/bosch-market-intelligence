import { useNavigate } from 'react-router-dom';
import { flexRender, type Row } from '@tanstack/react-table';
import type { ProductListItem } from '../../api/types';

/**
 * Individual table row — navigates to the product detail page on click.
 * Cells are rendered via flexRender from the column definitions so the
 * table columns remain the single source of truth.
 */
export function ProductRow({ row }: { row: Row<ProductListItem> }) {
  const navigate = useNavigate();

  return (
    <tr
      onClick={() => navigate(`/products/${row.original.torob_product_id}`)}
      className="border-b border-slate-100 hover:bg-slate-50 cursor-pointer transition-colors"
    >
      {row.getVisibleCells().map((cell) => (
        <td key={cell.id} className="px-4 py-3 text-sm">
          {flexRender(cell.column.columnDef.cell, cell.getContext())}
        </td>
      ))}
    </tr>
  );
}