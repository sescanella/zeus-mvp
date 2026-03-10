import { useState, useCallback, useRef } from 'react';

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
 * Manages a queue of notification toasts with auto-dismiss after 4 seconds.
 * Multiple toasts can coexist and are independently timed.
 *
 * Usage:
 *   enqueue('Spool taken successfully', 'success')  → shows success toast
 *   enqueue('Connection error', 'error')             → shows error toast
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

      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, AUTO_DISMISS_MS);
    },
    []
  );

  return { toasts, enqueue, dismiss };
}
