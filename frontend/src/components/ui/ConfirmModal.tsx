import { useEffect, useRef } from 'react';
import { AlertTriangle, X } from 'lucide-react';

interface ConfirmModalProps {
  isOpen: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: 'danger' | 'default';
  isLoading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

/**
 * Reusable confirmation dialog that replaces the native `window.confirm`.
 *
 * RTL-aware, Tailwind-styled, and accessibile:
 * - Focus is moved to the confirm button on open.

 * - Closes on Escape (unless loading) or on backdrop click (unless loading).
 * - aria-modal / aria-labelledby / aria-describedby for screen readers.

 * @param isOpen        whether the modal is visible
 * @param title          Persian heading
 * @param message        Persian body text
 * @param confirmLabel   confirm button label (default «تأیید»)
 * @param cancelLabel    cancel button label (default «انصراف»)
 * @param variant         'danger' (red) or 'default' (indigo)
 * @param isLoading        whether a mutation is in flight (disables both buttons)
 * @param onConfirm       callback fired on confirm
 * @param onCancel         callback fired on cancel / close
 */
export function ConfirmModal({
  isOpen,
  title,
  message,
  confirmLabel = 'تأیید',
  cancelLabel = 'انصراف',
  variant = 'default',
  isLoading = false,
  onConfirm,
  onCancel,
}: ConfirmModalProps) {
  const confirmButtonRef = useRef<HTMLButtonElement>(null);

  // Focus them confirm button when the modal opens.

  useEffect(() => {
    if (isOpen && confirmButtonRef.current) {
      confirmButtonRef.current.focus();
    }
  }, [isOpen]);

  // Close on Escape.

  useEffect(() => {
    if (!isOpen) return;
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !isLoading) {
        onCancel();
      }
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, isLoading, onCancel]);

  // Close on backdrop click (when the click target is the overlay itself).
  const handleOverlayClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget && !isLoading) {
      onCancel();
    }
  };

  if (!isOpen) return null;

  const variantClasses = {
    danger: {
      icon: 'text-red-500 bg-red-100',
      confirm: 'bg-red-600 hover:bg-red-700 focus:ring-red-500',
    },
    default: {
      icon: 'text-blue-500 bg-blue-100',
      confirm: 'bg-indigo-600 hover:bg-indigo-700 focus:ring-indigo-500',
    },
  } as const;
  const classes = variantClasses[variant];

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
      onClick={handleOverlayClick}
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-modal-title"
      aria-describedby="confirm-modal-message"
    >
      <div
        className="bg-white rounded-xl shadow-2xl max-w-md w-full p-6 animate-slide-in"
        dir="rtl"
      >
        <div className="flex items-start gap-4 mb-4">
          <div className={`p-3 rounded-full ${classes.icon}`}>
            <AlertTriangle className="w-6 h-6" />
          </div>
          <div className="flex-1">
            <h2 id="confirm-modal-title" className="text-lg font-semibold text-slate-800">
              {title}
            </h2>
            <p id="confirm-modal-message" className="text-sm text-slate-600 mt-2">
              {message}
            </p>
          </div>
          <button
            onClick={onCancel}
            disabled={isLoading}
            className="p-1 text-slate-400 hover:text-slate-600 rounded-lg transition-colors disabled:opacity-50"
            aria-label="بستن"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="flex gap-3 justify-end">
          <button
            onClick={onCancel}
            disabled={isLoading}
            className="px-4 py-2 text-sm font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors disabled:opacity-50"
          >
            {cancelLabel}
          </button>
          <button
            ref={confirmButtonRef}
            onClick={onConfirm}
            disabled={isLoading}
            className={`px-4 py-2 text-sm font-medium text-white rounded-lg transition-colors disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-offset-2 ${classes.confirm}`}
          >
            {isLoading ? 'در حال پردازش...' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}