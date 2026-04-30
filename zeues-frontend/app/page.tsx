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
import { WorkerPickerModal } from '@/components/WorkerPickerModal';
import { SpoolCardList } from '@/components/SpoolCardList';
import { NotificationToast } from '@/components/NotificationToast';
import { Search, X as XIcon, ChevronDown } from 'lucide-react';
import {
  finalizarSpool,
  cancelarReparacion,
  pausarReparacion,
  completarReparacion,
  iniciarSpool,
} from '@/lib/api';
import { classifyApiError } from '@/lib/error-classifier';
import type { SpoolCardData, EstadoTrabajo, Worker } from '@/lib/types';
import { getValidActions, deriveOperation, isMetReady } from '@/lib/spool-state-machine';
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
  const [workerFilter, setWorkerFilter] = useState<string | null>(null); // v5.1 UX-1d: filter by ocupado_por (exact match "INICIALES(ID)")

  // Count spools per estado for filter badges
  const estadoCounts = useMemo(() => {
    const counts: Partial<Record<EstadoTrabajo, number>> = {};
    for (const estado of ALL_ESTADOS) {
      const count = spools.filter(s => s.estado_trabajo === estado).length;
      if (count > 0) counts[estado] = count;
    }
    return counts;
  }, [spools]);

  // v5.1 UX-1d: derive list of workers currently occupying at least one spool,
  // ordered alphabetically. The dropdown only shows workers who have active
  // occupation — selecting the same person who has multiple spools shows all.
  const activeWorkers = useMemo(() => {
    const workerCounts = new Map<string, number>();
    for (const s of spools) {
      if (s.ocupado_por) {
        workerCounts.set(s.ocupado_por, (workerCounts.get(s.ocupado_por) ?? 0) + 1);
      }
    }
    return Array.from(workerCounts.entries())
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => a.name.localeCompare(b.name));
  }, [spools]);

  // Auto-clear worker filter if the selected worker no longer has any occupied spools
  useEffect(() => {
    if (workerFilter && !activeWorkers.some(w => w.name === workerFilter)) {
      setWorkerFilter(null);
    }
  }, [workerFilter, activeWorkers]);

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

  // v5.1 UX-2: batch-INICIAR flow. Holds the tags the user selected in
  // AddSpoolModal while the WorkerPickerModal asks for an armador.
  const [batchTags, setBatchTags] = useState<string[] | null>(null);
  const [batchInProgress, setBatchInProgress] = useState(false);

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
   * v5.1 UX-2: AddSpoolModal confirmed a batch selection. Remember the
   * tags and open the worker picker. `AddSpoolModal` has already closed
   * itself by now.
   */
  const handleBatchAdd = (tags: string[]) => {
    if (tags.length === 0) return;
    setBatchTags(tags);
    modalStack.push('batch-worker-picker');
  };

  const handleBatchCancel = () => {
    // Ignore ALL close signals (cancel button, ESC, backdrop) while the
    // INICIAR batch is in-flight. The WorkerPickerModal also disables
    // the cancel button via `disabled`, but the Modal's ESC handler
    // calls onClose directly — so we guard here too.
    if (batchInProgress) return;
    const count = batchTags?.length ?? 0;
    modalStack.pop();
    setBatchTags(null);
    // T-132 / Bug 8: without this toast, dismissing the WorkerPickerModal
    // (cancel / ESC / backdrop) leaves no trace — operator perceives
    // "ASIGNAR ARMADOR (N) doesn't work" because the AddSpoolModal closed
    // and nothing else happened.
    if (count > 0) {
      enqueue(
        `Asignación cancelada — ningún spool fue asignado a un armador`,
        'success',
      );
    }
  };

  /**
   * v5.1 UX-2: armador picked. For each selected tag, add it to the
   * tracked card list (sequential — addSpool fetches /spool-status) and
   * then fire POST /api/v4/occupation/iniciar in parallel with
   * Promise.allSettled so one failure doesn't block the rest.
   * The backend derives worker_nombre from worker_id since v5.0.
   *
   * Wrapped in try/finally so `batchInProgress` is always reset even
   * if an unexpected synchronous error escapes (addSpool or enqueue).
   * Without it a single throw would lock the UI with no recovery.
   */
  const handleBatchWorkerPick = async (worker: Worker) => {
    if (!batchTags || batchTags.length === 0) return;
    const tags = batchTags; // snapshot for this run
    setBatchInProgress(true);

    try {
      // Step 1: ensure every spool is tracked in the card list before
      // INICIAR fires. Sequential on purpose — addSpool hits the backend
      // and parallelizing it could trigger the 60 writes/min Sheets
      // rate limit. `addSpool` is idempotent (no-op if already tracked).
      for (const tag of tags) {
        try {
          await addSpool(tag);
        } catch {
          // Ignore per-spool add errors; INICIAR below will report the real problem.
        }
      }

      // Step 2: fire all INICIAR in parallel. Sheets tolerates ~5-10
      // concurrent writes well below the 60/min ceiling.
      const results = await Promise.allSettled(
        tags.map((tag) =>
          iniciarSpool({
            tag_spool: tag,
            worker_id: worker.id,
            operacion: 'ARM',
          })
        )
      );

      const successes: string[] = [];
      const failures: { tag: string; message: string }[] = [];
      results.forEach((r, i) => {
        const tag = tags[i];
        if (r.status === 'fulfilled') {
          successes.push(tag);
        } else {
          failures.push({ tag, message: classifyApiError(r.reason).userMessage });
        }
      });

      // Step 3: refresh successfully-started spools in parallel so
      // occupied badges update without waiting for the 30s poller.
      // Failures here are silent — the card will eventually refresh via
      // the poller. Parallel, not sequential, because no write pressure.
      await Promise.allSettled(
        successes.map((tag) => refreshSingle(tag))
      );

      // Step 4: user feedback. On a factory floor the operator needs to
      // know exactly which tags failed so they can address each one.
      if (successes.length > 0) {
        enqueue(
          `${successes.length} spool${successes.length === 1 ? '' : 's'} asignado${
            successes.length === 1 ? '' : 's'
          } a ${worker.nombre_completo}`,
          'success'
        );
      }
      if (failures.length > 0) {
        // T-132 / Bug 8: group failures by reason so the operator sees
        // every distinct cause, not just the first failure's message.
        // Heterogeneous batches (e.g., 1 ARM-not-completed + 1 already-
        // occupied) used to be invisible because we only showed
        // failures[0].message.
        const byMsg = new Map<string, string[]>();
        for (const f of failures) {
          const arr = byMsg.get(f.message);
          if (arr) arr.push(f.tag);
          else byMsg.set(f.message, [f.tag]);
        }
        const summary = Array.from(byMsg.entries())
          .map(([msg, tags]) => `${tags.join(', ')}: ${msg}`)
          .join(' · ');
        enqueue(
          failures.length === 1
            ? `Falló ${failures[0].tag}: ${failures[0].message}`
            : `${failures.length} fallos — ${summary}`,
          'error',
        );
      }
    } finally {
      setBatchInProgress(false);
      modalStack.pop();
      setBatchTags(null);
    }
  };

  /**
   * Card click opens the modal chain for a single spool.
   * Skips OperationModal when the spool already has an active operation
   * or when the next step is deterministic (T-110: ARM_TERM→SOLD,
   * SOLD_TERM→MET).
   */
  const handleCardClick = (spool: SpoolCardData) => {
    setSelectedSpool(spool);

    // T-110 hotspot H2: PENDIENTE_METROLOGIA has only one valid next
    // step — open the MetrologiaModal directly. The MET path bypasses
    // handleSelectOperation, so check it before deriveOperation.
    if (isMetReady(spool)) {
      modalStack.push('metrologia');
      return;
    }

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

  /**
   * T-111 hotspot H1: after a successful FINALIZAR (ARM/SOLD/REP) the only
   * valid next move for the operator is the next operation in the chain
   * (ARM→SOLD, SOLD→MET, REP→MET). Replicates the post-RECHAZADO handoff
   * pattern from handleMetComplete (clear stack → refresh in background →
   * pre-set selectedOperation/Action → push next modal) so the operator
   * never has to re-click the card just to advance the chain.
   *
   * Caller MUST keep selectedSpool populated through this call — the next
   * modal reads it. The helper itself does not clear selectedSpool; the
   * following modal's own onComplete handler does (handleWorkerComplete /
   * handleMetComplete).
   *
   * NOT applicable to PAUSAR (operator wants out), API failures (modal
   * stays open for retry), or BLOQUEADO (no next step). Those callers
   * skip this helper and clear state themselves.
   */
  const chainNextModalAfterFinalizar = async (
    tag: string,
    nextOp: Operation,
    nextModal: 'worker' | 'metrologia',
    nextAction: Action | null = 'INICIAR',
  ) => {
    modalStack.clear();
    let refreshFailed = false;
    try {
      await refreshSingle(tag);
    } catch {
      // Refresh failure is non-fatal — the next modal operates on tag_spool,
      // not on a stale spool snapshot. Warn the operator that the card may
      // lag until the next 30s poll.
      refreshFailed = true;
    }
    enqueue('Operacion completada', 'success');
    if (refreshFailed) {
      enqueue(
        'Aviso: la card puede seguir mostrando el estado anterior hasta el proximo refresco.',
        'error',
      );
    }
    setSelectedOperation(nextOp);
    setSelectedAction(nextAction);
    modalStack.push(nextModal);
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
      let chained = false;
      try {
        await executeDirectAction(action, effectiveSpool, effectiveOp, workerId);
        const tag = effectiveSpool.tag_spool;

        // T-111: post-FINALIZAR REP, the only valid next move is metrología.
        // Auto-chain to MetrologiaModal so the operator does not have to
        // re-click the card. PAUSAR REP keeps the legacy clear-and-exit
        // behaviour (operator explicitly requested to stop the flow).
        if (action === 'FINALIZAR' && effectiveOp === 'REP') {
          await chainNextModalAfterFinalizar(tag, 'MET', 'metrologia', null);
          chained = true;
        } else {
          modalStack.clear();
          try {
            await refreshSingle(tag);
          } catch {
            // Spool may have been removed — ignore refresh errors
          }
          enqueue('Operacion completada', 'success');
        }
      } catch (err: unknown) {
        enqueue(classifyApiError(err).userMessage, 'error');
      } finally {
        setApiLoading(false);
        // When the chain takes over, the next modal owns the lifecycle —
        // its onComplete handler (handleWorkerComplete / handleMetComplete)
        // is responsible for clearing selection. Clearing here would
        // unmount the just-pushed modal because of the {selectedSpool && ...}
        // guard around the modal block.
        if (!chained) {
          setSelectedSpool(null);
          setSelectedOperation(null);
          setSelectedAction(null);
        }
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

    // Close the modal stack and the UnionesModal-specific scratch state
    // immediately so the user sees no ActionModal/OperationModal flash.
    // selectedSpool/Operation/Action are NOT cleared here — when the FINALIZAR
    // path chains into the next modal (T-111), the next modal needs them
    // populated. Each branch below decides whether to clear or chain.
    modalStack.clear();
    setPendingAction(null);
    setUnionesSpool(null);

    const clearSelection = () => {
      setSelectedSpool(null);
      setSelectedOperation(null);
      setSelectedAction(null);
    };

    if (!action) {
      clearSelection();
      return;
    }

    const tag = action.spool.tag_spool;

    if (action.type === 'EDIT') {
      clearSelection();
      try {
        await refreshSingle(tag);
      } catch {
        // ignore
      }
      enqueue('Uniones guardadas', 'success');
      return;
    }

    if (action.type !== 'FINALIZAR' && action.type !== 'PAUSAR') {
      clearSelection();
      return;
    }

    // Happy FINALIZAR path with at least one union selected.
    if (selectedIds.length > 0 && action.workerId !== null && action.operation !== null) {
      setApiLoading(true);
      let chained = false;
      try {
        await finalizarSpool({
          tag_spool: tag,
          worker_id: action.workerId,
          operacion: action.operation,
          selected_unions: selectedIds,
        });

        // T-111 hotspot H1: post-FINALIZAR ARM/SOLD, the next move is
        // deterministic — INICIAR SOLD (next worker) or open MET. Auto-chain
        // so the operator never re-clicks the card. PAUSAR with selected
        // unions still ends the flow (operator chose to stop).
        if (action.type === 'FINALIZAR') {
          if (action.operation === 'ARM') {
            await chainNextModalAfterFinalizar(tag, 'SOLD', 'worker', 'INICIAR');
            chained = true;
          } else if (action.operation === 'SOLD') {
            await chainNextModalAfterFinalizar(tag, 'MET', 'metrologia', null);
            chained = true;
          }
        }

        if (!chained) {
          try {
            await refreshSingle(tag);
          } catch {
            // ignore
          }
          enqueue('Operacion completada', 'success');
        }
      } catch (err: unknown) {
        enqueue(classifyApiError(err).userMessage, 'error');
      } finally {
        setApiLoading(false);
        if (!chained) {
          clearSelection();
        }
      }
      return;
    }

    // PAUSAR with zero selected unions: keep partial progress, mark as paused.
    if (selectedIds.length === 0 && action.type === 'PAUSAR' && action.workerId !== null && action.operation !== null) {
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
        clearSelection();
      }
      return;
    }

    if (action.type === 'FINALIZAR') {
      clearSelection();
      enqueue('Error: no se pudieron identificar las uniones seleccionadas', 'error');
      return;
    }

    // PAUSAR fallback (no workerId/operation, just save uniones).
    clearSelection();
    try {
      await refreshSingle(tag);
    } catch {
      // ignore
    }
    enqueue('Uniones guardadas', 'success');
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
            aria-label={showFilter ? 'Ocultar filtros' : 'Mostrar filtros'}
            className={`h-16 px-4 font-mono font-black text-sm tracking-widest border-4 cursor-pointer transition-colors focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset ${
              estadoFilter || workerFilter
                ? 'bg-white/10 border-white text-white'
                : 'border-white/30 text-white/70 hover:border-white/50'
            }`}
          >
            {(() => {
              const activeCount = (estadoFilter ? 1 : 0) + (workerFilter ? 1 : 0);
              if (activeCount === 0) return 'FILTRAR';
              // Single estado filter: keep the historical "{count} {ESTADO}" badge
              // where count is the number of spools in that estado (pre-v5.1 behavior).
              if (activeCount === 1 && estadoFilter) {
                return (
                  <>
                    <span className="inline-flex items-center justify-center min-w-[1.5rem] h-6 px-1 mr-1.5 rounded bg-white/20 text-xs font-black">{estadoCounts[estadoFilter] ?? 0}</span>
                    {ESTADO_LABELS[estadoFilter]}
                  </>
                );
              }
              // Single worker filter: show the worker's ocupado_por string directly.
              // The label already encodes identity; the spool count lives in the
              // dropdown option text.
              if (activeCount === 1 && workerFilter) {
                return workerFilter;
              }
              return (
                <>
                  <span className="inline-flex items-center justify-center min-w-[1.5rem] h-6 px-1 mr-1.5 rounded bg-white/20 text-xs font-black">{activeCount}</span>
                  FILTROS
                </>
              );
            })()}
          </button>
        </div>

        {/* Filter panel — stays open until toggled. Contains estado chips (v5.0) and worker dropdown (v5.1 UX-1d). */}
        {showFilter && (
          <div
            id="estado-filter-panel"
            role="region"
            aria-label="Filtros del listado"
            className="mt-3 space-y-3"
          >
            <div className="flex flex-wrap gap-2">
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

            {/* Worker filter dropdown (v5.1 UX-1d) — only shown when at least one spool is occupied. */}
            {activeWorkers.length > 0 && (
              <div>
                <label htmlFor="worker-filter" className="sr-only">
                  Filtrar spools por trabajador ocupante
                </label>
                <div className="relative">
                  <select
                    id="worker-filter"
                    value={workerFilter ?? ''}
                    onChange={(e) => setWorkerFilter(e.target.value || null)}
                    className={`w-full h-16 pl-4 pr-12 appearance-none font-mono font-black text-sm tracking-widest border-2 cursor-pointer transition-colors focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset ${
                      workerFilter
                        ? 'bg-white/10 border-white text-white'
                        : 'bg-transparent border-white/30 text-white/70'
                    }`}
                  >
                    <option value="" className="bg-zeues-navy text-white">
                      TODOS LOS TRABAJADORES
                    </option>
                    {activeWorkers.map((w) => (
                      <option key={w.name} value={w.name} className="bg-zeues-navy text-white">
                        {w.name} · {w.count} {w.count === 1 ? 'spool' : 'spools'}
                      </option>
                    ))}
                  </select>
                  <ChevronDown
                    size={20}
                    strokeWidth={3}
                    className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-white/60"
                    aria-hidden="true"
                  />
                </div>
              </div>
            )}
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
          workerFilter={workerFilter}
        />
      </div>

      {/* ── Modals ── */}

      <AddSpoolModal
        isOpen={modalStack.isOpen('add-spool')}
        onAdd={handleAddSpool}
        onBatchAdd={handleBatchAdd}
        onClose={handleAddSpoolClose}
        alreadyTracked={spools.map((s) => s.tag_spool)}
        isTopOfStack={modalStack.isOpen('add-spool')}
      />

      {batchTags && (
        <WorkerPickerModal
          isOpen={modalStack.isOpen('batch-worker-picker')}
          operationType="ARM"
          title={`ASIGNAR ARMADOR A ${batchTags.length} SPOOL${batchTags.length === 1 ? '' : 'S'}`}
          subtitle={batchTags.slice(0, 3).join(', ') + (batchTags.length > 3 ? `, +${batchTags.length - 3} más` : '')}
          onPick={handleBatchWorkerPick}
          onClose={handleBatchCancel}
          disabled={batchInProgress}
          isTopOfStack={modalStack.isOpen('batch-worker-picker')}
        />
      )}

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
