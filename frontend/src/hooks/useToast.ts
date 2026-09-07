import { useContext } from 'react';
import { ToastContext, ToastApi } from '../components/ui/toastContext';

/**
 * Access the toast API. Must be used inside a <ToastProvider> (provided by
 * AppLayout). Throws otherwise so misuse is caught at render time.
 */
export function useToast(): ToastApi {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return ctx;
}