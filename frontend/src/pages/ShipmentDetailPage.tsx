import { useNavigate, useParams } from 'react-router-dom';
import { ArrowRight, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useShipment } from '../hooks/useShipments';
import { shipmentsApi } from '../api/shipments';
import { useToast } from '../hooks/useToast';
import { apiErrorMessage } from '../utils/error';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { ErrorState } from '../components/ui/ErrorState';
import { Spinner } from '../components/ui/Loading';
import { ConfirmModal } from '../components/ui';
import { formatNumber, formatDate } from '../utils/format';
import { COST_TYPE_LABELS } from '../utils/shipmentCosts';
import type { ShipmentItemResult } from '../api/shipments';

function marginBadge(pct: number | null) {
  if (pct == null) return <Badge variant="neutral">بدون داده</Badge>;
  const sign = pct > 0 ? '+' : '';
  const variant = pct > 0 ? 'success' : 'danger';
  return (
    <Badge variant={variant}>
      {sign}
      {pct.toFixed(1)}٪
    </Badge>
  );
}

function profitBadge(p: boolean | null) {
  if (p == null) return <Badge variant="neutral">بدون داده</Badge>;
  return <Badge variant={p ? 'success' : 'danger'}>{p ? 'سودآور' : 'زیان‌ده'}</Badge>;
}

function ItemRow({ item, onClick }: { item: ShipmentItemResult; onClick: () => void }) {
  return (
    <tr
      onClick={onClick}
      className="border-b border-slate-100 hover:bg-slate-50 cursor-pointer transition-colors"
    >
      <td className="px-4 py-3">
        <div className="font-medium text-slate-800 max-w-xs truncate" title={item.title}>{item.title}</div>
        {item.sku && <div className="text-xs text-slate-400" dir="ltr">{item.sku}</div>}
      </td>
      <td className="px-4 py-3 text-slate-600">{item.quantity}</td>
      <td className="px-4 py-3 text-slate-700" dir="ltr">{formatNumber(item.unit_purchase_price_usd)}</td>
      <td className="px-4 py-3 text-slate-700" dir="ltr">{formatNumber(item.allocated_cost_per_unit_usd)}</td>
      <td className="px-4 py-3 text-slate-700 font-medium" dir="ltr">{formatNumber(item.landed_cost_usd)}</td>
      <td className="px-4 py-3 text-slate-700" dir="ltr">{item.landed_cost_per_unit_toman != null ? formatNumber(item.landed_cost_per_unit_toman) : '—'}</td>
      <td className="px-4 py-3 text-slate-700" dir="ltr">{item.market_min_toman != null ? formatNumber(item.market_min_toman) : '—'}</td>
      <td className="px-4 py-3 text-slate-700" dir="ltr">{item.market_median_toman != null ? formatNumber(item.market_median_toman) : '—'}</td>
      <td className="px-4 py-3">{marginBadge(item.margin_vs_min_pct)}</td>
      <td className="px-4 py-3">{marginBadge(item.margin_vs_median_pct)}</td>
      <td className="px-4 py-3">{profitBadge(item.is_profitable)}</td>
    </tr>
  );
}

export function ShipmentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const shipmentId = id ? Number(id) : null;
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const toast = useToast();

  const [deleteOpen, setDeleteOpen] = useState(false);

  const { data: shipment, isLoading, error, refetch } = useShipment(shipmentId);

  const finalizeMutation = useMutation({
    mutationFn: (shipId: number) => shipmentsApi.finalize(shipId),
    onSuccess: () => {
      toast.success('محموله با موفقیت نهایی شد');
      queryClient.invalidateQueries({ queryKey: ['shipment', shipmentId] });
      queryClient.invalidateQueries({ queryKey: ['shipments'] });
    },
    onError: (err: unknown) => {
      toast.error(apiErrorMessage(err, 'خطا در نهایی‌سازی محموله'));
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (shipId: number) => shipmentsApi.delete(shipId),
    onSuccess: () => {
      toast.success('محموله با موفقیت حذف شد');
      queryClient.invalidateQueries({ queryKey: ['shipments'] });
      navigate('/shipments');
    },
    onError: (err: unknown) => {
      toast.error(apiErrorMessage(err, 'خطا در حذف محموله'));
    },
  });

  const handleDelete = () => {
    if (!shipment || shipment.status !== 'draft') return;
    setDeleteOpen(true);
  };

  const handleFinalize = () => {
    if (!shipment) return;
    finalizeMutation.mutate(shipment.id);
  };

  const handleDeleteConfirm = () => {
    if (!shipment) return;
    deleteMutation.mutate(shipment.id);
    setDeleteOpen(false);
  };

  const handleDeleteCancel = () => setDeleteOpen(false);

  if (isLoading) {
    return <Spinner size="lg" />;
  }

  if (error || !shipment) {
    return (
      <div>
        <h1 className="text-2xl font-bold text-slate-800 mb-6">جزئیات محموله</h1>
        <ErrorState message={`خطا در دریافت محموله: ${String(error)}`} onRetry={() => refetch()} />
      </div>
    );
  }

  const isDraft = shipment.status === 'draft';

  return (
    <div>
      <button
        onClick={() => navigate('/shipments')}
        className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-indigo-600 mb-4"
      >
        <ArrowRight className="w-4 h-4" /> بازگشت به محموله‌ها
      </button>

      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">{shipment.name}</h1>
          <div className="flex flex-wrap items-center gap-3 mt-2 text-sm text-slate-500">
            <Badge variant={isDraft ? 'warning' : 'success'}>
              {isDraft ? 'پیش‌نویس' : 'نهایی شده'}
            </Badge>
            {shipment.dollar_rate != null && (
              <span dir="ltr">نرخ دلار: {formatNumber(shipment.dollar_rate)}</span>
            )}
            <span>تاریخ ایجاد: {formatDate(shipment.created_at)}</span>
            {shipment.finalized_at && <span>نهایی: {formatDate(shipment.finalized_at)}</span>}
          </div>
          {shipment.message && <p className="text-xs text-slate-400 mt-2">{shipment.message}</p>}
        </div>

        {isDraft && (
          <div className="flex items-center gap-2">
            <button
              onClick={() => navigate(`/shipments/${shipment.id}/edit`)}
              className="px-4 py-2 border border-indigo-600 text-indigo-600 hover:bg-indigo-50 rounded-lg text-sm font-medium transition-colors"
            >
              ویرایش
            </button>
            <button
              onClick={handleFinalize}
              disabled={finalizeMutation.isPending}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {finalizeMutation.isPending ? 'در حال نهایی‌سازی...' : 'نهایی‌سازی'}
            </button>
            <button
              onClick={handleDelete}
              disabled={deleteMutation.isPending}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-red-50 text-red-600 hover:bg-red-100 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Trash2 className="w-4 h-4" /> {deleteMutation.isPending ? 'در حال حذف...' : 'حذف'}
            </button>
          </div>
        )}
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <Card>
          <p className="text-sm text-slate-500">ارزش کل محموله</p>
          <p className="text-2xl font-bold text-slate-800" dir="ltr">${formatNumber(shipment.total_value_usd)}</p>
        </Card>
        <Card>
          <p className="text-sm text-slate-500">جمع هزینه‌ها</p>
          <p className="text-2xl font-bold text-slate-800" dir="ltr">${formatNumber(shipment.total_costs_usd)}</p>
        </Card>
        <Card>
          <p className="text-sm text-slate-500">نرخ دلار (ریال)</p>
          <p className="text-2xl font-bold text-slate-800" dir="ltr">
            {shipment.dollar_rate != null ? formatNumber(shipment.dollar_rate) : '—'}
          </p>
        </Card>
        <Card>
          <p className="text-sm text-slate-500">تعداد اقلام</p>
          <p className="text-2xl font-bold text-slate-800">{shipment.items.length}</p>
        </Card>
      </div>

      {/* Results table */}
      <Card className="mb-6" padding="sm">
        <h2 className="text-lg font-semibold text-slate-800 px-4 pt-4 mb-2">نتایج محاسبه</h2>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-slate-50">
              <tr className="border-b border-slate-200">
                <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500">محصول</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500">تعداد</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500">خرید ($)</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500">تسهیم ($)</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500">تمام‌شده ($)</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500">تمام‌شده (ریال)</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500">کمینه بازار</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500">میانه بازار</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500">حاشیه (کمینه)</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500">حاشیه (میانه)</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500">وضعیت</th>
              </tr>
            </thead>
            <tbody>
              {shipment.items.map((item) => (
                <ItemRow
                  key={item.id}
                  item={item}
                  onClick={() => item.torob_product_id && navigate(`/products/${item.torob_product_id}`)}
                />
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Cost breakdown */}
      <Card className="mb-6">
        <h2 className="text-lg font-semibold text-slate-800 mb-4">جزئیات هزینه‌ها</h2>
        {shipment.costs.length === 0 ? (
          <p className="text-sm text-slate-400">هزینه‌ای ثبت نشده است.</p>
        ) : (
          <div className="space-y-2">
            {shipment.costs.map((c) => {
              const pct = shipment.total_costs_usd > 0
                ? ((c.amount_usd / shipment.total_costs_usd) * 100).toFixed(1)
                : '0.0';
              return (
                <div key={c.id} className="flex items-center justify-between bg-slate-50 rounded-lg px-4 py-2">
                  <div>
                    <span className="font-medium text-slate-700">{COST_TYPE_LABELS[c.cost_type] ?? c.cost_type}</span>
                    {c.description && <span className="text-sm text-slate-500 mx-2">— {c.description}</span>}
                  </div>
                  <div className="text-sm text-slate-600">
                    <span className="text-slate-400 ml-2">{pct}٪</span>
                    <span className="font-medium" dir="ltr">${formatNumber(c.amount_usd)}</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </Card>

      <ConfirmModal
        isOpen={deleteOpen && shipment.status === 'draft'}
        title="حذف محموله"
        message="آیا از حذف این محموله مطمئن هستید؟ این عملیات غیرقابل بازگشت است."
        confirmLabel="حذف"
        cancelLabel="انصراف"
        variant="danger"
        isLoading={deleteMutation.isPending}
        onConfirm={handleDeleteConfirm}
        onCancel={handleDeleteCancel}
      />
    </div>
  );
}