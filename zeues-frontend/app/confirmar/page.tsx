'use client';

import { Suspense, useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Image from 'next/image';
import { Puzzle, Flame, SearchCheck, ArrowLeft, X, CheckCircle, Package, Loader2, AlertCircle } from 'lucide-react';
import { useAppState } from '@/lib/context';
import { Modal } from '@/components/Modal';
import { FixedFooter } from '@/components';
import {
  tomarOcupacion,
  pausarOcupacion,
  completarOcupacion,
  tomarOcupacionBatch,
  tomarReparacion,
  pausarReparacion,
  completarReparacion,
  cancelarReparacion,
  iniciarSpool,
  finalizarSpool
} from '@/lib/api';
import type {
  TomarRequest,
  PausarRequest,
  CompletarRequest,
  BatchTomarRequest,
  BatchOccupationResponse,
  IniciarRequest,
  FinalizarRequest
} from '@/lib/types';

/**
 * Formatea una fecha en formato DD-MM-YYYY para el backend.
 *
 * @param date - Date object a formatear
 * @returns String en formato DD-MM-YYYY (e.g., "28-01-2026")
 *
 * @example
 * formatDateDDMMYYYY(new Date(2026, 0, 28)) // "28-01-2026"
 */
const formatDateDDMMYYYY = (date: Date): string => {
  const day = String(date.getDate()).padStart(2, '0');
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const year = date.getFullYear();
  return `${day}-${month}-${year}`;
};

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
  const [error, setError] = useState('');
  const [errorType, setErrorType] = useState<'network' | 'not-found' | 'validation' | 'forbidden' | 'server' | 'generic'>('generic');
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
    const errorMessage = error instanceof Error ? error.message : 'Error desconocido';

    if (errorMessage.includes('409') || errorMessage.includes('Conflicto')) {
      // Race condition - unions changed, need to reload
      setCountdown(2);
      setErrorModal({
        title: 'Datos desactualizados',
        message: `Las uniones disponibles han cambiado. Recargando${countdown !== null ? ` en ${countdown}s` : ''}...`,
        action: () => {
          router.push('/seleccionar-uniones');
        }
      });
    } else if (errorMessage.includes('403') || errorMessage.includes('autorizado') || errorMessage.includes('permisos')) {
      // Ownership validation failed
      setErrorModal({
        title: 'Error de permisos',
        message: 'No eres el dueño de este spool. Este spool está ocupado por otro trabajador.',
        action: () => router.push('/seleccionar-spool')
      });
    } else {
      // Generic error
      setErrorModal({
        title: 'Error',
        message: errorMessage || 'Ocurrió un error. Por favor intenta nuevamente.',
        action: () => setErrorModal(null)
      });
    }
  };

  const handleConfirm = async () => {
    try {
      setLoading(true);
      setError('');
      setErrorType('generic');

      // Check for v4.0 INICIAR flow (single mode only)
      if (state.accion === 'INICIAR' && !isBatchMode) {
        // v4.0: INICIAR flow - occupy spool with Ocupado_Por + Fecha_Ocupacion
        const worker_id = state.selectedWorker!.id;
        const worker_nombre = state.selectedWorker!.nombre_completo; // Format: "INICIALES(ID)"
        const tag_spool = state.selectedSpool!;
        const operacion = state.selectedOperation as 'ARM' | 'SOLD';

        const payload: IniciarRequest = {
          tag_spool,
          worker_id,
          worker_nombre,
          operacion,
        };

        await iniciarSpool(payload);

        // Navigate to success (no need to store extra data for INICIAR)
        router.push('/exito');
      } else if (state.accion === 'FINALIZAR' && !isBatchMode) {
        // v4.0: FINALIZAR flow with union selection
        const worker_id = state.selectedWorker!.id;
        const tag_spool = state.selectedSpool!;
        const operacion = state.selectedOperation as 'ARM' | 'SOLD' | 'REPARACION';

        // REPARACION uses v3.0 endpoint (no union selection, uses state machine)
        if (operacion === 'REPARACION') {
          await completarReparacion({
            tag_spool,
            worker_id,
          });
          router.push('/exito');
        } else {
          // ARM/SOLD use v4.0 endpoint with union selection
          const payload: FinalizarRequest = {
            tag_spool,
            worker_id,
            operacion,
            selected_unions: state.selectedUnions, // Already union IDs (format: "OT-123+5")
          };

          const response = await finalizarSpool(payload);

          // Store pulgadas for success page (backend field name is "pulgadas", not "pulgadas_completadas")
          setState({ pulgadasCompletadas: response.pulgadas || 0 });

          // Clear session storage on success
          if (state.selectedSpool) {
            sessionStorage.removeItem(`unions_selection_${state.selectedSpool}`);
          }

          // Navigate to success
          router.push('/exito');
        }
      } else if (isBatchMode) {
        // v3.0: Batch mode - procesar múltiples spools
        const worker_nombre = state.selectedWorker!.nombre_completo; // Format: "INICIALES(ID)"
        const worker_id = state.selectedWorker!.id;
        const operacion = state.selectedOperation as 'ARM' | 'SOLD' | 'METROLOGIA' | 'REPARACION';
        let batchResponse: BatchOccupationResponse;

        if (tipo === 'tomar') {
          // v3.0: TOMAR
          if (operacion === 'REPARACION') {
            // REPARACION: Use individual reparación endpoints (no batch endpoint exists)
            const results = await Promise.allSettled(
              state.selectedSpools.map(tag_spool =>
                tomarReparacion({
                  tag_spool,
                  worker_id,
                })
              )
            );
            batchResponse = {
              total: results.length,
              succeeded: results.filter(r => r.status === 'fulfilled').length,
              failed: results.filter(r => r.status === 'rejected').length,
              details: results.map((r, i) => ({
                success: r.status === 'fulfilled',
                tag_spool: state.selectedSpools[i],
                message: r.status === 'fulfilled' ? 'Spool tomado exitosamente' : (r.reason?.message || 'Error desconocido'),
              })),
            };
          } else {
            // ARM/SOLD/METROLOGIA: Use batch endpoint
            const batchPayload: BatchTomarRequest = {
              tag_spools: state.selectedSpools,
              worker_id,
              worker_nombre,
              operacion,
            };
            batchResponse = await tomarOcupacionBatch(batchPayload);
          }
        } else if (tipo === 'pausar') {
          // v3.0: PAUSAR
          if (operacion === 'REPARACION') {
            // REPARACION: Use reparación-specific endpoint
            const results = await Promise.allSettled(
              state.selectedSpools.map(tag_spool =>
                pausarReparacion({
                  tag_spool,
                  worker_id,
                })
              )
            );
            batchResponse = {
              total: results.length,
              succeeded: results.filter(r => r.status === 'fulfilled').length,
              failed: results.filter(r => r.status === 'rejected').length,
              details: results.map((r, i) => ({
                success: r.status === 'fulfilled',
                tag_spool: state.selectedSpools[i],
                message: r.status === 'fulfilled' ? 'Spool pausado exitosamente' : (r.reason?.message || 'Error desconocido'),
              })),
            };
          } else {
            // ARM/SOLD: Use general pausar endpoint
            const results = await Promise.allSettled(
              state.selectedSpools.map(tag_spool =>
                pausarOcupacion({
                  tag_spool,
                  worker_id,
                  worker_nombre,
                  operacion,
                })
              )
            );
            batchResponse = {
              total: results.length,
              succeeded: results.filter(r => r.status === 'fulfilled').length,
              failed: results.filter(r => r.status === 'rejected').length,
              details: results.map((r, i) => ({
                success: r.status === 'fulfilled',
                tag_spool: state.selectedSpools[i],
                message: r.status === 'fulfilled' ? r.value.message : (r.reason?.message || 'Error desconocido'),
              })),
            };
          }
        } else if (tipo === 'completar') {
          // v3.0: COMPLETAR
          if (operacion === 'REPARACION') {
            // REPARACION: Use reparación-specific endpoint
            const results = await Promise.allSettled(
              state.selectedSpools.map(tag_spool =>
                completarReparacion({
                  tag_spool,
                  worker_id,
                })
              )
            );
            batchResponse = {
              total: results.length,
              succeeded: results.filter(r => r.status === 'fulfilled').length,
              failed: results.filter(r => r.status === 'rejected').length,
              details: results.map((r, i) => ({
                success: r.status === 'fulfilled',
                tag_spool: state.selectedSpools[i],
                message: r.status === 'fulfilled' ? 'Reparación completada exitosamente' : (r.reason?.message || 'Error desconocido'),
              })),
            };
          } else {
            // ARM/SOLD: COMPLETAR requiere fecha_operacion - llamar individualmente
            const fecha_operacion = formatDateDDMMYYYY(new Date()); // DD-MM-YYYY format
            const results = await Promise.allSettled(
              state.selectedSpools.map(tag_spool =>
                completarOcupacion({
                  tag_spool,
                  worker_id,
                  worker_nombre,
                  fecha_operacion,
                })
              )
            );
            batchResponse = {
              total: results.length,
              succeeded: results.filter(r => r.status === 'fulfilled').length,
              failed: results.filter(r => r.status === 'rejected').length,
              details: results.map((r, i) => ({
                success: r.status === 'fulfilled',
                tag_spool: state.selectedSpools[i],
                message: r.status === 'fulfilled' ? r.value.message : (r.reason?.message || 'Error desconocido'),
              })),
            };
          }
        } else if (tipo === 'cancelar') {
          // v3.0: CANCELAR (REPARACION only)
          if (operacion !== 'REPARACION') {
            throw new Error('CANCELAR solo está disponible para REPARACIÓN');
          }
          const results = await Promise.allSettled(
            state.selectedSpools.map(tag_spool =>
              cancelarReparacion({
                tag_spool,
                worker_id,
              })
            )
          );
          batchResponse = {
            total: results.length,
            succeeded: results.filter(r => r.status === 'fulfilled').length,
            failed: results.filter(r => r.status === 'rejected').length,
            details: results.map((r, i) => ({
              success: r.status === 'fulfilled',
              tag_spool: state.selectedSpools[i],
              message: r.status === 'fulfilled' ? 'Reparación cancelada exitosamente' : (r.reason?.message || 'Error desconocido'),
            })),
          };
        } else {
          throw new Error('Tipo de acción no soportado');
        }

        // Store batch response in context (inline type after BatchActionResponse removal)
        const convertedResponse = {
          total: batchResponse.total,
          succeeded: batchResponse.succeeded,
          failed: batchResponse.failed,
          details: batchResponse.details,
        };

        // Guardar resultados en contexto para P6
        setState({ batchResults: convertedResponse });

        // Navegar a página de éxito
        router.push('/exito');
      } else {
        // v3.0: Single mode - usar endpoints v3.0 occupation
        const worker_nombre = state.selectedWorker!.nombre_completo; // Format: "INICIALES(ID)"
        const worker_id = state.selectedWorker!.id;
        const tag_spool = state.selectedSpool!;
        const operacion = state.selectedOperation as 'ARM' | 'SOLD' | 'METROLOGIA' | 'REPARACION';

        if (tipo === 'tomar') {
          // v3.0: TOMAR
          if (operacion === 'REPARACION') {
            // REPARACION: Use reparación-specific endpoint
            await tomarReparacion({
              tag_spool,
              worker_id,
            });
          } else {
            // ARM/SOLD/METROLOGIA: Use general occupation endpoint
            const payload: TomarRequest = {
              tag_spool,
              worker_id,
              worker_nombre,
              operacion,
            };
            await tomarOcupacion(payload);
          }
        } else if (tipo === 'pausar') {
          // v3.0: PAUSAR
          if (operacion === 'REPARACION') {
            // REPARACION: Use reparación-specific endpoint
            await pausarReparacion({
              tag_spool,
              worker_id,
            });
          } else {
            // ARM/SOLD: Use general pausar endpoint
            const payload: PausarRequest = {
              tag_spool,
              worker_id,
              worker_nombre,
              operacion,
            };
            await pausarOcupacion(payload);
          }
        } else if (tipo === 'completar') {
          // v3.0: COMPLETAR
          if (operacion === 'REPARACION') {
            // REPARACION: Use reparación-specific endpoint
            await completarReparacion({
              tag_spool,
              worker_id,
            });
          } else {
            // ARM/SOLD: COMPLETAR con fecha_operacion requerida
            const payload: CompletarRequest = {
              tag_spool,
              worker_id,
              worker_nombre,
              fecha_operacion: formatDateDDMMYYYY(new Date()), // DD-MM-YYYY format
            };
            await completarOcupacion(payload);
          }
        } else if (tipo === 'cancelar') {
          // v3.0: CANCELAR (REPARACION only)
          if (operacion !== 'REPARACION') {
            throw new Error('CANCELAR solo está disponible para REPARACIÓN');
          }
          await cancelarReparacion({
            tag_spool,
            worker_id,
          });
        } else {
          throw new Error('Tipo de acción no soportado');
        }

        // Clear batch results for single mode
        setState({ batchResults: null });

        // Si llegamos aquí, la acción fue exitosa
        router.push('/exito');
      }
    } catch (err) {
      // v4.0: Use new error handler for INICIAR/FINALIZAR, fallback to v3.0 for other actions
      if (state.accion === 'INICIAR' || state.accion === 'FINALIZAR') {
        handleApiError(err);
      } else {
        // v3.0: Manejar errores específicos según código HTTP (incluye nuevos códigos)
        const errorMessage = err instanceof Error ? err.message : 'Error al procesar acción';

        if (errorMessage.includes('red') || errorMessage.includes('conexión') || errorMessage.includes('Failed to fetch')) {
          setErrorType('network');
          setError('Error de conexión con el servidor. Verifica que el backend esté disponible.');
        } else if (errorMessage.includes('ocupado') || errorMessage.includes('409')) {
          // v3.0: 409 CONFLICT - Spool occupied by another worker (LOC-04 requirement)
          setErrorType('forbidden');
          setError('Este spool está siendo usado por otro trabajador. Intenta más tarde.');
        } else if (errorMessage.includes('expiró') || errorMessage.includes('410')) {
          // v3.0: 410 GONE - Lock expired (worker took too long)
          setErrorType('validation');
          setError('La operación tardó demasiado tiempo. Por favor vuelve a intentar.');
        } else if (errorMessage.includes('404') || errorMessage.includes('no encontrado')) {
          setErrorType('not-found');
          setError(errorMessage);
        } else if (errorMessage.includes('400') || errorMessage.includes('ya iniciada') || errorMessage.includes('ya completada') || errorMessage.includes('dependencias') || errorMessage.includes('Requisitos')) {
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
