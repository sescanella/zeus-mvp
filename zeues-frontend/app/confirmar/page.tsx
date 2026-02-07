'use client';

import { Suspense, useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Image from 'next/image';
import { ArrowLeft, X, CheckCircle, Package, Loader2 } from 'lucide-react';
import { useAppState } from '@/lib/context';
import { Modal } from '@/components/Modal';
import { FixedFooter } from '@/components';
import { OPERATION_ICONS } from '@/lib/operation-config';
import { classifyApiError } from '@/lib/error-classifier';
import {
  // REPARACION operations (Phase 6)
  tomarReparacion,
  pausarReparacion,
  completarReparacion,
  cancelarReparacion,
  // v4.0 operations (INICIAR/FINALIZAR)
  iniciarSpool,
  finalizarSpool
} from '@/lib/api';
import type {
  IniciarRequest,
  FinalizarRequest
} from '@/lib/types';

// Internal type for batch results (REPARACION only now - v3.0 occupation batch removed)
interface BatchResult {
  total: number;
  succeeded: number;
  failed: number;
  details: Array<{ success: boolean; tag_spool: string; message: string }>;
}

interface ErrorModalState {
  title: string;
  message: string;
  action: () => void;
}

function ConfirmarContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  // v3.0: Use selectedTipo from context instead of query param (legacy support: map 'iniciar' → 'tomar')
  const queryTipo = searchParams.get('tipo') as 'iniciar' | 'tomar' | 'pausar' | 'completar' | 'cancelar' | null;
  const { state, resetState, setState } = useAppState();

  // Map legacy 'iniciar' to v3.0 'tomar' (backward compatibility)
  const tipo = queryTipo === 'iniciar' ? 'tomar' : (state.selectedTipo || queryTipo) as 'tomar' | 'pausar' | 'completar' | 'cancelar' | null;

  const [loading, setLoading] = useState(false);
  const [errorModal, setErrorModal] = useState<ErrorModalState | null>(null);
  const [countdown, setCountdown] = useState<number | null>(null);

  const isBatchMode = state.batchMode && state.selectedSpools.length > 0;

  useEffect(() => {
    // Validar flujo: debe tener worker, operación, y al menos un spool (single o batch)
    const hasSingleSpool = state.selectedSpool !== null;
    const hasBatchSpools = state.selectedSpools.length > 0;

    // v4.0: INICIAR/FINALIZAR flows don't use 'tipo', they use state.accion
    const isV4Flow = state.accion === 'INICIAR' || state.accion === 'FINALIZAR';
    const hasValidTipo = tipo !== null || isV4Flow;

    if (!state.selectedWorker || !state.selectedOperation || !hasValidTipo || (!hasSingleSpool && !hasBatchSpools)) {
      router.push('/');
    }
  }, [state, tipo, router]);

  // Countdown effect for auto-reload (409 case)
  useEffect(() => {
    if (countdown !== null && countdown > 0) {
      const timer = setTimeout(() => setCountdown(countdown - 1), 1000);
      return () => clearTimeout(timer);
    } else if (countdown === 0) {
      router.push('/seleccionar-uniones');
    }
  }, [countdown, router]);

  // Clear error modal on unmount
  useEffect(() => {
    return () => {
      setErrorModal(null);
    };
  }, []);

  const handleApiError = (error: unknown) => {
    const classified = classifyApiError(error);

    if (classified.type === 'conflict') {
      // Race condition - unions changed, need to reload
      if (classified.retryDelay) {
        setCountdown(Math.floor(classified.retryDelay / 1000));
      }
      setErrorModal({
        title: 'Datos desactualizados',
        message: `Las uniones disponibles han cambiado. Recargando${countdown !== null ? ` en ${countdown}s` : ''}...`,
        action: () => {
          router.push('/seleccionar-uniones');
        }
      });
    } else if (classified.type === 'forbidden') {
      // Ownership validation failed
      setErrorModal({
        title: 'Error de permisos',
        message: classified.userMessage,
        action: () => router.push('/seleccionar-spool')
      });
    } else {
      // Generic error
      setErrorModal({
        title: 'Error',
        message: classified.userMessage,
        action: () => setErrorModal(null)
      });
    }
  };

  const handleConfirm = async () => {
    try {
      setLoading(true);

      const worker_id = state.selectedWorker!.id;
      const worker_nombre = state.selectedWorker!.nombre_completo;
      const operacion = state.selectedOperation as 'ARM' | 'SOLD' | 'REPARACION';

      // v4.0: INICIAR flow (single or batch mode)
      if (state.accion === 'INICIAR') {
        if (isBatchMode) {
          // Batch INICIAR: call iniciarSpool in a loop
          const results = await Promise.allSettled(
            state.selectedSpools.map(tag_spool =>
              operacion === 'REPARACION'
                ? tomarReparacion({ tag_spool, worker_id })
                : iniciarSpool({
                    tag_spool,
                    worker_id,
                    worker_nombre,
                    operacion: operacion as 'ARM' | 'SOLD',
                  })
            )
          );

          const batchResponse: BatchResult = {
            total: results.length,
            succeeded: results.filter(r => r.status === 'fulfilled').length,
            failed: results.filter(r => r.status === 'rejected').length,
            details: results.map((r, i) => ({
              success: r.status === 'fulfilled',
              tag_spool: state.selectedSpools[i],
              message: r.status === 'fulfilled' ? 'Spool iniciado exitosamente' : ((r as PromiseRejectedResult).reason?.message || 'Error desconocido'),
            })),
          };

          setState({ batchResults: batchResponse });
          router.push('/exito');
        } else {
          // Single INICIAR
          const tag_spool = state.selectedSpool!;

          if (operacion === 'REPARACION') {
            await tomarReparacion({ tag_spool, worker_id });
          } else {
            const payload: IniciarRequest = {
              tag_spool,
              worker_id,
              worker_nombre,
              operacion,
            };
            await iniciarSpool(payload);
          }

          setState({ batchResults: null });
          router.push('/exito');
        }
      }
      // v4.0: FINALIZAR flow (single mode only for ARM/SOLD, batch for REPARACION)
      else if (state.accion === 'FINALIZAR') {
        const tag_spool = state.selectedSpool!;

        if (operacion === 'REPARACION') {
          // REPARACION uses dedicated endpoint (no union selection)
          await completarReparacion({ tag_spool, worker_id });
          setState({ batchResults: null });
          router.push('/exito');
        } else {
          // ARM/SOLD use v4.0 endpoint with union selection
          const payload: FinalizarRequest = {
            tag_spool,
            worker_id,
            operacion,
            selected_unions: state.selectedUnions,
          };

          const response = await finalizarSpool(payload);

          setState({ pulgadasCompletadas: response.pulgadas || 0 });

          if (state.selectedSpool) {
            sessionStorage.removeItem(`unions_selection_${state.selectedSpool}`);
          }

          router.push('/exito');
        }
      }
      // REPARACION-specific actions: PAUSAR and CANCELAR (use tipo from query param)
      else if (operacion === 'REPARACION' && tipo) {
        if (isBatchMode) {
          let results: PromiseSettledResult<unknown>[];
          let successMessage: string;

          if (tipo === 'pausar') {
            results = await Promise.allSettled(
              state.selectedSpools.map(tag_spool =>
                pausarReparacion({ tag_spool, worker_id })
              )
            );
            successMessage = 'Reparación pausada exitosamente';
          } else if (tipo === 'cancelar') {
            results = await Promise.allSettled(
              state.selectedSpools.map(tag_spool =>
                cancelarReparacion({ tag_spool, worker_id })
              )
            );
            successMessage = 'Reparación cancelada exitosamente';
          } else {
            throw new Error('Acción no soportada para REPARACIÓN');
          }

          const batchResponse: BatchResult = {
            total: results.length,
            succeeded: results.filter(r => r.status === 'fulfilled').length,
            failed: results.filter(r => r.status === 'rejected').length,
            details: results.map((r, i) => ({
              success: r.status === 'fulfilled',
              tag_spool: state.selectedSpools[i],
              message: r.status === 'fulfilled' ? successMessage : ((r as PromiseRejectedResult).reason?.message || 'Error desconocido'),
            })),
          };

          setState({ batchResults: batchResponse });
          router.push('/exito');
        } else {
          const tag_spool = state.selectedSpool!;

          if (tipo === 'pausar') {
            await pausarReparacion({ tag_spool, worker_id });
          } else if (tipo === 'cancelar') {
            await cancelarReparacion({ tag_spool, worker_id });
          } else {
            throw new Error('Acción no soportada para REPARACIÓN');
          }

          setState({ batchResults: null });
          router.push('/exito');
        }
      } else {
        throw new Error('Flujo no reconocido. Vuelve a iniciar.');
      }
    } catch (err) {
      console.error('Error al confirmar acción:', err);
      handleApiError(err);
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    if (confirm('¿Seguro que quieres cancelar? Se perderá toda la información.')) {
      resetState();
      router.push('/');
    }
  };

  // Guard: must have worker, operation, and at least one spool
  const hasSingleSpool = state.selectedSpool !== null;
  const hasBatchSpools = state.selectedSpools.length > 0;

  // v4.0: INICIAR/FINALIZAR flows don't use 'tipo', they use state.accion
  const isV4Flow = state.accion === 'INICIAR' || state.accion === 'FINALIZAR';
  const hasValidTipo = tipo !== null || isV4Flow;

  if (!state.selectedWorker || !state.selectedOperation || !hasValidTipo || (!hasSingleSpool && !hasBatchSpools)) {
    return null;
  }

  // v3.0/v4.0: Action labels for UI
  const actionLabel =
    state.accion === 'INICIAR' ? 'INICIAR' :
    state.accion === 'FINALIZAR' ? 'FINALIZAR' :
    tipo === 'tomar' ? 'TOMAR' :
    tipo === 'pausar' ? 'PAUSAR' :
    tipo === 'completar' ? 'COMPLETAR' :
    tipo === 'cancelar' ? 'CANCELAR' : 'ACCIÓN';

  const operationLabel =
    state.selectedOperation === 'ARM' ? 'ARMADO' :
    state.selectedOperation === 'SOLD' ? 'SOLDADURA' :
    state.selectedOperation === 'METROLOGIA' ? 'METROLOGÍA' :
    state.selectedOperation === 'REPARACION' ? 'REPARACIÓN' : 'OPERACIÓN';

  const OperationIcon = OPERATION_ICONS[state.selectedOperation];

  const spoolsList = isBatchMode ? state.selectedSpools : [state.selectedSpool];
  const spoolCount = spoolsList.length;

  return (
    <div
      className="min-h-screen bg-[#001F3F]"
      style={{
        backgroundImage: `
          linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
          linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)
        `,
        backgroundSize: '50px 50px'
      }}
    >
      {/* Logo */}
      <div className="flex justify-center pt-8 pb-6 tablet:header-compact border-b-4 border-white/30">
        <Image
          src="/logos/logo-grisclaro-F8F9FA.svg"
          alt="Kronos Mining"
          width={200}
          height={80}
          priority
        />
      </div>

      {/* Header */}
      <div className="px-10 tablet:px-6 narrow:px-5 py-6 tablet:py-4 border-b-4 border-white/30">
        <div className="flex items-center justify-center gap-4">
          <OperationIcon size={48} strokeWidth={3} className="text-zeues-orange" />
          <h2 className="text-3xl narrow:text-2xl font-black text-white tracking-[0.25em] font-mono">
            {operationLabel} - {actionLabel}
          </h2>
        </div>
      </div>

      {/* Content */}
      <div className="p-8 tablet:p-5 tablet:pb-footer">
        <div className="max-w-4xl mx-auto">
          {/* Info secundaria compacta */}
          <div className="flex items-center justify-center gap-6 tablet:gap-4 mb-6 tablet:mb-4 text-center">
            <span className="text-base font-black text-white/60 font-mono">
              {state.selectedWorker.nombre_completo}
            </span>
            <div className="h-6 w-px bg-white/30"></div>
            <span className="text-base font-black text-white/60 font-mono">{operationLabel}</span>
          </div>

          {/* Loading State */}
          {loading && (
            <div className="flex flex-col items-center justify-center py-20 mb-6">
              <Loader2 size={64} className="text-zeues-orange animate-spin mb-4" strokeWidth={3} />
              <span className="text-xl font-black text-white font-mono">PROCESANDO...</span>
              <span className="text-base font-black text-white/60 font-mono mt-2">Actualizando Google Sheets</span>
            </div>
          )}

          {/* Lista de spools */}
          {!loading && (
            <>
              <div className="border-4 border-white mb-8 tablet:mb-6">
                {/* Header con count */}
                <div className="border-b-4 border-white bg-white/5 p-5 narrow:p-4 flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <Package size={40} strokeWidth={3} className="text-white" />
                    <h3 className="text-2xl narrow:text-xl font-black text-white font-mono tracking-[0.2em]">
                      {isBatchMode ? 'SPOOLS SELECCIONADOS' : 'SPOOL SELECCIONADO'}
                    </h3>
                  </div>
                  <div className="w-16 h-16 bg-white/10 border-4 border-white flex items-center justify-center">
                    <span className="text-3xl narrow:text-2xl font-black text-white font-mono">{spoolCount}</span>
                  </div>
                </div>

                {/* Lista scrollable grande */}
                <div className="max-h-96 overflow-y-auto custom-scrollbar">
                  {spoolsList.map((tag, index) => (
                    <div
                      key={tag}
                      className="h-16 border-b-2 border-white/30 last:border-b-0 flex items-center px-6 gap-5 hover:bg-white/5"
                    >
                      <div className="w-12 h-12 bg-white/10 border-2 border-white flex items-center justify-center">
                        <span className="text-xl font-black text-white font-mono">{index + 1}</span>
                      </div>
                      <span className="text-2xl narrow:text-xl font-black text-white font-mono flex-1">{tag}</span>
                      <CheckCircle size={28} strokeWidth={3} className="text-green-500" />
                    </div>
                  ))}
                </div>
              </div>

              {/* v4.0: Show selected unions count for FINALIZAR */}
              {state.accion === 'FINALIZAR' && (
                <div className="border-4 border-white/30 p-6 mb-8 bg-white/5">
                  <div className="text-center mb-4">
                    <span className="text-sm font-black text-white/50 font-mono">UNIONES SELECCIONADAS:</span>
                  </div>
                  <div className="text-center mb-2">
                    <span className="text-4xl font-black text-white font-mono">{state.selectedUnions.length}</span>
                    <span className="text-lg font-black text-white/60 font-mono ml-2">uniones</span>
                  </div>
                  <div className="text-center">
                    <span className="text-2xl font-black text-zeues-orange font-mono">
                      {state.pulgadasCompletadas.toFixed(1)}&quot;
                    </span>
                    <span className="text-sm font-black text-white/60 font-mono ml-2">pulgadas-diámetro</span>
                  </div>
                </div>
              )}

              {/* Fecha si es completar */}
              {tipo === 'completar' && (
                <div className="border-2 border-white/30 p-4 mb-8 text-center">
                  <span className="text-sm font-black text-white/50 font-mono">FECHA: </span>
                  <span className="text-lg font-black text-white font-mono">{new Date().toLocaleDateString('es-ES')}</span>
                </div>
              )}

              {/* Botón CONFIRMAR - único elemento naranja grande */}
              <button
                onClick={handleConfirm}
                disabled={loading}
                className="w-full h-24 mb-6 tablet:mb-4 bg-zeues-orange border-4 border-zeues-orange flex items-center justify-center gap-4 cursor-pointer active:bg-zeues-orange/80 transition-all disabled:opacity-50 group"
              >
                <CheckCircle size={48} strokeWidth={3} className="text-white" />
                <span className="text-3xl narrow:text-2xl font-black text-white font-mono tracking-[0.25em]">
                  CONFIRMAR {spoolCount} SPOOL{spoolCount !== 1 ? 'S' : ''}
                </span>
              </button>
            </>
          )}

          {/* Fixed Navigation Footer */}
          <FixedFooter
            backButton={{
              text: "VOLVER",
              onClick: () => router.back(),
              icon: <ArrowLeft size={24} strokeWidth={3} />
            }}
            primaryButton={{
              text: "INICIO",
              onClick: handleCancel,
              variant: "danger",
              icon: <X size={24} strokeWidth={3} />
            }}
          />
        </div>
      </div>

      {/* Error Modal (v4.0) */}
      {errorModal && (
        <Modal
          isOpen={true}
          onClose={() => setErrorModal(null)}
          onBackdropClick={null}
        >
          <div className="text-center">
            <h3 className="text-lg font-semibold mb-4 text-red-600">
              {errorModal.title}
            </h3>
            <p className="text-gray-600 mb-6">
              {errorModal.message}
            </p>
            <button
              onClick={errorModal.action}
              className="h-14 px-8 bg-zeues-orange border-4 border-zeues-orange text-white font-mono font-black active:bg-zeues-orange/80 transition-all"
            >
              {errorModal.title === 'Datos desactualizados' ? 'Recargar' : 'Aceptar'}
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}

export default function ConfirmarPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-[#001F3F] flex items-center justify-center">
        <Loader2 size={64} className="text-zeues-orange animate-spin" strokeWidth={3} />
      </div>
    }>
      <ConfirmarContent />
    </Suspense>
  );
}
