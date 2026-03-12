'use client';

/**
 * page.tsx — v5.0 single-page application
 *
 * Wires all components and modals together with SpoolListContext.
 * Modal chain: select spools -> operation -> action -> worker (or metrologia).
 * 30s polling with Page Visibility API + modal pause.
 * CANCELAR dual logic: frontend-only (libre) vs backend (occupied).
 *
 * Multi-select: card click toggles selection, "Procesar" button opens modal chain.
 * Validation: only spools with compatible actions can be selected together.
 *
 * Plan: 04-02-PLAN.md Task 1
 */

import React, { useState, useEffect, useRef, useMemo } from 'react';
import { SpoolListProvider, useSpoolList } from '@/lib/SpoolListContext';
import { useModalStack } from '@/hooks/useModalStack';
import { useNotificationToast } from '@/hooks/useNotificationToast';
import { AddSpoolModal } from '@/components/AddSpoolModal';
import { OperationModal } from '@/components/OperationModal';
import { ActionModal } from '@/components/ActionModal';
import { WorkerModal } from '@/components/WorkerModal';
import { MetrologiaModal } from '@/components/MetrologiaModal';
import { SpoolCardList } from '@/components/SpoolCardList';
import { NotificationToast } from '@/components/NotificationToast';
import { finalizarSpool, cancelarReparacion } from '@/lib/api';
import type { SpoolCardData } from '@/lib/types';
import type { Operation, Action } from '@/lib/spool-state-machine';

// ─── Helper ───────────────────────────────────────────────────────────────────

/**
 * Parses worker ID from ocupado_por format "MR(93)" -> 93.
 * Returns null if format does not match.
 */
function parseWorkerIdFromOcupadoPor(ocupadoPor: string): number | null {
  const match = ocupadoPor.match(/\((\d+)\)$/);
  return match ? parseInt(match[1], 10) : null;
}

/**
 * Returns a compatibility key for a spool.
 * Spools with the same key can be selected together:
 * - "occupied" for spools with ocupado_por (actions: FINALIZAR, PAUSAR, CANCELAR)
 * - "free" for libre spools (actions: INICIAR, CANCELAR)
 */
function getCompatibilityKey(spool: SpoolCardData): string {
  return spool.ocupado_por !== null && spool.ocupado_por !== '' ? 'occupied' : 'free';
}

// ─── HomePage (inner component) ───────────────────────────────────────────────

function HomePage() {
  const { spools, addSpool, removeSpool, refreshAll, refreshSingle } =
    useSpoolList();
  const modalStack = useModalStack();
  const { toasts, enqueue, dismiss } = useNotificationToast();

  // Multi-select state: set of selected spool tags
  const [selectedTags, setSelectedTags] = useState<Set<string>>(new Set());
  const [selectedOperation, setSelectedOperation] =
    useState<Operation | null>(null);
  const [selectedAction, setSelectedAction] = useState<Action | null>(null);

  // Derive selected spool objects from tags (always fresh from spools array)
  const selectedSpools = useMemo(
    () => spools.filter((s) => selectedTags.has(s.tag_spool)),
    [spools, selectedTags]
  );

  // Stable ref for refreshAll — safe for use in setInterval without stale closure
  const refreshAllRef = useRef(refreshAll);
  useEffect(() => {
    refreshAllRef.current = refreshAll;
  }, [refreshAll]);

  // ── 30s Polling ─────────────────────────────────────────────────────────────
  useEffect(() => {
    const intervalId = setInterval(() => {
      if (
        document.visibilityState === 'visible' &&
        modalStack.stack.length === 0
      ) {
        refreshAllRef.current();
      }
    }, 30_000);

    // Also pause polling when tab becomes hidden
    const handleVisibilityChange = () => {
      // Nothing needed here — the interval check handles it
    };
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      clearInterval(intervalId);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [modalStack.stack.length]);

  // ── Clean up stale selections when spools list changes ──────────────────────
  useEffect(() => {
    const currentTags = new Set(spools.map((s) => s.tag_spool));
    setSelectedTags((prev) => {
      const next = new Set<string>();
      prev.forEach((tag) => {
        if (currentTags.has(tag)) next.add(tag);
      });
      return next.size === prev.size ? prev : next;
    });
  }, [spools]);

  // ── Handlers ─────────────────────────────────────────────────────────────────

  const handleAddSpool = async (tag: string) => {
    await addSpool(tag);
    modalStack.pop();
    enqueue(`Spool ${tag} agregado`, 'success');
  };

  /**
   * Toggle spool selection with compatibility validation.
   * Only allows selecting spools with compatible actions (all free or all occupied).
   */
  const handleCardClick = (spool: SpoolCardData) => {
    setSelectedTags((prev) => {
      const next = new Set(prev);
      const tag = spool.tag_spool;

      // If already selected, deselect
      if (next.has(tag)) {
        next.delete(tag);
        return next;
      }

      // Compatibility check: if there are already selected spools,
      // the new spool must have the same compatibility key
      if (next.size > 0) {
        const existingTag = next.values().next().value;
        if (existingTag !== undefined) {
          const existingSpool = spools.find((s) => s.tag_spool === existingTag);
          if (existingSpool) {
            const existingKey = getCompatibilityKey(existingSpool);
            const newKey = getCompatibilityKey(spool);
            if (existingKey !== newKey) {
              enqueue(
                existingKey === 'occupied'
                  ? 'Solo puedes seleccionar spools ocupados juntos'
                  : 'Solo puedes seleccionar spools libres juntos',
                'error'
              );
              return prev;
            }
          }
        }
      }

      next.add(tag);
      return next;
    });
  };

  /**
   * "Procesar" button handler — opens modal chain for selected spools.
   */
  const handleProcesar = () => {
    if (selectedSpools.length === 0) return;

    // For MET, only allow single spool selection
    // (metrologia is a per-spool operation with binary result)
    modalStack.push('operation');
  };

  const handleSelectOperation = (op: Operation) => {
    setSelectedOperation(op);
    modalStack.push('action');
  };

  const handleSelectMet = () => {
    if (selectedSpools.length !== 1) {
      enqueue('Metrologia solo permite un spool a la vez', 'error');
      return;
    }
    modalStack.push('metrologia');
  };

  const handleSelectAction = (action: Action) => {
    setSelectedAction(action);
    modalStack.push('worker');
  };

  const handleWorkerComplete = async () => {
    const tags = selectedSpools.map((s) => s.tag_spool);
    modalStack.clear();

    // Refresh all affected spools
    for (const tag of tags) {
      try {
        await refreshSingle(tag);
      } catch {
        // Spool may have been removed — ignore refresh errors
      }
    }

    const count = tags.length;
    enqueue(
      count === 1
        ? 'Operacion completada'
        : `Operacion completada para ${count} spools`,
      'success'
    );
    setSelectedTags(new Set());
    setSelectedOperation(null);
    setSelectedAction(null);
  };

  const handleMetComplete = async (resultado: 'APROBADO' | 'RECHAZADO') => {
    if (selectedSpools.length === 0) return;
    const spool = selectedSpools[0];
    const tag = spool.tag_spool;
    modalStack.clear();

    if (resultado === 'APROBADO') {
      removeSpool(tag);
      enqueue(`Metrologia aprobada — ${tag}`, 'success');
    } else {
      await refreshSingle(tag);
      enqueue(`Metrologia rechazada — ${tag}`, 'success');
    }

    setSelectedTags(new Set());
    setSelectedOperation(null);
    setSelectedAction(null);
  };

  const handleCancel = async () => {
    if (selectedSpools.length === 0) return;

    // CANCELAR processes each spool individually
    let successCount = 0;
    let errorCount = 0;

    for (const spool of selectedSpools) {
      const tag = spool.tag_spool;
      const { ocupado_por, operacion_actual } = spool;

      // Libre spool — frontend-only removal (STATE-03)
      if (!ocupado_por) {
        removeSpool(tag);
        successCount++;
        continue;
      }

      // Occupied spool — parse worker ID
      const workerId = parseWorkerIdFromOcupadoPor(ocupado_por);
      if (workerId === null) {
        errorCount++;
        continue;
      }

      try {
        if (operacion_actual === 'REPARACION') {
          await cancelarReparacion({ tag_spool: tag, worker_id: workerId });
        } else {
          const operacion = (operacion_actual ?? selectedOperation ?? 'ARM') as
            | 'ARM'
            | 'SOLD';
          await finalizarSpool({
            tag_spool: tag,
            worker_id: workerId,
            operacion,
            selected_unions: [],
          });
        }
        removeSpool(tag);
        successCount++;
      } catch {
        errorCount++;
      }
    }

    modalStack.clear();

    if (errorCount === 0) {
      const msg = successCount === 1
        ? `Spool cancelado`
        : `${successCount} spools cancelados`;
      enqueue(msg, 'success');
    } else {
      enqueue(
        `${successCount} cancelados, ${errorCount} con error`,
        errorCount === selectedSpools.length ? 'error' : 'success'
      );
    }

    setSelectedTags(new Set());
    setSelectedOperation(null);
    setSelectedAction(null);
  };

  const handleModalClose = () => {
    modalStack.pop();
    if (modalStack.stack.length <= 1) {
      // After pop, stack will be empty — reset operation/action selection
      setSelectedOperation(null);
      setSelectedAction(null);
    }
  };

  const handleClearSelection = () => {
    setSelectedTags(new Set());
  };

  // ── Render ───────────────────────────────────────────────────────────────────

  const selectionCount = selectedTags.size;

  return (
    <div className="min-h-screen bg-zeues-navy text-white">
      {/* Header */}
      <header className="p-4 text-center border-b-4 border-white/30">
        <img src="/logos/logo-grisclaro-F8F9FA.svg" alt="KM" className="h-10 mx-auto" />
      </header>

      {/* Add Spool button */}
      <div className="px-4 py-4">
        <button
          onClick={() => modalStack.push('add-spool')}
          className="w-full h-16 bg-zeues-orange text-white font-bold font-mono rounded-none text-lg tracking-widest"
          aria-label="Anadir spool al listado"
        >
          + Anadir Spool
        </button>
      </div>

      {/* Spool card list */}
      <div className="px-4">
        <SpoolCardList
          spools={spools}
          selectedTags={selectedTags}
          onCardClick={handleCardClick}
          onRemove={removeSpool}
        />
      </div>

      {/* Selection action bar — fixed at bottom when spools are selected */}
      {selectionCount > 0 && (
        <div className="fixed bottom-0 left-0 right-0 bg-zeues-navy border-t-4 border-zeues-orange p-4 flex gap-3 z-40">
          <button
            onClick={handleClearSelection}
            className="h-14 px-4 font-mono font-black text-white/60 border-2 border-white/30 hover:text-white hover:border-white/50 transition-colors focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset text-sm"
            aria-label="Deseleccionar todos los spools"
          >
            LIMPIAR
          </button>
          <button
            onClick={handleProcesar}
            className="flex-1 h-14 bg-zeues-orange text-white font-mono font-black text-lg tracking-widest focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset"
            aria-label={`Procesar ${selectionCount} spool${selectionCount > 1 ? 's' : ''} seleccionado${selectionCount > 1 ? 's' : ''}`}
          >
            PROCESAR {selectionCount} SPOOL{selectionCount > 1 ? 'S' : ''}
          </button>
        </div>
      )}

      {/* Bottom padding when selection bar is visible to prevent overlap */}
      {selectionCount > 0 && <div className="h-24" />}

      {/* ── Modals ── */}

      <AddSpoolModal
        isOpen={modalStack.isOpen('add-spool')}
        onAdd={handleAddSpool}
        onClose={handleModalClose}
        alreadyTracked={spools.map((s) => s.tag_spool)}
        isTopOfStack={modalStack.isOpen('add-spool')}
      />

      {selectedSpools.length > 0 && (
        <>
          <OperationModal
            isOpen={modalStack.isOpen('operation')}
            spools={selectedSpools}
            onSelectOperation={handleSelectOperation}
            onSelectMet={handleSelectMet}
            onClose={handleModalClose}
            isTopOfStack={modalStack.isOpen('operation')}
          />

          {selectedOperation && (
            <ActionModal
              isOpen={modalStack.isOpen('action')}
              spools={selectedSpools}
              operation={selectedOperation}
              onSelectAction={handleSelectAction}
              onCancel={handleCancel}
              onClose={handleModalClose}
              isTopOfStack={modalStack.isOpen('action')}
            />
          )}

          {selectedOperation && selectedAction && (
            <WorkerModal
              isOpen={modalStack.isOpen('worker')}
              spools={selectedSpools}
              operation={selectedOperation}
              action={selectedAction}
              onComplete={handleWorkerComplete}
              onClose={handleModalClose}
              isTopOfStack={modalStack.isOpen('worker')}
            />
          )}

          {selectedSpools.length === 1 && (
            <MetrologiaModal
              isOpen={modalStack.isOpen('metrologia')}
              spool={selectedSpools[0]}
              onComplete={handleMetComplete}
              onClose={handleModalClose}
              isTopOfStack={modalStack.isOpen('metrologia')}
            />
          )}
        </>
      )}

      {/* Toast overlay */}
      <NotificationToast toasts={toasts} onDismiss={dismiss} />
    </div>
  );
}

// ─── Page (default export, wraps HomePage in SpoolListProvider) ───────────────

export default function Page() {
  return (
    <SpoolListProvider>
      <HomePage />
    </SpoolListProvider>
  );
}
