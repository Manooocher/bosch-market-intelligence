import { Suspense } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { ToastProvider } from '../ui/ToastProvider';
import { PageLoadingFallback } from '../ui/PageLoadingFallback';

export function AppLayout() {
  return (
    <ToastProvider>
      <div className="flex h-screen bg-slate-50">
        <Sidebar />
        <div className="flex-1 flex flex-col overflow-hidden">
          <Header />
          <main className="flex-1 overflow-y-auto p-6">
            {/* Suspense around the nested page outlet keeps the shell (sidebar,
                header) visible while a lazy page chunk loads. */}
            <Suspense fallback={<PageLoadingFallback />}>
              <Outlet />
            </Suspense>
          </main>
        </div>
      </div>
    </ToastProvider>
  );
}