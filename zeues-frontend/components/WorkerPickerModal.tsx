'use client';

/**
 * WorkerPickerModal — v5.1 UX-2 (batch ingreso).
 *
 * Pure picker: lists the workers allowed for a given operation role and
 * fires `onPick(worker)` when one is selected. No side effects (no API
 * calls, no occupation logic). Used by the batch-INICIAR flow in
 * AddSpoolModal where the caller owns the orchestration across N spools.
 *
 * For the single-spool INICIAR/FINALIZAR flow keep using WorkerModal —
 * it bundles the API call and error recovery for that case.
 */

import React, { useCallback, useEffect, useState } from 'react';
import { Modal } from '@/components/Modal';
import { Loading } from '@/components/Loading';
import { getWorkers } from '@/lib/api';
import { OPERATION_TO_ROLES, type OperationType } from '@/lib/operation-config';
import { classifyApiError } from '@/lib/error-classifier';
import type { Worker } from '@/lib/types';

interface WorkerPickerModalProps {
  isOpen: boolean;
  operationType: OperationType; // 'ARM' | 'SOLD' | 'REPARACION' | 'METROLOGIA'
  title: string;                // e.g. "ASIGNAR ARMADOR A 5 SPOOLS"
  subtitle?: string;            // e.g. "MK-1923, MK-1924, MK-1925, …"
  onPick: (worker: Worker) => void;
  onClose: () => void;
  disabled?: boolean;           // true while the parent is processing the pick
  isTopOfStack?: boolean;
}

export function WorkerPickerModal({
  isOpen,
  operationType,
  title,
  subtitle,
  onPick,
  onClose,
  disabled = false,
  isTopOfStack,
}: WorkerPickerModalProps) {
  const [workers, setWorkers] = useState<Worker[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchWorkers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getWorkers();
      const allowedRoles = OPERATION_TO_ROLES[operationType];
      const filtered = data.filter(
        (w) => w.activo && w.roles?.some((r) => allowedRoles.includes(r))
      );
      setWorkers(filtered);
    } catch (err: unknown) {
      setError(classifyApiError(err).userMessage);
    } finally {
      setLoading(false);
    }
  }, [operationType]);

  useEffect(() => {
    if (isOpen) {
      fetchWorkers();
    }
  }, [isOpen, fetchWorkers]);

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      ariaLabel={title}
      isTopOfStack={isTopOfStack}
      className="bg-zeues-navy border-4 border-white"
    >
      <div className="flex flex-col gap-4">
        <div>
          <h2 className="text-white font-mono font-black text-xl tracking-widest uppercase">
            {title}
          </h2>
          {subtitle && (
            <p className="text-white/70 font-mono text-sm mt-1 truncate">
              {subtitle}
            </p>
          )}
        </div>

        {loading ? (
          <Loading message="CARGANDO" />
        ) : error ? (
          <div className="flex flex-col gap-3">
            <p role="alert" className="text-red-400 font-mono text-sm font-black">
              {error}
            </p>
            <button
              type="button"
              onClick={fetchWorkers}
              className="w-full h-12 font-mono font-black text-white border-2 border-white rounded cursor-pointer hover:bg-white/10 focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset text-sm"
              aria-label="Reintentar cargar trabajadores"
            >
              REINTENTAR
            </button>
          </div>
        ) : (
          <div className="flex flex-col gap-2 max-h-[50vh] overflow-y-auto">
            {workers.map((worker) => (
              <button
                key={worker.id}
                type="button"
                onClick={() => onPick(worker)}
                disabled={disabled}
                className="w-full h-16 font-mono font-black text-white bg-zeues-navy/80 border border-white/20 rounded cursor-pointer hover:bg-white/10 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset"
                aria-label={`Asignar a ${worker.nombre} ${worker.apellido || ''}`.trim()}
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

        <button
          type="button"
          onClick={onClose}
          disabled={disabled}
          className="w-full h-12 font-mono font-black text-white/70 border border-white/20 rounded cursor-pointer hover:text-white hover:border-white/40 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset text-sm"
          aria-label="Cancelar"
        >
          CANCELAR
        </button>
      </div>
    </Modal>
  );
}
