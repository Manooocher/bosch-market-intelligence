import { createContext } from 'react';

/**
 * Actions exposed by the toast system. Obtained via `useToast()` (see
 * hooks/useToast). Each method appends a toast of the given type.
 */
export interface ToastApi {
  /** Show a success toast (emerald). */
  success: (message: string) => void;
  /** Show an error toast (red). */
  error: (message: string) => void;
  /** Show an informational toast (blue). */
  info: (message: string) => void;
}

/**
 * React context carrying the {@link ToastApi}. Provided by {@link ToastProvider}
 * and consumed by `useToast()`. Null when no provider is mounted.
 */
export const ToastContext = createContext<ToastApi | null>(null);