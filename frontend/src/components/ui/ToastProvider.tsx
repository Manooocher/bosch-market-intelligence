import { ReactNode, useState, useCallback, useMemo } from 'react';
import { ToastData, ToastType } from './Toast';
import { ToastContainer } from './ToastContainer';
import { ToastContext, ToastApi } from './toastContext';

let toastId = 0;

/**
 * React Context provider for the global toast notification system.
 *
 * Mounted once in {@link AppLayout}. Exposes a stable {@link ToastApi}
 * (success/error/info) to every descendant via {@link ToastContext}, and
 * renders the {@link ToastContainer} so toasts appear fixed in the corner.
 *
 * Consumers call `useToast()` (see hooks/useToast) to get the API. Toasts
 * auto-dismiss after 4s (handled by the Toast component) or via manual close.
 */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastData[]>([]);

  const removeToast = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback((type: ToastType, message: string) => {
    const id = ++toastId;
    setToasts((prev) => [...prev, { id, type, message }]);
  }, []);

  const api = useMemo<ToastApi>(() => ({
    success: (message: string) => addToast('success', message),
    error: (message: string) => addToast('error', message),
    info: (message: string) => addToast('info', message),
  }), [addToast]);

  return (
    <ToastContext.Provider value={api}>
      {children}
      <ToastContainer toasts={toasts} onClose={removeToast} />
    </ToastContext.Provider>
  );
}