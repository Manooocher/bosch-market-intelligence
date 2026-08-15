import { useParams, useNavigate } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import { useProductDetail } from '../hooks/useProductDetail';
import { useSellers } from '../hooks/useSellers';
import { ProductDetailHeader } from '../components/products/ProductDetailHeader';
import { PriceComparisonCards } from '../components/products/PriceComparisonCards';
import { SellerTable } from '../components/sellers/SellerTable';
import { PriceDistribution } from '../components/charts/PriceDistribution';
import { ErrorState } from '../components/ui/ErrorState';
import { Card } from '../components/ui/Card';

export function ProductDetailPage() {
  const { torobId } = useParams<{ torobId: string }>();
  const navigate = useNavigate();

  const {
    data: product,
    isLoading: productLoading,
    error: productError,
    refetch: refetchProduct,
  } = useProductDetail(torobId ?? '');

  const {
    data: sellers,
    isLoading: sellersLoading,
  } = useSellers(torobId ?? '');

  if (!torobId) {
    return (
      <div>
        <h1 className="text-2xl font-bold text-slate-800 mb-6">جزئیات محصول</h1>
        <ErrorState message="شناسه محصول نامعتبر است." />
      </div>
    );
  }

  if (productError) {
    return (
      <div>
        <button
          onClick={() => navigate('/products')}
          className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-indigo-600 mb-4"
        >
          <ArrowRight className="w-4 h-4" /> بازگشت به محصولات
        </button>
        <ErrorState
          message={`خطا در دریافت محصول: ${String(productError)}`}
          onRetry={() => refetchProduct()}
        />
      </div>
    );
  }

  if (productLoading || !product) {
    return (
      <div>
        <div className="h-8 w-2/3 bg-slate-200 rounded animate-pulse mb-4" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="h-28 bg-slate-100 rounded-xl animate-pulse" />
          ))}
        </div>
        <div className="h-64 bg-slate-100 rounded-xl animate-pulse" />
      </div>
    );
  }

  return (
    <div>
      <button
        onClick={() => navigate('/products')}
        className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-indigo-600 mb-4"
      >
        <ArrowRight className="w-4 h-4" /> بازگشت به محصولات
      </button>

      <ProductDetailHeader product={product} />
      <PriceComparisonCards product={product} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="mb-6 lg:mb-0">
          <h2 className="text-lg font-semibold text-slate-800 mb-4">فروشندگان</h2>
          <SellerTable sellers={sellers ?? []} isLoading={sellersLoading} />
        </Card>

        <Card>
          <h2 className="text-lg font-semibold text-slate-800 mb-4">توزیع قیمت فروشندگان</h2>
          <PriceDistribution
            sellers={sellers ?? []}
            nabkadePriceRial={
              product.margin_vs_min_rial != null && product.market_stats?.min_price_rial != null
                ? (product.margin_vs_min_rial + Math.floor(product.market_stats.min_price_rial / 10)) * 10
                : null
            }
          />
        </Card>
      </div>
    </div>
  );
}