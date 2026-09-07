import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { lazy } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ErrorBoundary } from './components/ErrorBoundary';
import { AppLayout } from './components/layout/AppLayout';
import { MarketOverviewPage } from './pages/MarketOverviewPage';
import { ProductsPage } from './pages/ProductsPage';
import { ProductDetailPage } from './pages/ProductDetailPage';
import { MarginsPage } from './pages/MarginsPage';
import { ShipmentsPage } from './pages/ShipmentsPage';
import { ShipmentFormPage } from './pages/ShipmentFormPage';
import { ShipmentDetailPage } from './pages/ShipmentDetailPage';

// DataProbe is a developer-only diagnostics page. Imported dynamically and
// gated behind import.meta.env.DEV so Vite prunes it from the production
// bundle (dev servers still get /_debug/data; prod builds omit it entirely).
// The lazy fallback branch keeps the type a valid JSX component and is itself
// dead-code eliminated by the `false && ...` route guard below in prod.
const DataProbe = import.meta.env.DEV
  ? lazy(() => import('./pages/_debug/DataProbe').then((m) => ({ default: m.DataProbe })))
  : lazy(() => Promise.resolve({ default: () => null }));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60 * 60 * 1000,  // 1 hour (data updates every 4 days)
      gcTime: 4 * 60 * 60 * 1000, // 4 hours
      refetchOnWindowFocus: false,
      refetchOnReconnect: false,
    },
  },
});

export default function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Routes>
            {import.meta.env.DEV && <Route path="/_debug/data" element={<DataProbe />} />}
            <Route path="/" element={<AppLayout />}>
              <Route index element={<MarketOverviewPage />} />
              <Route path="products" element={<ProductsPage />} />
              <Route path="products/:torobId" element={<ProductDetailPage />} />
              <Route path="margins" element={<MarginsPage />} />
              <Route path="shipments" element={<ShipmentsPage />} />
              <Route path="shipments/new" element={<ShipmentFormPage />} />
              <Route path="shipments/:id" element={<ShipmentDetailPage />} />
              <Route path="shipments/:id/edit" element={<ShipmentFormPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}