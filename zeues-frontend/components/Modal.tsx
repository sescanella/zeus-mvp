'use client';

import React, { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';

interface ModalProps {
  isOpen: boolean;
  onClose?: () => void;
  /**
   * Optional callback for backdrop clicks. Opt-in:
   * omitir (o pasar null) deshabilita el cierre por click-fuera (default seguro).
   * Pasar `() => onClose()` habilita click-outside-to-close.
   */
  onBackdropClick?: (() => void) | null;
  children: React.ReactNode;
  className?: string;
  ariaLabel?: string;
  isTopOfStack?: boolean;
}

const FOCUSABLE_SELECTORS =
  'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

export function Modal({ isOpen, onClose, onBackdropClick, children, className = '', ariaLabel, isTopOfStack = true }: ModalProps) {
  const [mounted, setMounted] = React.useState(false);
  const dialogRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<Element | null>(null);

  // Handle SSR - only render portal after mount
  useEffect(() => {
    setMounted(true);
    return () => setMounted(false);
  }, []);

  // Prevent body scroll when modal is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }

    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  // Save previously focused element and auto-focus first element on open.
  // Restore focus to saved element on close.
  useEffect(() => {
    if (isOpen) {
      previousFocusRef.current = document.activeElement;

      const timer = setTimeout(() => {
        const dialog = dialogRef.current;
        if (!dialog) return;
        const focusable = dialog.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTORS);
        if (focusable.length > 0) {
          focusable[0].focus();
        } else {
          dialog.focus();
        }
      }, 50);

      return () => clearTimeout(timer);
    } else {
      const saved = previousFocusRef.current;
      if (saved && 'focus' in saved) {
        (saved as HTMLElement).focus();
      }
      previousFocusRef.current = null;
    }
  }, [isOpen]);

  // ESC key handler + focus trap
  useEffect(() => {
    if (!isOpen) return;
    if (isTopOfStack === false) return; // not top of stack — ignore keyboard events

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        if (onClose) onClose();
        return;
      }

      if (event.key === 'Tab') {
        const dialog = dialogRef.current;
        if (!dialog) return;

        const focusable = Array.from(
          dialog.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTORS)
        ).filter((el) => !el.hasAttribute('disabled'));

        if (focusable.length === 0) {
          event.preventDefault();
          return;
        }

        const first = focusable[0];
        const last = focusable[focusable.length - 1];

        if (event.shiftKey) {
          // Shift+Tab: if focus is on first element, wrap to last
          if (document.activeElement === first) {
            event.preventDefault();
            last.focus();
          }
        } else {
          // Tab: if focus is on last element, wrap to first
          if (document.activeElement === last) {
            event.preventDefault();
            first.focus();
          }
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose, isTopOfStack]);

  // Don't render anything if not open or not mounted (SSR)
  if (!isOpen || !mounted) return null;

  const hasCustomMaxH = className.includes('max-h-');

  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target !== e.currentTarget) return;
    // Opt-in: solo cierra si el caller pasa explícitamente una función.
    // undefined o null = ignorar backdrop click (default).
    if (typeof onBackdropClick === 'function') {
      onBackdropClick();
    }
  };

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      onClick={handleBackdropClick}
    >
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/50 transition-opacity duration-200 pointer-events-none" />

      {/* Modal content */}
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label={ariaLabel}
        tabIndex={-1}
        className={`
          relative rounded-none shadow-xl
          w-[92vw] max-w-md md:max-w-xl ${hasCustomMaxH ? '' : 'max-h-[90vh]'} overflow-y-auto p-6
          transition-all duration-200
          focus:outline-none
          ${className}
        `}
      >
        {children}
      </div>
    </div>,
    document.body
  );
}
