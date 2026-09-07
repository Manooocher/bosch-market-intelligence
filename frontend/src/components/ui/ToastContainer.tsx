import { Toast, ToastData } from './Toast';

interface ToastContainerProps {
  toasts: ToastData[];
  onClose: (id: number) => void;
}

/**
 * Fixed-position stack that renders all active toasts in the top-right corner.
 * Managed by {@link ToastProvider}; pages normally never render this directly.
 *
 * @param toasts  the active toasts (newest appended last)
 * @param onClose callback to remove a toast by id (also fires on auto-dismiss)
 */
export function ToastContainer({ toasts, onClose }: ToastContainerProps) {
  return (
    <div className="fixed top-4 right-4 z-50 space-y-2 max-w-sm" dir="rtl">
      {toasts.map((toast) => (
        <Toast key={toast.id} toast={toast} onClose={onClose} />
      ))}
    </div>
  );
}