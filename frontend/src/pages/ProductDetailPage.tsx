import { useParams } from 'react-router-dom';

export function ProductDetailPage() {
  const { torobId } = useParams<{ torobId: string }>();

  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-800 mb-6">جزئیات محصول</h1>
      <p className="text-sm text-slate-500 mb-4">شناسه: {torobId}</p>
      <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-amber-800">
        🚧 در حال توسعه — محتوای کامل در فاز ۴ اضافه می‌شود
      </div>
    </div>
  );
}