'use client';

import React, { useEffect, useRef, useState } from 'react';
import { Modal } from './Modal';
import { getWorkers, completarMetrologia } from '@/lib/api';
import { OPERATION_TO_ROLES } from '@/lib/operation-config';
import { classifyApiError } from '@/lib/error-classifier';
import { hapticTap } from '@/lib/haptic';
import type { Worker, SpoolCardData } from '@/lib/types';

// ─── Types ────────────────────────────────────────────────────────────────────

interface MetrologiaModalProps {
  isOpen: boolean;
  spool: SpoolCardData;
  onComplete: (resultado: 'APROBADO' | 'RECHAZADO') => void;
  onClose: () => void;
  isTopOfStack?: boolean;
}

type Step = 'resultado' | 'worker';

// ─── Component ────────────────────────────────────────────────────────────────

export function MetrologiaModal({
  isOpen,
  spool,
  onComplete,
  onClose,
  isTopOfStack,
}: MetrologiaModalProps) {
  const [step, setStep] = useState<Step>('resultado');
  const [resultado, setResultado] = useState<'APROBADO' | 'RECHAZADO' | null>(null);
  const [workers, setWorkers] = useState<Worker[]>([]);
  const [fetchLoading, setFetchLoading] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [apiLoading, setApiLoading] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const lastWorkerRef = useRef<Worker | null>(null);

  function fetchWorkers() {
    setFetchLoading(true);
    setFetchError(null);

    const allowedRoles = OPERATION_TO_ROLES['METROLOGIA'];
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

  // Reset flow when modal opens/closes; fetch workers on open
  useEffect(() => {
    if (!isOpen) {
      setStep('resultado');
      setResultado(null);
      setApiError(null);
      lastWorkerRef.current = null;
      return;
    }

    // Prefetch workers when modal opens
    fetchWorkers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen]);

  function handleResultadoSelect(chosen: 'APROBADO' | 'RECHAZADO') {
    hapticTap();
    setResultado(chosen);
    setApiError(null);
    lastWorkerRef.current = null;
    setStep('worker');
  }

  function handleBack() {
    setStep('resultado');
    setResultado(null);
    setApiError(null);
    lastWorkerRef.current = null;
  }

  async function handleWorkerClick(worker: Worker) {
    if (apiLoading || !resultado) return;
    lastWorkerRef.current = worker;
    setApiLoading(true);
    setApiError(null);

    try {
      await completarMetrologia(spool.tag_spool, worker.id, resultado);
      onComplete(resultado);
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

  const title = step === 'resultado' ? 'RESULTADO METROLOGIA' : 'SELECCIONAR INSPECTOR';

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      ariaLabel="Completar inspección de metrología"
      className="bg-zeues-navy border-4 border-white"
      isTopOfStack={isTopOfStack}
    >
      <div className="flex flex-col gap-4">
        {/* Header */}
        <div>
          <h2 className="text-white font-mono font-black text-xl tracking-widest uppercase">
            {title}
          </h2>
          <p className="text-white/70 font-mono text-sm mt-1">
            {spool.tag_spool}
            {step === 'worker' && resultado && (
              <span className={resultado === 'APROBADO' ? ' text-green-400' : ' text-red-400'}>
                {' '}— {resultado === 'APROBADO' ? 'APROBADA' : 'RECHAZADA'}
              </span>
            )}
          </p>
        </div>

        {/* Step 1: Resultado selection */}
        {step === 'resultado' && (
          <div className="flex flex-col gap-3">
            <button
              onClick={() => handleResultadoSelect('APROBADO')}
              className="w-full h-16 font-mono font-black border-2 border-green-400 text-green-400 rounded cursor-pointer hover:bg-green-400/10 focus:outline-none focus:ring-2 focus:ring-green-400 focus:ring-inset"
              aria-label="Marcar como APROBADA"
            >
              APROBADA
            </button>
            <button
              onClick={() => handleResultadoSelect('RECHAZADO')}
              className="w-full h-16 font-mono font-black border-2 border-red-400 text-red-400 rounded cursor-pointer hover:bg-red-400/10 focus:outline-none focus:ring-2 focus:ring-red-400 focus:ring-inset"
              aria-label="Marcar como RECHAZADA"
            >
              RECHAZADA
            </button>
          </div>
        )}

        {/* Step 2: Worker selection */}
        {step === 'worker' && (
          <div className="flex flex-col gap-2">
            {fetchLoading ? (
              <p className="text-white/70 font-mono text-sm text-center py-4" role="status" aria-label="Cargando"><span aria-hidden="true">CARGANDO...</span></p>
            ) : fetchError ? (
              <div className="flex flex-col gap-3">
                <p role="alert" className="text-red-400 font-mono text-sm font-black">
                  {fetchError}
                </p>
                <button
                  onClick={fetchWorkers}
                  className="w-full h-12 font-mono font-black text-white border-2 border-white rounded cursor-pointer hover:bg-white/10 focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset text-sm"
                  aria-label="Reintentar cargar inspectores"
                >
                  REINTENTAR
                </button>
              </div>
            ) : (
              workers.map((worker) => (
                <button
                  key={worker.id}
                  onClick={() => handleWorkerClick(worker)}
                  disabled={apiLoading}
                  className="w-full h-16 font-mono font-black text-white bg-zeues-navy/80 border border-white/20 rounded cursor-pointer hover:bg-white/10 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset"
                  aria-label={`Seleccionar inspector ${worker.nombre} ${worker.apellido || ''}`.trim()}
                >
                  {worker.nombre} {worker.apellido || ''}
                </button>
              ))
            )}

            {!fetchLoading && !fetchError && workers.length === 0 && (
              <p className="text-white/70 font-mono text-sm text-center py-4">
                No hay inspectores disponibles
              </p>
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
                  aria-label="Reintentar la inspección"
                >
                  REINTENTAR
                </button>
              </div>
            )}

            {/* Back button */}
            <button
              onClick={handleBack}
              disabled={apiLoading}
              className="w-full h-12 font-mono font-black text-white/70 border border-white/20 rounded cursor-pointer hover:text-white hover:border-white/40 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset text-sm mt-1"
              aria-label="Volver a selección de resultado"
            >
              VOLVER
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
