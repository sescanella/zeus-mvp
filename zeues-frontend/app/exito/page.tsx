'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';
import { CheckCircle, AlertCircle } from 'lucide-react';
import { useAppState } from '@/lib/context';

export default function ExitoPage() {
  const router = useRouter();
  const { state, resetState, resetV4State } = useAppState();
  const [countdown, setCountdown] = useState(5);

  const tipo = state.selectedTipo;
  const accion = state.accion;
  const selectedUnions = state.selectedUnions;
  const pulgadasCompletadas = state.pulgadasCompletadas;
  const selectedSpool = state.selectedSpool;
  const selectedWorker = state.selectedWorker;
  const selectedOperation = state.selectedOperation;

  const handleFinish = useCallback(() => {
    resetState();
    router.push('/');
  }, [resetState, router]);

  const handleNewWork = useCallback(() => {
    // Clear all state
    resetState();
    router.push('/');
  }, [resetState, router]);

  const handleContinueSameSpool = useCallback(() => {
    // Keep worker, operation, and spool - reset only union selection
    resetV4State();
    router.push('/tipo-interaccion');
  }, [resetV4State, router]);

  const handlePrint = useCallback(() => {
    window.print();
  }, []);

  useEffect(() => {
    // Redirect if accessed directly without completing workflow
    if (!selectedWorker || !selectedSpool) {
      router.push('/');
    }
  }, [selectedWorker, selectedSpool, router]);

  useEffect(() => {
    // Clear session storage for completed workflow
    if (selectedSpool) {
      sessionStorage.removeItem(`unions_selection_${selectedSpool}`);
    }

    // Cleanup on unmount
    return () => {
      resetV4State();
    };
  }, [selectedSpool, resetV4State]);

  useEffect(() => {
    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          handleFinish();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    // Cleanup: cancelar timer al desmontar componente
    return () => clearInterval(timer);
  }, [handleFinish]);

  // Get dynamic success message based on workflow type
  const getSuccessMessage = () => {
    if (accion === 'INICIAR') {
      return {
        title: '¡Spool Ocupado!',
        subtitle: 'Has iniciado el trabajo exitosamente',
        details: `Spool ${selectedSpool} está ahora ocupado por ti.`
      };
    } else if (accion === 'FINALIZAR') {
      const unionsCount = selectedUnions.length;

      return {
        title: unionsCount === 0 ? '¡Spool Liberado!' : '¡Trabajo Registrado!',
        subtitle: unionsCount === 0
          ? 'El spool fue liberado sin registrar trabajo'
          : `Se registraron ${unionsCount} ${unionsCount === 1 ? 'unión' : 'uniones'}`,
        details: null
      };
    } else {
      // v3.0 messages (existing)
      const mensaje = tipo === 'tomar' ? 'TOMADO' :
                      tipo === 'pausar' ? 'PAUSADO' :
                      tipo === 'completar' ? 'COMPLETADO' : 'CANCELADO';
      return {
        title: mensaje,
        subtitle: null,
        details: null
      };
    }
  };

  const message = getSuccessMessage();

  // Determine if this is a cancel action for icon color (v3.0 + v4.0 zero-selection)
  const isCancelAction = tipo === 'cancelar' || (accion === 'FINALIZAR' && selectedUnions.length === 0);
  const isSuccess = !isCancelAction;

  return (
    <div
      className="min-h-screen bg-[#001F3F] flex flex-col"
      style={{
        backgroundImage: `
          linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
          linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)
        `,
        backgroundSize: '50px 50px'
      }}
    >
      {/* Logo */}
      <div className="flex justify-center pt-8 pb-6 border-b-4 border-white/30">
        <Image
          src="/logos/logo-grisclaro-F8F9FA.svg"
          alt="Kronos Mining"
          width={200}
          height={80}
          priority
        />
      </div>

      {/* Content - Centered */}
      <div className="flex-1 flex flex-col items-center justify-center px-8 narrow:px-5 gap-8">
        {/* Check - Verde para éxito, Amarillo para cancelar */}
        {isSuccess ? (
          <CheckCircle size={160} strokeWidth={3} className="text-green-500 narrow:w-[120px] narrow:h-[120px]" />
        ) : (
          <AlertCircle size={160} strokeWidth={3} className="text-yellow-500 narrow:w-[120px] narrow:h-[120px]" />
        )}

        {/* Title */}
        <h1 className="text-5xl narrow:text-4xl sm:text-6xl md:text-7xl font-black text-white font-mono tracking-[0.3em] text-center">
          {message.title}
        </h1>

        {/* Subtitle (v4.0 only) */}
        {message.subtitle && (
          <p className="text-xl text-white/80 text-center font-mono">
            {message.subtitle}
          </p>
        )}

        {/* Details (v4.0 INICIAR) */}
        {message.details && (
          <p className="text-lg text-white/60 text-center font-mono">
            {message.details}
          </p>
        )}

        {/* v4.0 FINALIZAR: Work Summary */}
        {accion === 'FINALIZAR' && selectedUnions.length > 0 && (
          <div className="bg-white/10 rounded-lg p-6 w-full max-w-2xl border-2 border-white/30">
            <h3 className="text-2xl font-bold text-white mb-4 font-mono text-center">RESUMEN DEL TRABAJO</h3>

            <div className="grid grid-cols-2 gap-6 mb-4">
              <div className="text-center">
                <p className="text-sm text-white/60 mb-2 font-mono">UNIONES COMPLETADAS</p>
                <p className="text-4xl font-black text-zeues-orange font-mono">{selectedUnions.length}</p>
              </div>
              <div className="text-center">
                <p className="text-sm text-white/60 mb-2 font-mono">PULGADAS-DIÁMETRO</p>
                <p className="text-4xl font-black text-zeues-orange font-mono">{pulgadasCompletadas.toFixed(1)}</p>
              </div>
            </div>

            <div className="pt-4 border-t border-white/20">
              <div className="flex justify-between items-center">
                <span className="text-white/60 font-mono">OPERACIÓN:</span>
                <span className="font-black text-white font-mono text-lg">
                  {selectedOperation === 'ARM' ? 'ARMADO' : 'SOLDADURA'}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Worker and timestamp info */}
        <div className="bg-white/5 rounded-lg p-4 w-full max-w-2xl border border-white/20">
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-sm text-white/60 font-mono">TRABAJADOR:</span>
              <span className="font-bold text-white font-mono">
                {selectedWorker?.nombre_completo || `${selectedWorker?.nombre} (${selectedWorker?.id})`}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-white/60 font-mono">FECHA/HORA:</span>
              <span className="font-bold text-white font-mono">
                {new Date().toLocaleString('es-CL', {
                  timeZone: 'America/Santiago',
                  year: 'numeric',
                  month: '2-digit',
                  day: '2-digit',
                  hour: '2-digit',
                  minute: '2-digit'
                })}
              </span>
            </div>
            {selectedSpool && (
              <div className="flex justify-between items-center">
                <span className="text-sm text-white/60 font-mono">SPOOL:</span>
                <span className="font-bold text-white font-mono">{selectedSpool}</span>
              </div>
            )}
          </div>
        </div>

        {/* Countdown con "SEGUNDOS" */}
        <div className="text-center">
          <div className="text-6xl narrow:text-5xl sm:text-7xl md:text-8xl font-black text-zeues-orange font-mono">{countdown}</div>
          <div className="text-xl sm:text-2xl font-black text-white/50 font-mono mt-4">SEGUNDOS</div>
        </div>

        {/* Navigation Buttons */}
        <div className="w-full max-w-2xl space-y-4">
          {/* v4.0: Continue with same spool (only for FINALIZAR) */}
          {accion === 'FINALIZAR' && selectedUnions.length > 0 && (
            <button
              onClick={handleContinueSameSpool}
              className="w-full h-16 border-4 border-white/50 flex items-center justify-center active:bg-white/20 group"
            >
              <span className="text-xl font-black text-white font-mono">
                CONTINUAR CON MISMO SPOOL
              </span>
            </button>
          )}

          {/* Nuevo Trabajo (all workflows) */}
          <button
            onClick={handleNewWork}
            className="w-full h-20 border-4 border-white flex items-center justify-center active:bg-white active:text-[#001F3F] group"
          >
            <span className="text-2xl font-black text-white font-mono group-active:text-[#001F3F]">
              NUEVO TRABAJO
            </span>
          </button>

          {/* Print option (optional) */}
          <div className="text-center pt-2">
            <button
              onClick={handlePrint}
              className="text-white/60 hover:text-white text-sm underline font-mono"
            >
              IMPRIMIR COMPROBANTE
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
