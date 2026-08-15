import { ExternalLink, RefreshCw } from 'lucide-react';
import type { ProductDetail } from '../../api/types';
import { Badge } from '../ui/Badge';
import { getCategoryLabelFromKey } from '../../utils/categories';

interface ProductDetailHeaderProps {
  product: ProductDetail;
}

export function ProductDetailHeader({ product }: ProductDetailHeaderProps) {
  const freshness = product.market_stats?.freshness ?? 'unknown';
  const freshnessBadge =
    freshness === 'fresh' ? (
      <Badge variant="success">تازه</Badge>
    ) : freshness === 'acceptable' ? (
      <Badge variant="warning">قابل قبول</Badge>
    ) : (
      <Badge variant="danger">قدیمی</Badge>
    );

  return (
    <div className="mb-6">
      <h1 className="text-2xl font-bold text-slate-800 mb-3">{product.title ?? '—'}</h1>

      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="info">{product.sku ?? 'بدون SKU'}</Badge>
        <Badge variant="neutral">{getCategoryLabelFromKey(product.category) ?? 'بدون دسته'}</Badge>
        <Badge variant="neutral">{product.market_stats?.seller_count ?? 0} فروشنده</Badge>
        {freshnessBadge}
      </div>

      <div className="mt-3 flex items-center gap-3">
        {product.torob_url && (
          <a
            href={product.torob_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-sm text-indigo-600 hover:text-indigo-800 font-medium"
          >
            <ExternalLink className="w-4 h-4" />
            مشاهده در ترب
          </a>
        )}
        {product.last_fetched_at && (
          <span className="inline-flex items-center gap-1.5 text-xs text-slate-400">
            <RefreshCw className="w-3.5 h-3.5" />
            آخرین به‌روزرسانی: {new Date(product.last_fetched_at).toLocaleDateString('fa-IR')}
          </span>
        )}
      </div>
    </div>
  );
}