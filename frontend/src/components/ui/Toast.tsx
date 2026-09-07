import { useEffect } from 'react';
import { CheckCircle2, XCircle, Info, X } from 'lucide-react';

/** Toast visual variant. */
export type ToastType = 'success' | 'error' | 'info';

/** A single toast notification. */
export interface ToastData {
  id: number;
  type: ToastType;
  message: string;
}

interface ToastProps {
  toast: ToastData;
  onClose: (id: number) => void;
}

/**
 * A single auto-dismissing toast notification.
 *
 * Variants: success (emerald), error (red), info (blue). Auto-dismisses after
 * 4 seconds via an internal timeout; can also be dismissed manually with the
 * close button. Rendered with RTL layout.
 *
 * @param toast   the toast data to display
 * @param onClose callback invoked with the toast id when it should be removed
 */
export function Toast({ toast, onClose }: ToastProps) {
  useEffect(() => {
    const timer = setTimeout(() => onClose(toast.id), 4000);
    return () => clearTimeout(timer);
  }, [toast.id, onClose]);

  const icons = {
    success: <CheckCircle2 className="w-5 h-5 text-emerald-500" />,
    error: <XCircle className="w-5 h-5 text-red-500" />,
    info: <Info className="w-5 h-5 text-blue-500" />,
  };

  const bgColors = {
    success: 'bg-emerald-50 border-emerald-200',
    error: 'bg-red-50 border-red-200',
    info: 'bg-blue-50 border-blue-200',
  };

  return (
    <div
      className={`flex items-center gap-3 p-4 rounded-lg shadow-lg border ${bgColors[toast.type]} animate-slide-in`}
      dir="rtl"
      role="status"
    >
      {icons[toast.type]}
      <p className="text-sm text-slate-700 flex-1">{toast.message}</p>
      <button
        onClick={() => onClose(toast.id)}
        className="text-slate-400 hover:text-slate-600"
        aria-label="بستن اعلان"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}