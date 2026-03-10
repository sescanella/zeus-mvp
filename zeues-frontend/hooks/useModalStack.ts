import { useState, useCallback } from 'react';

export type ModalId = 'add-spool' | 'operation' | 'action' | 'worker' | 'metrologia';

export interface UseModalStackReturn {
  stack: ModalId[];
  current: ModalId | null;
  push: (modal: ModalId) => void;
  pop: () => void;
  clear: () => void;
  isOpen: (modal: ModalId) => boolean;
}

/**
 * Manages a stack of modal IDs for multi-step modal navigation.
 * The top of the stack (last element) is the currently visible modal.
 *
 * Usage:
 *   push('operation')  → opens operation modal
 *   push('action')     → opens action modal on top of operation
 *   pop()              → returns to operation modal
 *   clear()            → closes all modals
 */
export function useModalStack(): UseModalStackReturn {
  const [stack, setStack] = useState<ModalId[]>([]);

  const push = useCallback((modal: ModalId) => {
    setStack((prev) => [...prev, modal]);
  }, []);

  const pop = useCallback(() => {
    setStack((prev) => prev.slice(0, -1));
  }, []);

  const clear = useCallback(() => {
    setStack([]);
  }, []);

  const isOpen = useCallback(
    (modal: ModalId) => stack.length > 0 && stack[stack.length - 1] === modal,
    [stack]
  );

  const current: ModalId | null = stack[stack.length - 1] ?? null;

  return { stack, current, push, pop, clear, isOpen };
}
