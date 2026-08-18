import { useNavigate } from 'react-router-dom';
import { Plus, Pencil, Trash2, Eye } from 'lucide-react';
import { useShipments } from '../hooks/useShipments';
import { shipmentsApi } from '../api/shipments';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { ErrorState } from '../components/ui/ErrorState';
import { EmptyState } from '../components/ui/EmptyState';
import { formatNumber, formatDate } from '../utils/format';

export function ShipmentsPage() {
  const navigate = useNavigate();
  const { data, isLoading, error, refetch } = useShipments();

  const handleDelete = async (id: number) => {
    if (!window.confirm('آیا از حذف این محموله مطمئن هستید؟')) return;
    await shipmentsApi.delete(id);
    refetch();
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-slate-800">محموله‌ها</h1>
        <button
          onClick={() => navigate('/shipments/new')}
          className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium transition-colors"
        >
          <Plus className="w-4 h-4" />
          ایجاد محموله جدید
        </button>
      </div>

      {error ? (
        <ErrorState message={`خطا در دریافت محموله‌ها: ${String(error)}`} onRetry={() => refetch()} />
      ) : (
        <Card padding="sm">
          {isLoading ? (
            <div className="space-y-2 p-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="h-12 bg-slate-100 rounded animate-pulse" />
              ))}
            </div>
          ) : !data || data.length === 0 ? (
            <EmptyState
              title="محموله‌ای یافت نشد"
              description="برای شروع، یک محموله جدید ایجاد کنید."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-slate-50">
                  <tr className="border-b border-slate-200">
                    <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500">نام</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500">وضعیت</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500">اقلام</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500">ارزش کل ($)</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500">هزینه‌ها ($)</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500">تاریخ</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500">عملیات</th>
                  </tr>
                </thead>
                <tbody>
                  {data.map((s) => (
                    <tr
                      key={s.id}
                      className="border-b border-slate-100 hover:bg-slate-50 cursor-pointer transition-colors"
                      onClick={() => navigate(`/shipments/${s.id}`)}
                    >
                      <td className="px-4 py-3 font-medium text-slate-800">{s.name}</td>
                      <td className="px-4 py-3">
                        <Badge variant={s.status === 'finalized' ? 'success' : 'warning'}>
                          {s.status === 'finalized' ? 'نهایی شده' : 'پیش‌نویس'}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-slate-600">{s.item_count}</td>
                      <td className="px-4 py-3 text-slate-700" dir="ltr">
                        {formatNumber(s.total_value_usd)}
                      </td>
                      <td className="px-4 py-3 text-slate-700" dir="ltr">
                        {formatNumber(s.total_costs_usd)}
                      </td>
                      <td className="px-4 py-3 text-slate-500">{formatDate(s.created_at)}</td>
                      <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => navigate(`/shipments/${s.id}`)}
                            className="p-1.5 rounded hover:bg-slate-100 text-slate-500"
                            title="مشاهده"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                          {s.status === 'draft' && (
                            <>
                              <button
                                onClick={() => navigate(`/shipments/${s.id}/edit`)}
                                className="p-1.5 rounded hover:bg-slate-100 text-slate-500"
                                title="ویرایش"
                              >
                                <Pencil className="w-4 h-4" />
                              </button>
                              <button
                                onClick={() => handleDelete(s.id)}
                                className="p-1.5 rounded hover:bg-red-50 text-red-500"
                                title="حذف"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}