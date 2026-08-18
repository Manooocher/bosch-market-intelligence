import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppLayout } from './components/layout/AppLayout';
import { MarketOverviewPage } from './pages/MarketOverviewPage';
import { ProductsPage } from './pages/ProductsPage';
import { ProductDetailPage } from './pages/ProductDetailPage';
import { MarginsPage } from './pages/MarginsPage';
import { ShipmentsPage } from './pages/ShipmentsPage';
import { ShipmentFormPage } from './pages/ShipmentFormPage';
import { ShipmentDetailPage } from './pages/ShipmentDetailPage';
import { DataProbe } from './pages/_debug/DataProbe';

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
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/_debug/data" element={<DataProbe />} />
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
  );
}