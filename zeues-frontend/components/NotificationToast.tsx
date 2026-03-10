'use client';

import { CheckCircle, AlertCircle, X } from 'lucide-react';
import type { Toast } from '@/hooks/useNotificationToast';

interface NotificationToastProps {
  toasts: Toast[];
  onDismiss: (id: string) => void;
}

/**
 * Renders a stacked queue of notification toasts with ARIA live region.
 *
 * The outer container is always in the DOM so the aria-live region is
 * registered with screen readers before the first toast arrives.
 *
 * Success toasts: green-400 border + CheckCircle icon
 * Error toasts:   red-400 border + AlertCircle icon
 *
 * Plan: 02-01-PLAN.md Task 1
 */
export function NotificationToast({ toasts, onDismiss }: NotificationToastProps) {
  return (
    <div
      aria-live="polite"
      aria-atomic="false"
      className="fixed top-4 right-4 z-[100] flex flex-col gap-2 pointer-events-none"
    >
      {toasts.map((toast) => {
        const isSuccess = toast.type === 'success';
        const borderClass = isSuccess ? 'border-green-400' : 'border-red-400';
        const Icon = isSuccess ? CheckCircle : AlertCircle;
        const iconClass = isSuccess ? 'text-green-400' : 'text-red-400';

        return (
          <div
            key={toast.id}
            role="alert"
            className={`pointer-events-auto bg-zeues-navy border-4 ${borderClass} rounded-none px-4 py-3 flex items-center gap-3 min-w-[280px] max-w-sm font-mono font-black text-sm text-white shadow-lg`}
          >
            <Icon className={`${iconClass} shrink-0`} size={20} aria-hidden="true" />
            <span className="flex-1">{toast.message}</span>
            <button
              onClick={() => onDismiss(toast.id)}
              aria-label="Cerrar notificacion"
              className="shrink-0 text-white/70 hover:text-white focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset rounded-sm p-0.5"
            >
              <X size={16} aria-hidden="true" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
