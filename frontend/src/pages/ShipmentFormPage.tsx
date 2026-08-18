import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Plus, Trash2, ArrowRight } from 'lucide-react';
import { useShipment } from '../hooks/useShipments';
import { shipmentsApi, ShipmentItemInput, ShipmentCostInput, CostType } from '../api/shipments';
import { COST_TYPE_LABELS, COST_TYPES } from '../utils/shipmentCosts';
import { Card } from '../components/ui/Card';
import { ErrorState } from '../components/ui/ErrorState';
import { formatNumber } from '../utils/format';

interface ItemRow {
  key: string;
  title: string;
  sku: string;
  quantity: number;
  unit_price: string;
}

interface CostRow {
  key: string;
  cost_type: CostType;
  description: string;
  amount: string;
}

function emptyItem(): ItemRow {
  return { key: crypto.randomUUID(), title: '', sku: '', quantity: 1, unit_price: '' };
}

function emptyCost(): CostRow {
  return { key: crypto.randomUUID(), cost_type: 'shipping', description: '', amount: '' };
}

export function ShipmentFormPage() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const shipmentId = id ? Number(id) : null;
  const isEdit = shipmentId != null && !Number.isNaN(shipmentId);

  const { data: existing, isLoading: loadingExisting } = useShipment(isEdit ? shipmentId : null);

  const [name, setName] = useState('');
  const [notes, setNotes] = useState('');
  const [items, setItems] = useState<ItemRow[]>([emptyItem()]);
  const [costs, setCosts] = useState<CostRow[]>([emptyCost()]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load existing data in edit mode
  useEffect(() => {
    if (isEdit && existing) {
      setName(existing.name);
      setNotes(existing.notes ?? '');
      setItems(existing.items.map((it) => ({
        key: crypto.randomUUID(),
        title: it.title,
        sku: it.sku ?? '',
        quantity: it.quantity,
        unit_price: String(it.unit_purchase_price_usd),
      })));
      setCosts(existing.costs.map((c) => ({
        key: crypto.randomUUID(),
        cost_type: c.cost_type,
        description: c.description ?? '',
        amount: String(c.amount_usd),
      })));
    }
  }, [isEdit, existing]);

  const updateItem = (key: string, patch: Partial<ItemRow>) =>
    setItems((prev) => prev.map((it) => (it.key === key ? { ...it, ...patch } : it)));
  const updateCost = (key: string, patch: Partial<CostRow>) =>
    setCosts((prev) => prev.map((c) => (c.key === key ? { ...c, ...patch } : c)));

  const totalValue = items.reduce(
    (sum, it) => sum + (Number(it.unit_price) || 0) * (it.quantity || 0),
    0,
  );
  const totalCosts = costs.reduce((sum, c) => sum + (Number(c.amount) || 0), 0);

  const valid = name.trim() !== '' && items.some((it) => it.title.trim() !== '' && it.quantity > 0);

  const buildPayload = () => ({
    name: name.trim(),
    notes: notes.trim() || null,
    items: items
      .filter((it) => it.title.trim() !== '')
      .map<ShipmentItemInput>((it) => ({
        title: it.title.trim(),
        sku: it.sku.trim() || null,
        quantity: it.quantity || 1,
        unit_purchase_price_usd: Number(it.unit_price) || 0,
      })),
    costs: costs
      .filter((c) => Number(c.amount) > 0)
      .map<ShipmentCostInput>((c) => ({
        cost_type: c.cost_type,
        description: c.description?.trim() || null,
        amount_usd: Number(c.amount) || 0,
      })),
  });

  const save = async (finalize: boolean) => {
    if (!valid) {
      setError('لطفاً نام محموله و حداقل یک محصول را وارد کنید.');
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const payload = buildPayload();
      let created;
      if (isEdit) {
        created = await shipmentsApi.update(shipmentId as number, payload);
      } else {
        created = await shipmentsApi.create(payload);
      }
      const targetId = created.id;
      if (finalize) {
        await shipmentsApi.finalize(targetId);
      }
      navigate(`/shipments/${targetId}`);
    } catch (e: unknown) {
      const detail =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'خطا در ذخیره محموله';
      setError(detail);
      setSubmitting(false);
    }
  };

  if (isEdit && loadingExisting) {
    return (
      <div>
        <h1 className="text-2xl font-bold text-slate-800 mb-6">ویرایش محموله</h1>
        <div className="h-64 bg-slate-100 rounded-xl animate-pulse" />
      </div>
    );
  }

  if (isEdit && existing?.status === 'finalized') {
    return (
      <div>
        <button
          onClick={() => navigate(`/shipments/${existing.id}`)}
          className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-indigo-600 mb-4"
        >
          <ArrowRight className="w-4 h-4" /> بازگشت
        </button>
        <Card>
          <h1 className="text-2xl font-bold text-slate-800 mb-4">ویرایش محموله</h1>
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-amber-800">
            این محموله نهایی شده و قابل ویرایش نیست.
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div>
      <button
        onClick={() => navigate('/shipments')}
        className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-indigo-600 mb-4"
      >
        <ArrowRight className="w-4 h-4" /> بازگشت به محموله‌ها
      </button>

      <h1 className="text-2xl font-bold text-slate-800 mb-6">
        {isEdit ? 'ویرایش محموله' : 'ایجاد محموله جدید'}
      </h1>

      {error && <ErrorState message={error} />}

      {/* Section 1: Shipment info */}
      <Card className="mb-6">
        <h2 className="text-lg font-semibold text-slate-800 mb-4">مشخصات محموله</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-slate-600 mb-1">نام محموله *</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2.5 rounded-lg border border-slate-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="مثلاً محموله واردات شهریور"
            />
          </div>
          <div>
            <label className="block text-sm text-slate-600 mb-1">یادداشت</label>
            <input
              type="text"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full px-3 py-2.5 rounded-lg border border-slate-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
        </div>
      </Card>

      {/* Section 2: Items */}
      <Card className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-slate-800">محصولات محموله</h2>
          <button
            onClick={() => setItems((prev) => [...prev, emptyItem()])}
            className="inline-flex items-center gap-1.5 text-sm text-indigo-600 hover:text-indigo-800"
          >
            <Plus className="w-4 h-4" /> افزودن محصول
          </button>
        </div>

        <div className="space-y-3">
          {items.map((it) => (
            <div key={it.key} className="grid grid-cols-1 md:grid-cols-12 gap-3 items-start bg-slate-50 rounded-lg p-3">
              <div className="md:col-span-4">
                <label className="block text-xs text-slate-500 mb-1">عنوان محصول *</label>
                <input
                  type="text"
                  value={it.title}
                  onChange={(e) => updateItem(it.key, { title: e.target.value })}
                  className="w-full px-3 py-2 rounded border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div className="md:col-span-2">
                <label className="block text-xs text-slate-500 mb-1">SKU</label>
                <input
                  type="text"
                  value={it.sku}
                  dir="ltr"
                  onChange={(e) => updateItem(it.key, { sku: e.target.value })}
                  className="w-full px-3 py-2 rounded border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div className="md:col-span-2">
                <label className="block text-xs text-slate-500 mb-1">تعداد</label>
                <input
                  type="number"
                  min={1}
                  value={it.quantity}
                  onChange={(e) => updateItem(it.key, { quantity: Number(e.target.value) })}
                  className="w-full px-3 py-2 rounded border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div className="md:col-span-3">
                <label className="block text-xs text-slate-500 mb-1">قیمت خرید هر واحد ($)</label>
                <input
                  type="number"
                  min={0}
                  dir="ltr"
                  value={it.unit_price}
                  onChange={(e) => updateItem(it.key, { unit_price: e.target.value })}
                  className="w-full px-3 py-2 rounded border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div className="md:col-span-1 flex justify-end pt-6">
                <button
                  onClick={() => setItems((prev) => prev.filter((x) => x.key !== it.key))}
                  className="p-1.5 rounded hover:bg-red-50 text-red-500"
                  title="حذف"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-4 text-left text-sm text-slate-600">
          جمع ارزش محصولات:{' '}
          <span className="font-semibold text-slate-800" dir="ltr">${formatNumber(totalValue)}</span>
        </div>
      </Card>

      {/* Section 3: Costs */}
      <Card className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-slate-800">هزینه‌های محموله</h2>
          <button
            onClick={() => setCosts((prev) => [...prev, emptyCost()])}
            className="inline-flex items-center gap-1.5 text-sm text-indigo-600 hover:text-indigo-800"
          >
            <Plus className="w-4 h-4" /> افزودن هزینه
          </button>
        </div>

        <div className="space-y-3">
          {costs.map((c) => (
            <div key={c.key} className="grid grid-cols-1 md:grid-cols-12 gap-3 items-start bg-slate-50 rounded-lg p-3">
              <div className="md:col-span-3">
                <label className="block text-xs text-slate-500 mb-1">نوع هزینه</label>
                <select
                  value={c.cost_type}
                  onChange={(e) => updateCost(c.key, { cost_type: e.target.value as CostType })}
                  className="w-full px-3 py-2 rounded border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  {COST_TYPES.map((ct) => (
                    <option key={ct} value={ct}>{COST_TYPE_LABELS[ct]}</option>
                  ))}
                </select>
              </div>
              <div className="md:col-span-5">
                <label className="block text-xs text-slate-500 mb-1">توضیح</label>
                <input
                  type="text"
                  value={c.description}
                  onChange={(e) => updateCost(c.key, { description: e.target.value })}
                  className="w-full px-3 py-2 rounded border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div className="md:col-span-3">
                <label className="block text-xs text-slate-500 mb-1">مبلغ ($)</label>
                <input
                  type="number"
                  min={0}
                  dir="ltr"
                  value={c.amount}
                  onChange={(e) => updateCost(c.key, { amount: e.target.value })}
                  className="w-full px-3 py-2 rounded border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div className="md:col-span-1 flex justify-end pt-6">
                <button
                  onClick={() => setCosts((prev) => prev.filter((x) => x.key !== c.key))}
                  className="p-1.5 rounded hover:bg-red-50 text-red-500"
                  title="حذف"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-4 text-left text-sm text-slate-600">
          جمع هزینه‌ها:{' '}
          <span className="font-semibold text-slate-800" dir="ltr">${formatNumber(totalCosts)}</span>
        </div>
      </Card>

      {/* Section 4: Summary + actions */}
      <Card className="mb-6">
        <h2 className="text-lg font-semibold text-slate-800 mb-4">خلاصه</h2>
        <div className="grid grid-cols-3 gap-4 text-sm">
          <div>
            <p className="text-slate-500">جمع ارزش محصولات</p>
            <p className="text-xl font-bold text-slate-800" dir="ltr">${formatNumber(totalValue)}</p>
          </div>
          <div>
            <p className="text-slate-500">جمع هزینه‌ها</p>
            <p className="text-xl font-bold text-slate-800" dir="ltr">${formatNumber(totalCosts)}</p>
          </div>
          <div>
            <p className="text-slate-500">برآورد کل به ورود</p>
            <p className="text-xl font-bold text-slate-800" dir="ltr">${formatNumber(totalValue + totalCosts)}</p>
          </div>
        </div>
      </Card>

      <div className="flex flex-wrap gap-3">
        <button
          onClick={() => save(false)}
          disabled={submitting}
          className="px-5 py-2.5 bg-white border border-indigo-600 text-indigo-600 hover:bg-indigo-50 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
        >
          ذخیره پیش‌نویس
        </button>
        <button
          onClick={() => save(true)}
          disabled={submitting}
          className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
        >
          ذخیره و نهایی‌سازی
        </button>
        <button
          onClick={() => navigate('/shipments')}
          className="px-5 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-sm font-medium transition-colors"
        >
          انصراف
        </button>
      </div>
    </div>
  );
}