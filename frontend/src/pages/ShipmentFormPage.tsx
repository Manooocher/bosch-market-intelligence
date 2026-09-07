import { useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Plus, Trash2, ArrowRight } from 'lucide-react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm, useFieldArray } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useShipment } from '../hooks/useShipments';
import { shipmentsApi, ShipmentCreateInput } from '../api/shipments';
import { useToast } from '../hooks/useToast';
import { apiErrorMessage } from '../utils/error';
import { COST_TYPE_LABELS, COST_TYPES } from '../utils/shipmentCosts';
import { Card } from '../components/ui/Card';
import { formatNumber } from '../utils/format';

/* ── Zod schemas ────────────────────────────────────────────────────────────
   Client-side validation that mirrors the backend's ShipmentItem/CostCreate
   constraints (quantity > 0, prices >= 0, at least one item) with Persian
   messages shown inline under each field. */

const inputNumber = (max: number, notNegativeMsg: string) =>
  z
    .number({ error: 'مقدار باید عدد باشد' })
    .min(0, notNegativeMsg)
    .max(max, `مقدار نمی‌تواند بیشتر از ${max.toLocaleString('fa-IR')} باشد`);

const shipmentItemSchema = z.object({
  title: z.string().min(1, 'عنوان محصول الزامی است'),
  sku: z.string().optional(),
  quantity: z
    .number({ error: 'تعداد باید عدد باشد' })
    .int('تعداد باید عدد صحیح باشد')
    .min(1, 'تعداد باید حداقل ۱ باشد')
    .max(10000, 'تعداد نمی‌تواند بیشتر از ۱۰۰۰۰ باشد'),
  unit_purchase_price_usd: inputNumber(1_000_000, 'قیمت نمی‌تواند منفی باشد'),
});

const shipmentCostSchema = z.object({
  cost_type: z.enum(
    ['shipping', 'customs', 'insurance', 'warehouse', 'handling', 'other'] as const,
    { error: 'نوع هزینه معتبر نیست' },
  ),
  description: z.string().optional(),
  amount_usd: inputNumber(10_000_000, 'مبلغ نمی‌تواند منفی باشد'),
});

const shipmentFormSchema = z.object({
  name: z
    .string()
    .min(1, 'نام محموله الزامی است')
    .max(200, 'نام محموله نمی‌تواند بیشتر از ۲۰۰ کاراکتر باشد'),
  notes: z.string().max(1000, 'یادداشت نمی‌تواند بیشتر از ۱۰۰۰ کاراکتر باشد').optional(),
  items: z.array(shipmentItemSchema).min(1, 'حداقل یک قلم کالا لازم است'),
  costs: z.array(shipmentCostSchema),
});

type ShipmentFormValues = z.infer<typeof shipmentFormSchema>;

const emptyItem = { title: '', sku: '', quantity: 1, unit_purchase_price_usd: 0 };
const emptyCost = { cost_type: 'shipping' as const, description: '', amount_usd: 0 };

/* ── Page ────────────────────────────────────────────────────────────────── */

export function ShipmentFormPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const toast = useToast();
  const { id } = useParams<{ id: string }>();
  const shipmentId = id ? Number(id) : null;
  const isEdit = shipmentId != null && !Number.isNaN(shipmentId);

  const { data: existing, isLoading: loadingExisting } = useShipment(isEdit ? shipmentId : null);

  const {
    register,
    control,
    handleSubmit,
    watch,
    reset,
    formState: { errors },
  } = useForm<ShipmentFormValues>({
    resolver: zodResolver(shipmentFormSchema),
    defaultValues: {
      name: '',
      notes: '',
      items: [emptyItem],
      costs: [],
    },
  });

  const { fields: itemFields, append: appendItem, remove: removeItem } = useFieldArray({
    control,
    name: 'items',
  });
  const { fields: costFields, append: appendCost, remove: removeCost } = useFieldArray({
    control,
    name: 'costs',
  });

  // Live summary figures — recomputed as the user edits.
  const watchedItems = watch('items');
  const watchedCosts = watch('costs');
  const totalValue = (watchedItems ?? []).reduce(
    (sum, it) => sum + (Number(it.unit_purchase_price_usd) || 0) * (Number(it.quantity) || 0),
    0,
  );
  const totalCosts = (watchedCosts ?? []).reduce(
    (sum, c) => sum + (Number(c.amount_usd) || 0),
    0,
  );

  // Preload existing shipment values in edit mode (idempotent on arrival).
  useEffect(() => {
    if (isEdit && existing) {
      reset({
        name: existing.name,
        notes: existing.notes ?? '',
        items: existing.items.map((it) => ({
          title: it.title,
          sku: it.sku ?? '',
          quantity: it.quantity,
          unit_purchase_price_usd: Number(it.unit_purchase_price_usd),
        })),
        costs: existing.costs.map((c) => ({
          cost_type: c.cost_type,
          description: c.description ?? '',
          amount_usd: Number(c.amount_usd),
        })),
      });
    }
  }, [isEdit, existing, reset]);

  const saveMutation = useMutation({
    mutationFn: async ({ values, finalize }: { values: ShipmentFormValues; finalize: boolean }) => {
      const payload: ShipmentCreateInput = {
        name: values.name.trim(),
        notes: values.notes?.trim() || null,
        items: values.items.map((it) => ({
          title: it.title.trim(),
          sku: it.sku?.trim() || null,
          quantity: it.quantity || 1,
          unit_purchase_price_usd: Number(it.unit_purchase_price_usd) || 0,
        })),
        costs: values.costs
          .filter((c) => Number(c.amount_usd) > 0)
          .map((c) => ({
            cost_type: c.cost_type,
            description: c.description?.trim() || null,
            amount_usd: Number(c.amount_usd) || 0,
          })),
      };
      const created = isEdit
        ? await shipmentsApi.update(shipmentId as number, payload)
        : await shipmentsApi.create(payload);
      if (finalize && created.id) {
        await shipmentsApi.finalize(created.id);
      }
      return created;
    },
    onSuccess: (created) => {
      toast.success(isEdit ? 'محموله با موفقیت به‌روزرسانی شد' : 'محموله با موفقیت ایجاد شد');
      queryClient.invalidateQueries({ queryKey: ['shipments'] });
      navigate(`/shipments/${created.id}`);
    },
    onError: (err: unknown) => {
      toast.error(apiErrorMessage(err, 'خطا در ذخیره محموله'));
    },
  });

  // Two submit paths — save-as-draft, or save-and-finalize — both run the same
  // validation first via handleSubmit, then pass a `finalize` flag to the mutation.
  const submit = handleSubmit((values) => saveMutation.mutate({ values, finalize: false }));
  const submitAndFinalize = handleSubmit((values) => saveMutation.mutate({ values, finalize: true }));

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

  const inputCls = (hasError: boolean) =>
    `w-full px-3 py-2.5 rounded-lg border bg-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 ${
      hasError ? 'border-red-500' : 'border-slate-200'
    }`;

  return (
    <form onSubmit={submit}>
      <button
        type="button"
        onClick={() => navigate('/shipments')}
        className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-indigo-600 mb-4"
      >
        <ArrowRight className="w-4 h-4" /> بازگشت به محموله‌ها
      </button>

      <h1 className="text-2xl font-bold text-slate-800 mb-6">
        {isEdit ? 'ویرایش محموله' : 'ایجاد محموله جدید'}
      </h1>

      {/* Section 1: Shipment info */}
      <Card className="mb-6">
        <h2 className="text-lg font-semibold text-slate-800 mb-4">مشخصات محموله</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label htmlFor="name" className="block text-sm text-slate-600 mb-1">
              نام محموله *
            </label>
            <input
              id="name"
              type="text"
              {...register('name')}
              className={inputCls(!!errors.name)}
              placeholder="مثلاً محموله واردات شهریور"
            />
            {errors.name && <p className="mt-1 text-sm text-red-600">{errors.name.message}</p>}
          </div>
          <div>
            <label htmlFor="notes" className="block text-sm text-slate-600 mb-1">
              یادداشت
            </label>
            <input
              id="notes"
              type="text"
              {...register('notes')}
              className={inputCls(false)}
            />
            {errors.notes && <p className="mt-1 text-sm text-red-600">{errors.notes.message}</p>}
          </div>
        </div>
      </Card>

      {/* Section 2: Items */}
      <Card className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-slate-800">محصولات محموله</h2>
          <button
            type="button"
            onClick={() => appendItem({ ...emptyItem })}
            className="inline-flex items-center gap-1.5 text-sm text-indigo-600 hover:text-indigo-800"
          >
            <Plus className="w-4 h-4" /> افزودن محصول
          </button>
        </div>

        {errors.items?.root?.message && (
          <p className="mb-4 text-sm text-red-600">{errors.items.root.message}</p>
        )}

        <div className="space-y-3">
          {itemFields.map((field, index) => {
            const itemErrors = errors.items?.[index];
            return (
              <div
                key={field.id}
                className="grid grid-cols-1 md:grid-cols-12 gap-3 items-start bg-slate-50 rounded-lg p-3"
              >
                <div className="md:col-span-4">
                  <label className="block text-xs text-slate-500 mb-1">عنوان محصول *</label>
                  <input
                    type="text"
                    {...register(`items.${index}.title`)}
                    className={inputCls(!!itemErrors?.title)}
                  />
                  {itemErrors?.title && (
                    <p className="mt-1 text-xs text-red-600">{itemErrors.title.message}</p>
                  )}
                </div>
                <div className="md:col-span-2">
                  <label className="block text-xs text-slate-500 mb-1">SKU</label>
                  <input
                    type="text"
                    dir="ltr"
                    {...register(`items.${index}.sku`)}
                    className={inputCls(false)}
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="block text-xs text-slate-500 mb-1">تعداد</label>
                  <input
                    type="number"
                    min={1}
                    {...register(`items.${index}.quantity`, { valueAsNumber: true })}
                    className={inputCls(!!itemErrors?.quantity)}
                  />
                  {itemErrors?.quantity && (
                    <p className="mt-1 text-xs text-red-600">{itemErrors.quantity.message}</p>
                  )}
                </div>
                <div className="md:col-span-3">
                  <label className="block text-xs text-slate-500 mb-1">قیمت خرید هر واحد ($)</label>
                  <input
                    type="number"
                    min={0}
                    step="0.01"
                    dir="ltr"
                    {...register(`items.${index}.unit_purchase_price_usd`, { valueAsNumber: true })}
                    className={inputCls(!!itemErrors?.unit_purchase_price_usd)}
                  />
                  {itemErrors?.unit_purchase_price_usd && (
                    <p className="mt-1 text-xs text-red-600">
                      {itemErrors.unit_purchase_price_usd.message}
                    </p>
                  )}
                </div>
                <div className="md:col-span-1 flex justify-end pt-6">
                  <button
                    type="button"
                    onClick={() => removeItem(index)}
                    disabled={itemFields.length <= 1}
                    className="p-1.5 rounded hover:bg-red-50 text-red-500 disabled:opacity-30"
                    title="حذف"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        <div className="mt-4 text-left text-sm text-slate-600">
          جمع ارزش محصولات:{' '}
          <span className="font-semibold text-slate-800" dir="ltr">
            ${formatNumber(totalValue)}
          </span>
        </div>
      </Card>

      {/* Section 3: Costs */}
      <Card className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-slate-800">هزینه‌های محموله</h2>
          <button
            type="button"
            onClick={() => appendCost({ ...emptyCost, cost_type: 'shipping' })}
            className="inline-flex items-center gap-1.5 text-sm text-indigo-600 hover:text-indigo-800"
          >
            <Plus className="w-4 h-4" /> افزودن هزینه
          </button>
        </div>

        {costFields.length === 0 && (
          <p className="text-sm text-slate-500 text-center py-4">
            هزینه‌ای ثبت نشده است. هزینه‌های حمل، گمرک و سایر را اینجا وارد کنید.
          </p>
        )}

        <div className="space-y-3">
          {costFields.map((field, index) => {
            const costErrors = errors.costs?.[index];
            return (
              <div
                key={field.id}
                className="grid grid-cols-1 md:grid-cols-12 gap-3 items-start bg-slate-50 rounded-lg p-3"
              >
                <div className="md:col-span-3">
                  <label className="block text-xs text-slate-500 mb-1">نوع هزینه</label>
                  <select {...register(`costs.${index}.cost_type`)} className={inputCls(false)}>
                    {COST_TYPES.map((ct) => (
                      <option key={ct} value={ct}>
                        {COST_TYPE_LABELS[ct]}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="md:col-span-5">
                  <label className="block text-xs text-slate-500 mb-1">توضیح</label>
                  <input
                    type="text"
                    {...register(`costs.${index}.description`)}
                    className={inputCls(false)}
                  />
                </div>
                <div className="md:col-span-3">
                  <label className="block text-xs text-slate-500 mb-1">مبلغ ($)</label>
                  <input
                    type="number"
                    min={0}
                    step="0.01"
                    dir="ltr"
                    {...register(`costs.${index}.amount_usd`, { valueAsNumber: true })}
                    className={inputCls(!!costErrors?.amount_usd)}
                  />
                  {costErrors?.amount_usd && (
                    <p className="mt-1 text-xs text-red-600">{costErrors.amount_usd.message}</p>
                  )}
                </div>
                <div className="md:col-span-1 flex justify-end pt-6">
                  <button
                    type="button"
                    onClick={() => removeCost(index)}
                    className="p-1.5 rounded hover:bg-red-50 text-red-500"
                    title="حذف"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        <div className="mt-4 text-left text-sm text-slate-600">
          جمع هزینه‌ها:{' '}
          <span className="font-semibold text-slate-800" dir="ltr">
            ${formatNumber(totalCosts)}
          </span>
        </div>
      </Card>

      {/* Section 4: Summary */}
      <Card className="mb-6">
        <h2 className="text-lg font-semibold text-slate-800 mb-4">خلاصه</h2>
        <div className="grid grid-cols-3 gap-4 text-sm">
          <div>
            <p className="text-slate-500">جمع ارزش محصولات</p>
            <p className="text-xl font-bold text-slate-800" dir="ltr">
              ${formatNumber(totalValue)}
            </p>
          </div>
          <div>
            <p className="text-slate-500">جمع هزینه‌ها</p>
            <p className="text-xl font-bold text-slate-800" dir="ltr">
              ${formatNumber(totalCosts)}
            </p>
          </div>
          <div>
            <p className="text-slate-500">برآورد کل به ورود</p>
            <p className="text-xl font-bold text-slate-800" dir="ltr">
              ${formatNumber(totalValue + totalCosts)}
            </p>
          </div>
        </div>
      </Card>

      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          onClick={() => void submit()}
          disabled={saveMutation.isPending}
          className="px-5 py-2.5 bg-white border border-indigo-600 text-indigo-600 hover:bg-indigo-50 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
        >
          {saveMutation.isPending ? 'در حال ذخیره...' : 'ذخیره پیش‌نویس'}
        </button>
        <button
          type="button"
          onClick={() => void submitAndFinalize()}
          disabled={saveMutation.isPending}
          className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
        >
          {saveMutation.isPending ? 'در حال ذخیره...' : 'ذخیره و نهایی‌سازی'}
        </button>
        <button
          type="button"
          onClick={() => navigate('/shipments')}
          className="px-5 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-sm font-medium transition-colors"
        >
          انصراف
        </button>
      </div>
    </form>
  );
}