import { Suspense,useEffect,useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { ToastProvider } from '../ui/ToastProvider';
import { PageLoadingFallback } from '../ui/PageLoadingFallback';

export function AppLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();

  // Close the mobile drawer cuando the route changes (on navigation clicks).
  useEffect(() => {
    setSidebarOpen(false);
  }, [location.pathname]);

  // Close the drawer on Escape key.
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setSidebarOpen(false);
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, []);

  return (
    <ToastProvider>
      <div className="flex h-screen bg-slate-50 overflow-hidden">
        {/* Semi-transparent overlay behind the drawer — mobile only. */}
        {sidebarOpen && (
          <div
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 md:hidden"
            onClick={() => setSidebarOpen(false)}
            aria-hidden="true"
          />
        )}

        {/* Sidebar — static on md+, slide-in drawer on mobile. */}
        <aside
          className={`
            fixed md:static inset-y-0 right-0 z-50
            w-64 bg-white border-l border-slate-200
            transform transition-transform duration-300 ease-in-out
            ${sidebarOpen ? 'translate-x-0' : 'translate-x-[100%] md:translate-x-0'}
          `}
          aria-label="منوی ناوبری"
          role="navigation"
        >
          <Sidebar onClose={() => setSidebarOpen(false)} />
        </aside>

        <div className="flex-1 flex flex-col overflow-hidden">
          <Header onMenuClick={() => setSidebarOpen(true)} />
          <main className="flex-1 overflow-y-auto p-4 md:p-6">
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