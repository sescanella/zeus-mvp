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

import React, { useState, useEffect, useRef, useMemo } from 'react';
import { SpoolListProvider, useSpoolList } from '@/lib/SpoolListContext';
import { useModalStack } from '@/hooks/useModalStack';
import { useNotificationToast } from '@/hooks/useNotificationToast';
import { AddSpoolModal } from '@/components/AddSpoolModal';
import { OperationModal } from '@/components/OperationModal';
import { ActionModal } from '@/components/ActionModal';
import { WorkerModal } from '@/components/WorkerModal';
import { MetrologiaModal } from '@/components/MetrologiaModal';
import { UnionesModal } from '@/components/UnionesModal';
import { NotasModal } from '@/components/NotasModal';
import { SpoolCardList } from '@/components/SpoolCardList';
import { NotificationToast } from '@/components/NotificationToast';
import { Search, X as XIcon } from 'lucide-react';
import {
  finalizarSpool,
  cancelarReparacion,
  pausarReparacion,
  completarReparacion,
} from '@/lib/api';
import { classifyApiError } from '@/lib/error-classifier';
import type { SpoolCardData, EstadoTrabajo } from '@/lib/types';
import { getValidActions, deriveOperation } from '@/lib/spool-state-machine';
import type { Operation, Action } from '@/lib/spool-state-machine';
import { ESTADO_LABELS, ESTADO_CHIP_COLORS, ALL_ESTADOS } from '@/lib/constants';

// ─── Blueprint grid overlay (matches BlueprintPageWrapper) ───────────────────

const BLUEPRINT_GRID_STYLE: React.CSSProperties = {
  backgroundImage: `
    linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)
  `,
  backgroundSize: '50px 50px',
};

// ─── Pending action type ─────────────────────────────────────────────────────

type PendingAction = {
  type: 'FINALIZAR' | 'PAUSAR' | 'EDIT';
  spool: SpoolCardData;
  operation: 'ARM' | 'SOLD' | null;
  workerId: number | null;
};

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

  // Filter state
  const [showFilter, setShowFilter] = useState(false);
  const [estadoFilter, setEstadoFilter] = useState<EstadoTrabajo | null>(null);
  const [searchText, setSearchText] = useState(''); // v5.1 UX-1a: free-text filter on tag_spool

  // Count spools per estado for filter badges
  const estadoCounts = useMemo(() => {
    const counts: Partial<Record<EstadoTrabajo, number>> = {};
    for (const estado of ALL_ESTADOS) {
      const count = spools.filter(s => s.estado_trabajo === estado).length;
      if (count > 0) counts[estado] = count;
    }
    return counts;
  }, [spools]);

  // Single spool selection for processing
  const [selectedSpool, setSelectedSpool] = useState<SpoolCardData | null>(null);
  const [selectedOperation, setSelectedOperation] =
    useState<Operation | null>(null);
  const [selectedAction, setSelectedAction] = useState<Action | null>(null);
  const [apiLoading, setApiLoading] = useState(false);
  const [unionesSpool, setUnionesSpool] = useState<SpoolCardData | null>(null);
  const [notasSpool, setNotasSpool] = useState<SpoolCardData | null>(null);
  const [notasWorkerId, setNotasWorkerId] = useState<number | null>(null);
  const [pendingAction, setPendingAction] = useState<PendingAction | null>(null);

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

    return () => {
      clearInterval(intervalId);
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
   * Skips OperationModal when the spool already has an active operation.
   */
  const handleCardClick = (spool: SpoolCardData) => {
    setSelectedSpool(spool);

    const knownOp = deriveOperation(spool);
    if (knownOp) {
      handleSelectOperation(knownOp, spool);
      return;
    }

    modalStack.push('operation');
  };

  const handleSelectOperation = (op: Operation, spoolOverride?: SpoolCardData) => {
    setSelectedOperation(op);

    const effectiveSpool = spoolOverride ?? selectedSpool;
    // Skip ActionModal when only one valid action
    if (effectiveSpool) {
      const actions = getValidActions(effectiveSpool);
      if (actions.length === 1) {
        handleSelectAction(actions[0], effectiveSpool, op);
        return;
      }
    }

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

  const handleSelectAction = async (action: Action, spoolOverride?: SpoolCardData, opOverride?: Operation) => {
    setSelectedAction(action);

    const effectiveSpool = spoolOverride ?? selectedSpool;
    const effectiveOp = opOverride ?? selectedOperation;

    // INICIAR: show WorkerModal (user picks the worker)
    if (action === 'INICIAR') {
      modalStack.push('worker');
      return;
    }

    // FINALIZAR / PAUSAR for ARM/SOLD: open UnionesModal with selection mode
    if (
      (action === 'FINALIZAR' || action === 'PAUSAR') &&
      effectiveSpool &&
      effectiveOp &&
      (effectiveOp === 'ARM' || effectiveOp === 'SOLD')
    ) {
      const ocupadoPor = effectiveSpool.ocupado_por;
      if (!ocupadoPor) {
        enqueue('Error: spool no tiene trabajador asignado', 'error');
        return;
      }

      const workerId = parseWorkerIdFromOcupadoPor(ocupadoPor);
      if (workerId === null) {
        enqueue('Error: formato de trabajador invalido', 'error');
        return;
      }

      setPendingAction({
        type: action as 'FINALIZAR' | 'PAUSAR',
        spool: effectiveSpool,
        operation: effectiveOp as 'ARM' | 'SOLD',
        workerId,
      });
      setUnionesSpool(effectiveSpool);
      modalStack.push('uniones');
      return;
    }

    // FINALIZAR / PAUSAR for REP: use direct action (no UnionesModal)
    if (
      (action === 'FINALIZAR' || action === 'PAUSAR') &&
      effectiveSpool &&
      effectiveOp
    ) {
      const ocupadoPor = effectiveSpool.ocupado_por;
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
        await executeDirectAction(action, effectiveSpool, effectiveOp, workerId);
        const tag = effectiveSpool.tag_spool;
        modalStack.clear();

        try {
          await refreshSingle(tag);
        } catch {
          // Spool may have been removed — ignore refresh errors
        }

        enqueue('Operacion completada', 'success');
      } catch (err: unknown) {
        enqueue(classifyApiError(err).userMessage, 'error');
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

    if (resultado === 'APROBADO') {
      modalStack.clear();
      removeSpool(tag);
      enqueue(`Metrologia aprobada — ${tag}`, 'success');
      setSelectedSpool(null);
      setSelectedOperation(null);
      setSelectedAction(null);
      return;
    }

    // T-095: RECHAZADO chains into reparación. The backend has already marked
    // the spool as RECHAZADO with Ocupado_Por=null (MetrologiaModal called
    // completarMetrologia). The operator now needs to pick the repairman.
    // Clear the whole modal stack so the OperationModal underneath doesn't
    // flash, refresh the card, switch selection to REP/INICIAR and open the
    // WorkerModal. WorkerModal will POST /api/tomar-reparacion on worker
    // selection, and its onComplete fires handleWorkerComplete which already
    // refreshes + clears state.
    modalStack.clear();
    let refreshFailed = false;
    try {
      await refreshSingle(tag);
    } catch {
      // Refresh failure is non-fatal for the REP flow — WorkerModal operates
      // on tag_spool, not on a stale spool snapshot, and tomarReparacion does
      // not read card state. But the card in the list won't reflect the new
      // RECHAZADO state until the next poll, so warn the operator.
      refreshFailed = true;
    }
    enqueue(`Metrologia rechazada — ${tag}. Selecciona reparador.`, 'success');
    if (refreshFailed) {
      enqueue(
        `Aviso: la card puede seguir mostrando el estado anterior hasta el proximo refresco.`,
        'error',
      );
    }
    setSelectedOperation('REP');
    setSelectedAction('INICIAR');
    modalStack.push('worker');
  };

  const handleRemove = async (tag: string) => {
    const spool = spools.find(s => s.tag_spool === tag);
    if (!spool) {
      removeSpool(tag);
      return;
    }

    // Libre spool — frontend-only removal
    if (!spool.ocupado_por) {
      removeSpool(tag);
      enqueue('Spool quitado', 'success');
      return;
    }

    // Occupied spool — call backend to release, then remove
    const workerId = parseWorkerIdFromOcupadoPor(spool.ocupado_por);
    if (workerId === null) {
      enqueue('Error: formato de trabajador invalido', 'error');
      return;
    }

    // Confirm before releasing occupied spool
    const confirmed = window.confirm(
      `¿Quitar spool ${tag} ocupado por ${spool.ocupado_por}? Se liberará el spool.`
    );
    if (!confirmed) return;

    try {
      if (spool.operacion_actual === 'REPARACION') {
        await cancelarReparacion({ tag_spool: tag, worker_id: workerId });
      } else {
        const operacion = (spool.operacion_actual ?? 'ARM') as 'ARM' | 'SOLD';
        await finalizarSpool({
          tag_spool: tag,
          worker_id: workerId,
          operacion,
          selected_unions: [],
        });
      }
      removeSpool(tag);
      enqueue('Spool quitado y liberado', 'success');
    } catch {
      enqueue('Error al liberar spool', 'error');
    }
  };

  const handleModalClose = () => {
    // Capture length BEFORE pop — pop() schedules a setState and the stack ref
    // remains stale until the next render. Reading after pop always sees the
    // pre-pop value, making the condition unreliable.
    const stackLengthBeforePop = modalStack.stack.length;
    modalStack.pop();
    if (stackLengthBeforePop <= 1) {
      // Stack will be empty after this pop — reset operation/action selection
      setSelectedOperation(null);
      setSelectedAction(null);
      setSelectedSpool(null);
    }
  };

  const handleUnionesClick = (spool: SpoolCardData) => {
    setPendingAction({ type: 'EDIT', spool, operation: null, workerId: null });
    setUnionesSpool(spool);
    modalStack.push('uniones');
  };

  const handleNotasClick = (spool: SpoolCardData) => {
    // Derive worker id from current occupancy if any, for author attribution in the
    // audit trail. If the spool is free, we still allow reading but block saving by
    // passing null (NotasModal hides the composer in that case).
    let workerId: number | null = null;
    if (spool.ocupado_por) {
      const m = spool.ocupado_por.match(/\((\d+)\)/);
      if (m) workerId = parseInt(m[1], 10);
    }
    setNotasWorkerId(workerId);
    setNotasSpool(spool);
    modalStack.push('notas');
  };

  const handleNotasClose = () => {
    modalStack.pop();
    setNotasSpool(null);
    setNotasWorkerId(null);
  };

  const handleUnionesComplete = async (selectedIds: string[]) => {
    const action = pendingAction;

    // Clear ALL modals and state immediately to prevent flash of ActionModal/OperationModal
    modalStack.clear();
    setPendingAction(null);
    setUnionesSpool(null);
    setSelectedSpool(null);
    setSelectedOperation(null);
    setSelectedAction(null);

    if (!action) return;

    const tag = action.spool.tag_spool;

    if (action.type === 'EDIT') {
      try {
        await refreshSingle(tag);
      } catch {
        // ignore
      }
      enqueue('Uniones guardadas', 'success');
    } else if (action.type === 'FINALIZAR' || action.type === 'PAUSAR') {
      if (selectedIds.length > 0 && action.workerId !== null && action.operation !== null) {
        setApiLoading(true);
        try {
          await finalizarSpool({
            tag_spool: tag,
            worker_id: action.workerId,
            operacion: action.operation,
            selected_unions: selectedIds,
          });
          try {
            await refreshSingle(tag);
          } catch {
            // ignore
          }
          enqueue('Operacion completada', 'success');
        } catch (err: unknown) {
          enqueue(classifyApiError(err).userMessage, 'error');
        } finally {
          setApiLoading(false);
        }
      } else if (selectedIds.length === 0 && action.type === 'PAUSAR' && action.workerId !== null && action.operation !== null) {
        setApiLoading(true);
        try {
          await finalizarSpool({
            tag_spool: tag,
            worker_id: action.workerId,
            operacion: action.operation,
            selected_unions: [],
            action_override: 'PAUSAR',
          });
          try {
            await refreshSingle(tag);
          } catch {
            // ignore
          }
          enqueue('Uniones guardadas y spool pausado', 'success');
        } catch (err: unknown) {
          enqueue(classifyApiError(err).userMessage, 'error');
        } finally {
          setApiLoading(false);
        }
      } else if (action.type === 'FINALIZAR') {
        enqueue('Error: no se pudieron identificar las uniones seleccionadas', 'error');
      } else {
        try {
          await refreshSingle(tag);
        } catch {
          // ignore
        }
        enqueue('Uniones guardadas', 'success');
      }
    }
  };

  // ── Render ───────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-zeues-navy text-white" style={BLUEPRINT_GRID_STYLE}>
      {/* Header */}
      <header className="flex items-center justify-between px-4 py-3 border-b-4 border-white/30">
        {spools.length > 0 ? (
          <span className="font-mono text-sm text-white/70 tracking-widest">
            {spools.length} {spools.length === 1 ? 'SPOOL' : 'SPOOLS'}
          </span>
        ) : (
          <span />
        )}
        <img src="/logos/logo-grisclaro-F8F9FA.svg" alt="KM" className="h-10" />
      </header>

      {/* Add Spool button + Filter */}
      <div className="px-4 py-4">
        {/* Search input (v5.1 UX-1a) */}
        {spools.length > 0 && (
          <div className="relative mb-3">
            <Search
              size={18}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40 pointer-events-none"
              aria-hidden="true"
            />
            <input
              type="text"
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              placeholder="Buscar por TAG (ej: MK-1923)"
              aria-label="Buscar spool en el listado por TAG"
              className="w-full h-12 pl-10 pr-10 bg-transparent border-2 border-white/30 text-white font-mono font-black placeholder:text-white/40 focus:outline-none focus:border-zeues-orange focus:ring-2 focus:ring-zeues-orange focus:ring-inset"
            />
            {searchText && (
              <button
                type="button"
                onClick={() => setSearchText('')}
                aria-label="Limpiar búsqueda"
                className="absolute right-2 top-1/2 -translate-y-1/2 min-w-[44px] min-h-[44px] flex items-center justify-center text-white/70 hover:text-white focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset"
              >
                <XIcon size={18} strokeWidth={3} />
              </button>
            )}
          </div>
        )}

        {/* Button row */}
        <div className="flex gap-3">
          <button
            onClick={() => modalStack.push('add-spool')}
            className="flex-1 h-16 bg-zeues-orange text-white font-bold font-mono rounded-none text-lg tracking-widest cursor-pointer focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset"
            aria-label="Añadir spool al listado"
          >
            + Añadir Spool
          </button>
          <button
            onClick={() => setShowFilter(!showFilter)}
            aria-expanded={showFilter}
            aria-controls="estado-filter-panel"
            aria-label={showFilter ? 'Ocultar filtros de estado' : 'Mostrar filtros de estado'}
            className={`h-16 px-4 font-mono font-black text-sm tracking-widest border-4 cursor-pointer transition-colors focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset ${
              estadoFilter
                ? 'bg-white/10 border-white text-white'
                : 'border-white/30 text-white/70 hover:border-white/50'
            }`}
          >
            {estadoFilter
              ? <><span className="inline-flex items-center justify-center min-w-[1.5rem] h-6 px-1 mr-1.5 rounded bg-white/20 text-xs font-black">{estadoCounts[estadoFilter] ?? 0}</span>{ESTADO_LABELS[estadoFilter]}</>
              : 'FILTRAR'}
          </button>
        </div>

        {/* Filter chip panel — stays open until toggled */}
        {showFilter && (
          <div
            id="estado-filter-panel"
            role="region"
            aria-label="Filtrar por estado"
            className="flex flex-wrap gap-2 mt-3"
          >
            {ALL_ESTADOS.map((estado) => (
              <button
                key={estado}
                onClick={() => setEstadoFilter(estadoFilter === estado ? null : estado)}
                aria-pressed={estadoFilter === estado}
                className={`inline-flex items-center justify-center min-h-[44px] px-3 py-2 font-mono font-black text-sm border-2 cursor-pointer transition-colors focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset ${
                  estadoFilter === estado
                    ? ESTADO_CHIP_COLORS[estado]
                    : 'border-white/20 text-white/70 hover:border-white/40'
                }`}
              >
                {estadoCounts[estado] != null && (
                  <span className={`inline-flex items-center justify-center min-w-[1.5rem] h-6 px-1 mr-1.5 rounded text-xs font-black ${
                    estadoFilter === estado ? 'bg-white/20' : 'bg-white/10'
                  }`}>{estadoCounts[estado]}</span>
                )}
                {ESTADO_LABELS[estado]}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Spool card list */}
      <div className="px-4">
        <SpoolCardList
          spools={spools}
          onCardClick={handleCardClick}
          onRemove={handleRemove}
          onUnionesClick={handleUnionesClick}
          onNotasClick={handleNotasClick}
          estadoFilter={estadoFilter}
          searchText={searchText}
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

      {unionesSpool && (
        <UnionesModal
          isOpen={modalStack.isOpen('uniones')}
          spool={unionesSpool}
          operacion={pendingAction?.operation ?? null}
          onComplete={handleUnionesComplete}
          onClose={() => { modalStack.pop(); setPendingAction(null); setUnionesSpool(null); }}
          isTopOfStack={modalStack.isOpen('uniones')}
        />
      )}

      {notasSpool && (
        <NotasModal
          isOpen={modalStack.isOpen('notas')}
          spool={notasSpool}
          workerId={notasWorkerId}
          onClose={handleNotasClose}
          isTopOfStack={modalStack.isOpen('notas')}
        />
      )}

      {/* Loading overlay for direct API calls (FINALIZAR/PAUSAR without WorkerModal) */}
      {apiLoading && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
          role="status"
          aria-label="Procesando operacion"
        >
          <div className="flex flex-col items-center gap-3 bg-zeues-navy border-4 border-white p-8">
            <div className="w-8 h-8 border-2 border-white/30 border-t-white rounded-full animate-spin" aria-hidden="true" />
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
