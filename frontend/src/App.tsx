import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useProducts } from './hooks/useProducts';
import { formatPrice } from './utils/format';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60 * 60 * 1000,
      gcTime: 4 * 60 * 60 * 1000,
      refetchOnWindowFocus: false,
    },
  },
});

// Phase-1 placeholder: proves the API + adapter layer end-to-end through the
// Vite dev proxy. Replaced by routed pages in Phase 2.
function Phase1Probe() {
  const { data, isLoading, error } = useProducts({ page: 1, per_page: 10 });
  const first = data?.items[0];

  return (
    <div style={{ padding: 24, fontFamily: 'Vazirmatn, sans-serif', direction: 'rtl' }}>
      <h1>Torob Intelligence — Phase 1 API Probe</h1>
      {isLoading && <p>درحال بارگذاری…</p>}
      {error && <p style={{ color: 'red' }}>خطا: {String(error)}</p>}
      {data && (
        <ul>
          <li>تعداد کل محصولات (mapped): {data.total}</li>
          <li>صفحه‌ها: {data.pages}</li>
          {first && (
            <>
              <li>SKU: {first.sku}</li>
              <li>دسته‌بندی (inferred): {first.category}</li>
              <li>آدرس توروب: {first.torob_url}</li>
              <li>قیمت کمینه: {formatPrice(first.min_price_rial)} ریال</li>
              <li>تازگی (ساعت): {first.freshness_hours}</li>
              <li>حاشیه سود %: {first.margin_vs_min_pct}</li>
            </>
          )}
        </ul>
      )}
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Phase1Probe />
    </QueryClientProvider>
  );
}
