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
  spool: SpoolCardData;
  operation: Operation;
  action: Action;
  onComplete: () => void;
  onClose: () => void;
  isTopOfStack?: boolean;
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

// ─── Component ────────────────────────────────────────────────────────────────

export function WorkerModal({
  isOpen,
  spool,
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

  // Fetch workers when modal opens
  useEffect(() => {
    if (!isOpen) return;

    let cancelled = false;
    setFetchLoading(true);
    setFetchError(null);
    setApiError(null);

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

  async function handleWorkerClick(worker: Worker) {
    if (apiLoading) return;
    setApiLoading(true);
    setApiError(null);

    try {
      const tag = spool.tag_spool;
      const workerId = worker.id;

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

      onComplete();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Error al ejecutar la operación';
      setApiError(message);
    } finally {
      setApiLoading(false);
    }
  }

  const operationType = toOperationType(operation);
  const title = OPERATION_TITLES[operationType];
  const actionLabel = action === 'INICIAR' ? 'INICIAR' : action === 'FINALIZAR' ? 'FINALIZAR' : 'PAUSAR';

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
            {spool.tag_spool} — {actionLabel}
          </p>
        </div>

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
                aria-label={`Seleccionar ${worker.nombre_completo}`}
              >
                {worker.nombre_completo}
              </button>
            ))}

            {workers.length === 0 && (
              <p className="text-white/60 font-mono text-sm text-center py-4">
                No hay trabajadores disponibles
              </p>
            )}
          </div>
        )}

        {/* Loading spinner during API call */}
        {apiLoading && (
          <div role="status" aria-label="Procesando..." className="flex justify-center py-2">
            <div className="w-6 h-6 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          </div>
        )}

        {/* Inline error on API failure */}
        {apiError && (
          <p role="alert" className="text-red-400 font-mono text-sm font-black mt-3">
            {apiError}
          </p>
        )}

        {/* Close button */}
        <button
          onClick={onClose}
          disabled={apiLoading}
          className="w-full h-10 font-mono font-black text-white/60 border border-white/20 rounded hover:text-white hover:border-white/40 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset text-sm"
          aria-label="Cancelar y cerrar"
        >
          CANCELAR
        </button>
      </div>
    </Modal>
  );
}
