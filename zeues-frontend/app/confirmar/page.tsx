'use client';

import { Suspense, useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Image from 'next/image';
import { Puzzle, Flame, SearchCheck, ArrowLeft, X, CheckCircle, Package, Loader2, AlertCircle } from 'lucide-react';
import { useAppState } from '@/lib/context';
import {
  iniciarAccion,
  completarAccion,
  cancelarAccion,
  iniciarAccionBatch,
  completarAccionBatch,
  cancelarAccionBatch
} from '@/lib/api';
import type { ActionPayload, BatchActionRequest } from '@/lib/types';

function ConfirmarContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const tipo = searchParams.get('tipo') as 'iniciar' | 'completar' | 'cancelar';
  const { state, resetState, setState } = useAppState();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [errorType, setErrorType] = useState<'network' | 'not-found' | 'validation' | 'forbidden' | 'server' | 'generic'>('generic');

  const isBatchMode = state.batchMode && state.selectedSpools.length > 0;

  useEffect(() => {
    // Validar flujo: debe tener worker, operación, y al menos un spool (single o batch)
    const hasSingleSpool = state.selectedSpool !== null;
    const hasBatchSpools = state.selectedSpools.length > 0;

    if (!state.selectedWorker || !state.selectedOperation || !tipo || (!hasSingleSpool && !hasBatchSpools)) {
      router.push('/');
    }
  }, [state, tipo, router]);

  const handleConfirm = async () => {
    try {
      setLoading(true);
      setError('');
      setErrorType('generic');

      if (isBatchMode) {
        // v2.0: Batch mode - procesar múltiples spools
        const batchPayload: BatchActionRequest = {
          worker_id: state.selectedWorker!.id,
          operacion: state.selectedOperation as 'ARM' | 'SOLD',
          tag_spools: state.selectedSpools,
          // Solo incluir timestamp si es completar
          ...(tipo === 'completar' && { timestamp: new Date().toISOString() }),
        };

        // Llamar API batch según tipo de acción
        let batchResponse;
        if (tipo === 'iniciar') {
          batchResponse = await iniciarAccionBatch(batchPayload);
        } else if (tipo === 'completar') {
          batchResponse = await completarAccionBatch(batchPayload);
        } else {
          // tipo === 'cancelar'
          batchResponse = await cancelarAccionBatch(batchPayload);
        }

        // Guardar resultados en contexto para P6
        setState({ batchResults: batchResponse });

        // Navegar a página de éxito
        router.push('/exito');
      } else {
        // Single mode - comportamiento original
        const payload: ActionPayload = {
          worker_id: state.selectedWorker!.id,
          operacion: state.selectedOperation as 'ARM' | 'SOLD',
          tag_spool: state.selectedSpool!,
          // Solo incluir timestamp si es completar
          ...(tipo === 'completar' && { timestamp: new Date().toISOString() }),
        };

        // Llamar API según tipo de acción
        if (tipo === 'iniciar') {
          await iniciarAccion(payload);
        } else if (tipo === 'completar') {
          await completarAccion(payload);
        } else {
          // tipo === 'cancelar'
          await cancelarAccion(payload);
        }

        // Clear batch results for single mode
        setState({ batchResults: null });

        // Si llegamos aquí, la acción fue exitosa
        router.push('/exito');
      }
    } catch (err) {
      // Manejar errores específicos según código HTTP
      const errorMessage = err instanceof Error ? err.message : 'Error al procesar acción';

      if (errorMessage.includes('red') || errorMessage.includes('conexión') || errorMessage.includes('Failed to fetch')) {
        setErrorType('network');
        setError('Error de conexión con el servidor. Verifica que el backend esté disponible.');
      } else if (errorMessage.includes('404') || errorMessage.includes('no encontrado')) {
        setErrorType('not-found');
        setError(errorMessage);
      } else if (errorMessage.includes('400') || errorMessage.includes('ya iniciada') || errorMessage.includes('ya completada') || errorMessage.includes('dependencias')) {
        setErrorType('validation');
        setError(errorMessage);
      } else if (errorMessage.includes('403') || errorMessage.includes('autorizado') || errorMessage.includes('completar')) {
        setErrorType('forbidden');
        setError(errorMessage);
      } else if (errorMessage.includes('503') || errorMessage.includes('Sheets') || errorMessage.includes('servidor')) {
        setErrorType('server');
        setError('Error del servidor de Google Sheets. Intenta más tarde.');
      } else {
        setErrorType('generic');
        setError(errorMessage);
      }
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

  if (!state.selectedWorker || !state.selectedOperation || (!hasSingleSpool && !hasBatchSpools)) {
    return null;
  }

  const actionLabel = tipo === 'iniciar' ? 'INICIAR' : tipo === 'completar' ? 'COMPLETAR' : 'CANCELAR';
  const operationLabel = state.selectedOperation === 'ARM' ? 'ARMADO' :
                        state.selectedOperation === 'SOLD' ? 'SOLDADURA' : 'METROLOGÍA';

  const OperationIcon = state.selectedOperation === 'ARM' ? Puzzle :
                        state.selectedOperation === 'SOLD' ? Flame : SearchCheck;

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

          {/* Error State */}
          {error && !loading && (
            <div className="border-4 border-red-500 p-8 mb-6 bg-red-500/10">
              <div className="flex items-center gap-4 mb-4">
                <AlertCircle size={48} className="text-red-500" strokeWidth={3} />
                <h3 className="text-2xl font-black text-red-500 font-mono">ERROR</h3>
              </div>
              <p className="text-lg text-white font-mono mb-6">{error}</p>
              {(errorType === 'server' || errorType === 'network') && (
                <button
                  onClick={handleConfirm}
                  className="px-6 py-3 border-4 border-white text-white font-mono font-black active:bg-white active:text-[#001F3F]"
                >
                  REINTENTAR
                </button>
              )}
            </div>
          )}

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
          <div className="fixed bottom-0 left-0 right-0 bg-[#001F3F] z-50 border-t-4 border-white/30 p-6 tablet:p-5">
            <div className="flex gap-4 tablet:gap-3 narrow:flex-col narrow:gap-3">
              <button
                onClick={() => router.back()}
                className="flex-1 narrow:w-full h-16 bg-transparent border-4 border-white flex items-center justify-center gap-3 active:bg-white active:text-[#001F3F] transition-all group"
              >
                <ArrowLeft size={24} strokeWidth={3} className="text-white group-active:text-[#001F3F]" />
                <span className="text-xl narrow:text-lg font-black text-white font-mono tracking-[0.15em] group-active:text-[#001F3F]">
                  VOLVER
                </span>
              </button>
              <button
                onClick={handleCancel}
                className="flex-1 narrow:w-full h-16 bg-transparent border-4 border-red-500 flex items-center justify-center gap-3 active:bg-red-500 active:border-red-500 transition-all group"
              >
                <X size={24} strokeWidth={3} className="text-red-500 group-active:text-white" />
                <span className="text-xl narrow:text-lg font-black text-red-500 font-mono tracking-[0.15em] group-active:text-white">
                  INICIO
                </span>
              </button>
            </div>
          </div>
        </div>
      </div>
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
