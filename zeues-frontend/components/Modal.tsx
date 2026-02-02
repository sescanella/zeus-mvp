'use client';

import React, { useEffect } from 'react';
import { createPortal } from 'react-dom';

interface ModalProps {
  isOpen: boolean;
  onClose?: () => void;
  onBackdropClick?: (() => void) | null;
  children: React.ReactNode;
  className?: string;
}

export function Modal({ isOpen, onClose, onBackdropClick, children, className = '' }: ModalProps) {
  const [mounted, setMounted] = React.useState(false);

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

  // ESC key handler
  useEffect(() => {
    if (!isOpen || !onClose) return;

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  // Don't render anything if not open or not mounted (SSR)
  if (!isOpen || !mounted) return null;

  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    // Only handle clicks on the backdrop itself, not content
    if (e.target === e.currentTarget) {
      if (onBackdropClick === null) {
        // null means backdrop clicks are disabled
        return;
      }
      if (onBackdropClick) {
        onBackdropClick();
      } else if (onClose) {
        onClose();
      }
    }
  };

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      onClick={handleBackdropClick}
    >
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/50 transition-opacity duration-200" />

      {/* Modal content */}
      <div
        className={`
          relative bg-white rounded-lg shadow-xl
          max-w-md w-full p-6
          transition-all duration-200
          ${className}
        `}
      >
        {children}
      </div>
    </div>,
    document.body
  );
}
