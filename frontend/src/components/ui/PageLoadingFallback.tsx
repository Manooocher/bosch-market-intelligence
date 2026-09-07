import { Loader2 } from 'lucide-react';

/**
 * Full-page loading fallback shown while a lazily-loaded route chunk is being
 * fetched (rendered inside <Suspense>). RTL-aware and consistent with the app
 * design; keeps the shell (sidebar/header) visible during page transitions.
 */
export function PageLoadingFallback() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[50vh] gap-4" dir="rtl">
      <Loader2 className="w-10 h-10 text-indigo-600 animate-spin" />
      <p className="text-sm text-slate-500">در حال بارگذاری صفحه...</p>
    </div>
  );
}