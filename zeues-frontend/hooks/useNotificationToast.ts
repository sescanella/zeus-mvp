import { useState, useCallback, useRef } from 'react';
import { hapticSuccess, hapticError } from '@/lib/haptic';

export type ToastType = 'success' | 'error';

export interface Toast {
  id: string;
  message: string;
  type: ToastType;
}

export interface UseNotificationToastReturn {
  toasts: Toast[];
  enqueue: (message: string, type: ToastType) => void;
  dismiss: (id: string) => void;
}

const AUTO_DISMISS_MS = 4000;

/**
 * Manages a queue of notification toasts.
 * Multiple toasts can coexist and are independently timed.
 * SUCCESS toasts auto-dismiss after 4 seconds.
 * ERROR toasts persist until manually dismissed by the user.
 *
 * Usage:
 *   enqueue('Spool taken successfully', 'success')  → shows success toast, auto-dismisses
 *   enqueue('Connection error', 'error')             → shows error toast, persists
 *   dismiss(id)                                      → removes toast immediately
 */
export function useNotificationToast(): UseNotificationToastReturn {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const counterRef = useRef(0);

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const enqueue = useCallback(
    (message: string, type: ToastType) => {
      const id = `toast-${Date.now()}-${counterRef.current++}`;
      const toast: Toast = { id, message, type };

      setToasts((prev) => [...prev, toast]);

      if (type === 'success') {
        hapticSuccess();
      } else {
        hapticError();
      }

      if (type === 'success') {
        setTimeout(() => {
          setToasts((prev) => prev.filter((t) => t.id !== id));
        }, AUTO_DISMISS_MS);
      }
    },
    []
  );

  return { toasts, enqueue, dismiss };
}
