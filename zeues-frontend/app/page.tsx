'use client';

/**
 * page.tsx — v5.0 single-page application
 *
 * Wires all components and modals together with SpoolListContext.
 * Modal chain: add-spool -> operation -> action -> worker (or metrologia).
 * 30s polling with Page Visibility API + modal pause.
 * CANCELAR dual logic: frontend-only (libre) vs backend (occupied).
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

// ─── HomePage (inner component) ───────────────────────────────────────────────

function HomePage() {
  const { spools, addSpool, removeSpool, refreshAll, refreshSingle } =
    useSpoolList();
  const modalStack = useModalStack();
  const { toasts, enqueue, dismiss } = useNotificationToast();

  // Selected spool/operation/action state for modal chain
  const [selectedSpool, setSelectedSpool] = useState<SpoolCardData | null>(
    null
  );
  const [selectedOperation, setSelectedOperation] =
    useState<Operation | null>(null);
  const [selectedAction, setSelectedAction] = useState<Action | null>(null);

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
    modalStack.pop();
    enqueue(`Spool ${tag} agregado`, 'success');
  };

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

  const handleSelectAction = (action: Action) => {
    setSelectedAction(action);
    modalStack.push('worker');
  };

  const handleWorkerComplete = async () => {
    if (!selectedSpool) return;
    const tag = selectedSpool.tag_spool;
    modalStack.clear();
    await refreshSingle(tag);
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
    const tag = selectedSpool.tag_spool;
    const { ocupado_por, operacion_actual } = selectedSpool;

    // Libre spool — frontend-only removal (STATE-03)
    if (!ocupado_por) {
      removeSpool(tag);
      modalStack.clear();
      setSelectedSpool(null);
      setSelectedOperation(null);
      setSelectedAction(null);
      return;
    }

    // Occupied spool — parse worker ID
    const workerId = parseWorkerIdFromOcupadoPor(ocupado_por);
    if (workerId === null) {
      enqueue('Error: no se pudo determinar el trabajador', 'error');
      return;
    }

    try {
      if (operacion_actual === 'REPARACION') {
        await cancelarReparacion({ tag_spool: tag, worker_id: workerId });
      } else {
        // ARM or SOLD — zero-union CANCELAR path
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
      enqueue(`Spool ${tag} cancelado`, 'success');
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'Error al cancelar spool';
      enqueue(message, 'error');
    }

    setSelectedSpool(null);
    setSelectedOperation(null);
    setSelectedAction(null);
  };

  const handleModalClose = () => {
    modalStack.pop();
    if (modalStack.stack.length <= 1) {
      // After pop, stack will be empty — reset selection
      setSelectedSpool(null);
      setSelectedOperation(null);
      setSelectedAction(null);
    }
  };

  // ── Render ───────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-zeues-navy text-white">
      {/* Header */}
      <header className="p-4 text-center border-b-4 border-white/30">
        <h1 className="text-2xl font-bold font-mono tracking-widest">ZEUES</h1>
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
        />
      </div>

      {/* ── Modals ── */}

      <AddSpoolModal
        isOpen={modalStack.isOpen('add-spool')}
        onAdd={handleAddSpool}
        onClose={handleModalClose}
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
