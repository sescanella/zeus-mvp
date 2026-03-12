'use client';

import React, { useEffect, useState } from 'react';
import { Modal } from './Modal';
import { Loading } from './Loading';
import {
  getWorkers,
  iniciarSpool,
  finalizarSpool,
  tomarReparacion,
  pausarReparacion,
  completarReparacion,
} from '@/lib/api';
import {
  OPERATION_TO_ROLES,
  OPERATION_TITLES,
  type OperationType,
} from '@/lib/operation-config';
import type { Worker, SpoolCardData } from '@/lib/types';
import type { Operation, Action } from '@/lib/spool-state-machine';

// ─── Types ────────────────────────────────────────────────────────────────────

interface WorkerModalProps {
  isOpen: boolean;
  spools: SpoolCardData[];
  operation: Operation;
  action: Action;
  onComplete: () => void;
  onClose: () => void;
  isTopOfStack?: boolean;
}

/** Result of processing a single spool in a batch */
interface BatchResult {
  tag: string;
  success: boolean;
  error?: string;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Maps Operation type (ARM/SOLD/REP/MET) to OperationType for OPERATION_TO_ROLES lookup.
 */
function toOperationType(operation: Operation): OperationType {
  switch (operation) {
    case 'ARM':
      return 'ARM';
    case 'SOLD':
      return 'SOLD';
    case 'REP':
      return 'REPARACION';
    case 'MET':
      return 'METROLOGIA';
    default:
      return 'ARM';
  }
}

/**
 * Small delay between sequential API calls to respect Google Sheets rate limits.
 * 60 writes/min = 1 write/sec. We use 500ms as a safe margin for single-user mode.
 */
function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

const BATCH_DELAY_MS = 500;

// ─── Component ────────────────────────────────────────────────────────────────

export function WorkerModal({
  isOpen,
  spools,
  operation,
  action,
  onComplete,
  onClose,
  isTopOfStack,
}: WorkerModalProps) {
  const [workers, setWorkers] = useState<Worker[]>([]);
  const [fetchLoading, setFetchLoading] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [apiLoading, setApiLoading] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [batchProgress, setBatchProgress] = useState<{ current: number; total: number } | null>(null);
  const [batchResults, setBatchResults] = useState<BatchResult[] | null>(null);

  // Fetch workers when modal opens
  useEffect(() => {
    if (!isOpen) return;

    let cancelled = false;
    setFetchLoading(true);
    setFetchError(null);
    setApiError(null);
    setBatchProgress(null);
    setBatchResults(null);

    getWorkers()
      .then((allWorkers) => {
        if (cancelled) return;
        const operationType = toOperationType(operation);
        const allowedRoles = OPERATION_TO_ROLES[operationType];
        const filtered = allWorkers.filter(
          (w) => w.roles?.some((r) => allowedRoles.includes(r)) ?? false
        );
        setWorkers(filtered);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const message = err instanceof Error ? err.message : 'Error al cargar trabajadores';
        setFetchError(message);
      })
      .finally(() => {
        if (!cancelled) setFetchLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [isOpen, operation]);

  /**
   * Execute API call for a single spool.
   */
  async function executeForSpool(spool: SpoolCardData, workerId: number): Promise<void> {
    const tag = spool.tag_spool;

    if (operation === 'ARM' || operation === 'SOLD') {
      if (action === 'INICIAR') {
        await iniciarSpool({
          tag_spool: tag,
          worker_id: workerId,
          operacion: operation as 'ARM' | 'SOLD',
        });
      } else if (action === 'FINALIZAR') {
        await finalizarSpool({
          tag_spool: tag,
          worker_id: workerId,
          operacion: operation as 'ARM' | 'SOLD',
          action_override: 'COMPLETAR',
        });
      } else if (action === 'PAUSAR') {
        await finalizarSpool({
          tag_spool: tag,
          worker_id: workerId,
          operacion: operation as 'ARM' | 'SOLD',
          action_override: 'PAUSAR',
        });
      }
    } else if (operation === 'REP') {
      if (action === 'INICIAR') {
        await tomarReparacion({ tag_spool: tag, worker_id: workerId });
      } else if (action === 'FINALIZAR') {
        await completarReparacion({ tag_spool: tag, worker_id: workerId });
      } else if (action === 'PAUSAR') {
        await pausarReparacion({ tag_spool: tag, worker_id: workerId });
      }
    }
  }

  async function handleWorkerClick(worker: Worker) {
    if (apiLoading) return;
    setApiLoading(true);
    setApiError(null);
    setBatchResults(null);

    const workerId = worker.id;
    const total = spools.length;

    // Single spool — simple path (no progress UI needed)
    if (total === 1) {
      try {
        await executeForSpool(spools[0], workerId);
        onComplete();
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : 'Error al ejecutar la operacion';
        setApiError(message);
      } finally {
        setApiLoading(false);
      }
      return;
    }

    // Multi-spool — batch with progress
    setBatchProgress({ current: 0, total });
    const results: BatchResult[] = [];

    for (let i = 0; i < total; i++) {
      const spool = spools[i];
      setBatchProgress({ current: i + 1, total });

      try {
        await executeForSpool(spool, workerId);
        results.push({ tag: spool.tag_spool, success: true });
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : 'Error desconocido';
        results.push({ tag: spool.tag_spool, success: false, error: message });
      }

      // Delay between calls to respect Sheets rate limits (skip after last)
      if (i < total - 1) {
        await delay(BATCH_DELAY_MS);
      }
    }

    setBatchResults(results);
    setApiLoading(false);

    const failures = results.filter((r) => !r.success);
    if (failures.length === 0) {
      // All succeeded — auto-complete after brief pause to show 100%
      setBatchProgress(null);
      onComplete();
    }
    // If there are failures, stay open to show results
  }

  const operationType = toOperationType(operation);
  const title = OPERATION_TITLES[operationType];
  const actionLabel = action === 'INICIAR' ? 'INICIAR' : action === 'FINALIZAR' ? 'FINALIZAR' : 'PAUSAR';

  // Summary text for multi-spool
  const spoolSummary = spools.length === 1
    ? spools[0].tag_spool
    : `${spools.length} spools`;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      ariaLabel={`Seleccionar trabajador para ${actionLabel} ${operation}`}
      className="bg-[#001F3F] max-w-sm"
      isTopOfStack={isTopOfStack}
    >
      <div className="flex flex-col gap-4">
        {/* Header */}
        <div>
          <h2 className="text-white font-mono font-black text-xl tracking-widest uppercase">
            {title}
          </h2>
          <p className="text-white/60 font-mono text-sm mt-1">
            {spoolSummary} — {actionLabel}
          </p>
        </div>

        {/* Batch progress */}
        {batchProgress && !batchResults && (
          <div role="status" aria-label={`Procesando spool ${batchProgress.current} de ${batchProgress.total}`} className="flex flex-col gap-2">
            <p className="text-zeues-orange font-mono font-black text-sm text-center">
              Procesando spool {batchProgress.current}/{batchProgress.total}...
            </p>
            <div className="w-full h-2 bg-white/10 rounded-full overflow-hidden">
              <div
                className="h-full bg-zeues-orange transition-all duration-300"
                style={{ width: `${(batchProgress.current / batchProgress.total) * 100}%` }}
              />
            </div>
          </div>
        )}

        {/* Batch results (shown on partial failure) */}
        {batchResults && batchResults.some((r) => !r.success) && (
          <div role="alert" className="flex flex-col gap-2">
            <p className="text-white font-mono font-black text-sm">
              Resultado: {batchResults.filter((r) => r.success).length}/{batchResults.length} exitosos
            </p>
            <div className="max-h-40 overflow-y-auto flex flex-col gap-1">
              {batchResults.map((result) => (
                <div
                  key={result.tag}
                  className={`font-mono text-xs px-2 py-1 ${
                    result.success ? 'text-green-400' : 'text-red-400'
                  }`}
                >
                  {result.tag}: {result.success ? 'OK' : result.error}
                </div>
              ))}
            </div>
            <button
              onClick={onComplete}
              className="w-full h-12 font-mono font-black text-white bg-zeues-orange border border-zeues-orange rounded hover:bg-zeues-orange/80 focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset text-sm mt-2"
              aria-label="Cerrar resultados"
            >
              CERRAR
            </button>
          </div>
        )}

        {/* Worker list — hide during batch processing and when showing results */}
        {!batchProgress && !batchResults && (
          <>
            {/* Content */}
            {fetchLoading ? (
              <Loading message="CARGANDO" />
            ) : fetchError ? (
              <p role="alert" className="text-red-400 font-mono text-sm font-black mt-3">
                {fetchError}
              </p>
            ) : (
              <div className="flex flex-col gap-2">
                {workers.map((worker) => (
                  <button
                    key={worker.id}
                    onClick={() => handleWorkerClick(worker)}
                    disabled={apiLoading}
                    className="w-full h-16 font-mono font-black text-white bg-[#0a3a6e] border border-white/20 rounded hover:bg-[#1a4a7e] disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset"
                    aria-label={`Seleccionar ${worker.nombre} ${worker.apellido || ''}`.trim()}
                  >
                    {worker.nombre} {worker.apellido || ''}
                  </button>
                ))}

                {workers.length === 0 && (
                  <p className="text-white/60 font-mono text-sm text-center py-4">
                    No hay trabajadores disponibles
                  </p>
                )}
              </div>
            )}
          </>
        )}

        {/* Loading spinner during single API call */}
        {apiLoading && !batchProgress && (
          <div role="status" aria-label="Procesando..." className="flex justify-center py-2">
            <div className="w-6 h-6 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          </div>
        )}

        {/* Inline error on API failure (single spool) */}
        {apiError && (
          <p role="alert" className="text-red-400 font-mono text-sm font-black mt-3">
            {apiError}
          </p>
        )}

        {/* Close button — hide during batch processing */}
        {!batchProgress && !batchResults && (
          <button
            onClick={onClose}
            disabled={apiLoading}
            className="w-full h-10 font-mono font-black text-white/60 border border-white/20 rounded hover:text-white hover:border-white/40 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset text-sm"
            aria-label="Cancelar y cerrar"
          >
            CANCELAR
          </button>
        )}
      </div>
    </Modal>
  );
}
