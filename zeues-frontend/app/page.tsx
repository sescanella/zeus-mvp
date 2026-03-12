'use client';

/**
 * page.tsx — v5.0 single-page application
 *
 * Wires all components and modals together with SpoolListContext.
 * Modal chain: click card -> operation -> action -> worker (or metrologia).
 * 30s polling with Page Visibility API + modal pause.
 * CANCELAR dual logic: frontend-only (libre) vs backend (occupied).
 *
 * Single-spool processing: card click opens modal chain for ONE spool.
 * Multi-add: AddSpoolModal allows adding multiple spools before closing.
 *
 * Plan: 04-02-PLAN.md Task 1
 */

import React, { useState, useEffect, useRef } from 'react';
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
import {
  finalizarSpool,
  cancelarReparacion,
  pausarReparacion,
  completarReparacion,
} from '@/lib/api';
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

// ─── HomePage (inner component) ───────────────────────────────────────────────

function HomePage() {
  const { spools, addSpool, removeSpool, refreshAll, refreshSingle } =
    useSpoolList();
  const modalStack = useModalStack();
  const { toasts, enqueue, dismiss } = useNotificationToast();

  // Single spool selection for processing
  const [selectedSpool, setSelectedSpool] = useState<SpoolCardData | null>(null);
  const [selectedOperation, setSelectedOperation] =
    useState<Operation | null>(null);
  const [selectedAction, setSelectedAction] = useState<Action | null>(null);
  const [apiLoading, setApiLoading] = useState(false);

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

  // ── Handlers ─────────────────────────────────────────────────────────────────

  const handleAddSpool = async (tag: string) => {
    await addSpool(tag);
    enqueue(`Spool ${tag} agregado`, 'success');
  };

  const handleAddSpoolClose = () => {
    modalStack.pop();
  };

  /**
   * Card click opens the modal chain for a single spool.
   */
  const handleCardClick = (spool: SpoolCardData) => {
    setSelectedSpool(spool);
    modalStack.push('operation');
  };

  const handleSelectOperation = (op: Operation) => {
    setSelectedOperation(op);
    modalStack.push('action');
  };

  const handleSelectMet = () => {
    modalStack.push('metrologia');
  };

  /**
   * Executes FINALIZAR or PAUSAR API call directly using the worker from ocupado_por.
   * Skips the WorkerModal since the worker is already known.
   */
  const executeDirectAction = async (
    action: 'FINALIZAR' | 'PAUSAR',
    spool: SpoolCardData,
    operation: Operation,
    workerId: number,
  ) => {
    const tag = spool.tag_spool;

    if (operation === 'ARM' || operation === 'SOLD') {
      const actionOverride: 'COMPLETAR' | 'PAUSAR' =
        action === 'FINALIZAR' ? 'COMPLETAR' : 'PAUSAR';
      await finalizarSpool({
        tag_spool: tag,
        worker_id: workerId,
        operacion: operation as 'ARM' | 'SOLD',
        action_override: actionOverride,
      });
    } else if (operation === 'REP') {
      if (action === 'FINALIZAR') {
        await completarReparacion({ tag_spool: tag, worker_id: workerId });
      } else {
        await pausarReparacion({ tag_spool: tag, worker_id: workerId });
      }
    }
  };

  const handleSelectAction = async (action: Action) => {
    setSelectedAction(action);

    // INICIAR: show WorkerModal (user picks the worker)
    if (action === 'INICIAR') {
      modalStack.push('worker');
      return;
    }

    // FINALIZAR / PAUSAR: use the worker already assigned in ocupado_por
    if (
      (action === 'FINALIZAR' || action === 'PAUSAR') &&
      selectedSpool &&
      selectedOperation
    ) {
      const ocupadoPor = selectedSpool.ocupado_por;
      if (!ocupadoPor) {
        enqueue('Error: spool no tiene trabajador asignado', 'error');
        return;
      }

      const workerId = parseWorkerIdFromOcupadoPor(ocupadoPor);
      if (workerId === null) {
        enqueue('Error: formato de trabajador invalido', 'error');
        return;
      }

      setApiLoading(true);
      try {
        await executeDirectAction(action, selectedSpool, selectedOperation, workerId);
        const tag = selectedSpool.tag_spool;
        modalStack.clear();

        try {
          await refreshSingle(tag);
        } catch {
          // Spool may have been removed — ignore refresh errors
        }

        enqueue('Operacion completada', 'success');
      } catch (err: unknown) {
        const message =
          err instanceof Error ? err.message : 'Error al ejecutar la operacion';
        enqueue(message, 'error');
      } finally {
        setApiLoading(false);
        setSelectedSpool(null);
        setSelectedOperation(null);
        setSelectedAction(null);
      }
    }
  };

  const handleWorkerComplete = async () => {
    if (!selectedSpool) return;
    const tag = selectedSpool.tag_spool;
    modalStack.clear();

    try {
      await refreshSingle(tag);
    } catch {
      // Spool may have been removed — ignore refresh errors
    }

    enqueue('Operacion completada', 'success');
    setSelectedSpool(null);
    setSelectedOperation(null);
    setSelectedAction(null);
  };

  const handleMetComplete = async (resultado: 'APROBADO' | 'RECHAZADO') => {
    if (!selectedSpool) return;
    const tag = selectedSpool.tag_spool;
    modalStack.clear();

    if (resultado === 'APROBADO') {
      removeSpool(tag);
      enqueue(`Metrologia aprobada — ${tag}`, 'success');
    } else {
      await refreshSingle(tag);
      enqueue(`Metrologia rechazada — ${tag}`, 'success');
    }

    setSelectedSpool(null);
    setSelectedOperation(null);
    setSelectedAction(null);
  };

  const handleCancel = async () => {
    if (!selectedSpool) return;

    const { tag_spool: tag, ocupado_por, operacion_actual } = selectedSpool;

    // Libre spool — frontend-only removal (STATE-03)
    if (!ocupado_por) {
      removeSpool(tag);
      modalStack.clear();
      enqueue('Spool cancelado', 'success');
      setSelectedSpool(null);
      setSelectedOperation(null);
      setSelectedAction(null);
      return;
    }

    // Occupied spool — parse worker ID
    const workerId = parseWorkerIdFromOcupadoPor(ocupado_por);
    if (workerId === null) {
      modalStack.clear();
      enqueue('Error: formato de trabajador invalido', 'error');
      setSelectedSpool(null);
      setSelectedOperation(null);
      setSelectedAction(null);
      return;
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
      modalStack.clear();
      enqueue('Spool cancelado', 'success');
    } catch {
      modalStack.clear();
      enqueue('Error al cancelar spool', 'error');
    }

    setSelectedSpool(null);
    setSelectedOperation(null);
    setSelectedAction(null);
  };

  const handleModalClose = () => {
    modalStack.pop();
    if (modalStack.stack.length <= 1) {
      // After pop, stack will be empty — reset operation/action selection
      setSelectedOperation(null);
      setSelectedAction(null);
      setSelectedSpool(null);
    }
  };

  // ── Render ───────────────────────────────────────────────────────────────────

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
          onCardClick={handleCardClick}
          onRemove={removeSpool}
        />
      </div>

      {/* ── Modals ── */}

      <AddSpoolModal
        isOpen={modalStack.isOpen('add-spool')}
        onAdd={handleAddSpool}
        onClose={handleAddSpoolClose}
        alreadyTracked={spools.map((s) => s.tag_spool)}
        isTopOfStack={modalStack.isOpen('add-spool')}
      />

      {selectedSpool && (
        <>
          <OperationModal
            isOpen={modalStack.isOpen('operation')}
            spool={selectedSpool}
            onSelectOperation={handleSelectOperation}
            onSelectMet={handleSelectMet}
            onClose={handleModalClose}
            isTopOfStack={modalStack.isOpen('operation')}
          />

          {selectedOperation && (
            <ActionModal
              isOpen={modalStack.isOpen('action')}
              spool={selectedSpool}
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
              spool={selectedSpool}
              operation={selectedOperation}
              action={selectedAction}
              onComplete={handleWorkerComplete}
              onClose={handleModalClose}
              isTopOfStack={modalStack.isOpen('worker')}
            />
          )}

          <MetrologiaModal
            isOpen={modalStack.isOpen('metrologia')}
            spool={selectedSpool}
            onComplete={handleMetComplete}
            onClose={handleModalClose}
            isTopOfStack={modalStack.isOpen('metrologia')}
          />
        </>
      )}

      {/* Loading overlay for direct API calls (FINALIZAR/PAUSAR without WorkerModal) */}
      {apiLoading && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
          role="status"
          aria-label="Procesando operacion"
        >
          <div className="flex flex-col items-center gap-3 bg-zeues-navy border-4 border-white p-8">
            <div className="w-8 h-8 border-3 border-white/30 border-t-white rounded-full animate-spin" />
            <p className="text-white font-mono font-black text-sm tracking-widest">
              PROCESANDO...
            </p>
          </div>
        </div>
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
