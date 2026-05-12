'use client';

import React, { useEffect, useRef, useState } from 'react';
import { X } from 'lucide-react';
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
import { classifyApiError } from '@/lib/error-classifier';
import { hapticTap } from '@/lib/haptic';
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
  const lastWorkerRef = useRef<Worker | null>(null);

  function fetchWorkers() {
    setFetchLoading(true);
    setFetchError(null);

    const operationType = toOperationType(operation);
    const allowedRoles = OPERATION_TO_ROLES[operationType];

    getWorkers()
      .then((allWorkers) => {
        const filtered = allWorkers.filter(
          (w) => w.roles?.some((r) => allowedRoles.includes(r)) ?? false
        );
        setWorkers(filtered);
      })
      .catch((err: unknown) => {
        setFetchError(classifyApiError(err).userMessage);
      })
      .finally(() => {
        setFetchLoading(false);
      });
  }

  // Fetch workers when modal opens
  useEffect(() => {
    if (!isOpen) return;

    setApiError(null);
    lastWorkerRef.current = null;
    fetchWorkers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, operation]);

  /**
   * Execute API call for the spool.
   */
  async function executeForSpool(workerId: number): Promise<void> {
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
    hapticTap();
    lastWorkerRef.current = worker;
    setApiLoading(true);
    setApiError(null);

    try {
      await executeForSpool(worker.id);
      onComplete();
    } catch (err: unknown) {
      setApiError(classifyApiError(err).userMessage);
    } finally {
      setApiLoading(false);
    }
  }

  async function handleRetry() {
    if (!lastWorkerRef.current) return;
    await handleWorkerClick(lastWorkerRef.current);
  }

  const operationType = toOperationType(operation);
  const title = OPERATION_TITLES[operationType];
  const actionLabel = action === 'INICIAR' ? 'INICIAR' : action === 'FINALIZAR' ? 'FINALIZAR' : 'PAUSAR';

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      ariaLabel={`Seleccionar trabajador para ${actionLabel} ${operation}`}
      className="bg-zeues-navy border-4 border-white"
      isTopOfStack={isTopOfStack}
    >
      <div className="flex flex-col gap-4">
        {/* Header */}
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <h2 className="text-white font-mono font-black text-xl tracking-widest uppercase">
              {title}
            </h2>
            <p className="text-white/70 font-mono text-sm mt-1">
              {spool.tag_spool} — {actionLabel}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={apiLoading}
            aria-label="Cerrar modal"
            className="min-w-[44px] min-h-[44px] flex items-center justify-center text-white/70 hover:text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset"
          >
            <X size={24} strokeWidth={3} />
          </button>
        </div>

        {/* Worker list */}
        {fetchLoading ? (
          <Loading message="CARGANDO" />
        ) : fetchError ? (
          <div className="flex flex-col gap-3">
            <p role="alert" className="text-red-400 font-mono text-sm font-black">
              {fetchError}
            </p>
            <button
              onClick={fetchWorkers}
              className="w-full h-12 font-mono font-black text-white border-2 border-white rounded cursor-pointer hover:bg-white/10 focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset text-sm"
              aria-label="Reintentar cargar trabajadores"
            >
              REINTENTAR
            </button>
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            {workers.map((worker) => (
              <button
                key={worker.id}
                onClick={() => handleWorkerClick(worker)}
                disabled={apiLoading}
                className="w-full h-16 font-mono font-black text-white bg-zeues-navy/80 border border-white/20 rounded cursor-pointer hover:bg-white/10 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset"
                aria-label={`Seleccionar ${worker.nombre} ${worker.apellido || ''}`.trim()}
              >
                {worker.nombre} {worker.apellido || ''}
              </button>
            ))}

            {workers.length === 0 && (
              <p className="text-white/70 font-mono text-sm text-center py-4">
                No hay trabajadores disponibles
              </p>
            )}
          </div>
        )}

        {/* Loading spinner during API call */}
        {apiLoading && (
          <div role="status" aria-label="Procesando..." className="flex justify-center py-2">
            <div className="w-6 h-6 border-2 border-white/30 border-t-white rounded-full animate-spin" aria-hidden="true" />
          </div>
        )}

        {/* Inline error on API failure + retry */}
        {apiError && (
          <div className="flex flex-col gap-3">
            <p role="alert" className="text-red-400 font-mono text-sm font-black">
              {apiError}
            </p>
            <button
              onClick={handleRetry}
              disabled={apiLoading}
              className="w-full h-12 font-mono font-black text-white border-2 border-white rounded cursor-pointer hover:bg-white/10 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset text-sm"
              aria-label="Reintentar la acción"
            >
              REINTENTAR
            </button>
          </div>
        )}

        {/* Close button */}
        <button
          onClick={onClose}
          disabled={apiLoading}
          className="w-full h-12 font-mono font-black text-white/70 border border-white/20 rounded cursor-pointer hover:text-white hover:border-white/40 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset text-sm"
          aria-label="Cancelar y cerrar"
        >
          CANCELAR
        </button>
      </div>
    </Modal>
  );
}
