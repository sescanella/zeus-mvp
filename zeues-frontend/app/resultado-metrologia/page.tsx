'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';
import { CheckCircle, XCircle, ArrowLeft, X, Loader2, AlertCircle } from 'lucide-react';
import { BlueprintPageWrapper } from '@/components';
import { useAppState } from '@/lib/context';
import { completarMetrologia } from '@/lib/api';

export default function ResultadoMetrologiaPage() {
  const router = useRouter();
  const { state } = useAppState();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (resultado: 'APROBADO' | 'RECHAZADO') => {
    try {
      setLoading(true);
      setError('');

      if (!state.selectedSpool) {
        setError('No se ha seleccionado un spool');
        setLoading(false);
        return;
      }

      if (!state.selectedWorker) {
        setError('No se ha seleccionado un trabajador');
        setLoading(false);
        return;
      }

      await completarMetrologia(
        state.selectedSpool,
        state.selectedWorker.id,
        resultado
      );

      // Success - navigate to success page
      router.push('/exito');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Error desconocido';

      // Handle 409 conflict specifically
      if (errorMessage.includes('409') || errorMessage.includes('ocupado')) {
        setError('El spool está ocupado por otro trabajador. Intenta más tarde.');
      } else if (errorMessage.includes('404')) {
        setError('Spool no encontrado. Verifica los datos.');
      } else if (errorMessage.includes('403')) {
        setError('No tienes autorización para realizar esta operación.');
      } else if (errorMessage.includes('400')) {
        setError('Error de validación. Verifica los datos.');
      } else {
        setError(errorMessage || 'Error al completar metrología. Intenta nuevamente.');
      }

      setLoading(false);
    }
  };

  if (!state.selectedSpool || !state.selectedWorker) {
    return (
      <BlueprintPageWrapper>
        <div className="flex items-center justify-center min-h-screen">
          <div className="text-center">
          <p className="text-xl text-white font-mono mb-6">
            Datos incompletos. Volviendo al inicio...
          </p>
          <button
            onClick={() => router.push('/')}
            className="px-8 py-4 border-4 border-white text-white font-mono font-black active:bg-white active:text-[#001F3F]"
          >
            IR AL INICIO
          </button>
        </div>
        </div>
      </BlueprintPageWrapper>
    );
  }

  return (
    <BlueprintPageWrapper>
      {/* Logo */}
      <div className="flex justify-center pt-4 pb-3 tablet:header-compact narrow:header-compact border-b-4 border-white/30">
        <Image
          src="/logos/logo-grisclaro-F8F9FA.svg"
          alt="Kronos Mining"
          width={140}
          height={56}
          priority
        />
      </div>

      {/* Header */}
      <div className="px-10 tablet:px-6 narrow:px-5 py-6 tablet:py-4 border-b-4 border-white/30">
        <h2 className="text-3xl narrow:text-2xl font-black text-center text-white tracking-[0.25em] font-mono">
          RESULTADO METROLOGÍA
        </h2>
      </div>

      {/* Content */}
      <div className="p-8 tablet:p-5 pb-footer tablet:pb-footer narrow:pb-footer">
        {/* Spool Info */}
        <div className="border-4 border-white p-6 mb-8">
          <div className="text-center">
            <p className="text-sm font-black text-white/50 font-mono mb-2">SPOOL SELECCIONADO</p>
            <h3 className="text-4xl narrow:text-3xl font-black text-zeues-orange font-mono tracking-wider">
              {state.selectedSpool}
            </h3>
          </div>
        </div>

        {/* Error Message */}
        {error && !loading && (
          <div className="border-4 border-red-500 p-8 mb-6 bg-red-500/10">
            <div className="flex items-center gap-4 mb-4">
              <AlertCircle size={48} className="text-red-500" strokeWidth={3} />
              <h3 className="text-2xl font-black text-red-500 font-mono">ERROR</h3>
            </div>
            <p className="text-lg text-white font-mono mb-6">{error}</p>
            <button
              onClick={() => setError('')}
              className="px-6 py-3 border-4 border-white text-white font-mono font-black active:bg-white active:text-[#001F3F]"
            >
              REINTENTAR
            </button>
          </div>
        )}

        {/* Binary Resultado Buttons */}
        {!loading && !error && (
          <div className="flex flex-col gap-6 mb-8">
            {/* APROBADO Button */}
            <button
              onClick={() => handleSubmit('APROBADO')}
              disabled={loading}
              className="
                h-32 narrow:h-28 w-full
                bg-transparent
                border-4 border-green-500
                flex flex-col items-center justify-center gap-3
                cursor-pointer
                active:bg-green-500 active:border-green-500
                transition-all duration-200
                disabled:opacity-30 disabled:cursor-not-allowed
                group
              "
            >
              <CheckCircle size={64} strokeWidth={3} className="text-green-500 group-active:text-white" />
              <span className="text-4xl narrow:text-3xl font-black text-green-500 font-mono tracking-[0.2em] group-active:text-white">
                APROBADO
              </span>
            </button>

            {/* RECHAZADO Button */}
            <button
              onClick={() => handleSubmit('RECHAZADO')}
              disabled={loading}
              className="
                h-32 narrow:h-28 w-full
                bg-transparent
                border-4 border-red-500
                flex flex-col items-center justify-center gap-3
                cursor-pointer
                active:bg-red-500 active:border-red-500
                transition-all duration-200
                disabled:opacity-30 disabled:cursor-not-allowed
                group
              "
            >
              <XCircle size={64} strokeWidth={3} className="text-red-500 group-active:text-white" />
              <span className="text-4xl narrow:text-3xl font-black text-red-500 font-mono tracking-[0.2em] group-active:text-white">
                RECHAZADO
              </span>
            </button>
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="flex flex-col items-center justify-center py-20">
            <Loader2 size={64} className="text-zeues-orange animate-spin mb-4" strokeWidth={3} />
            <span className="text-xl font-black text-white font-mono">PROCESANDO...</span>
          </div>
        )}
      </div>

      {/* Fixed Navigation Footer */}
      {!loading && (
        <div className="fixed bottom-0 left-0 right-0 bg-[#001F3F] z-50 border-t-4 border-white/30 p-6 tablet:p-5">
          <div className="flex gap-4 tablet:gap-3 narrow:flex-col narrow:gap-3">
            <button
              onClick={() => router.back()}
              className="
                flex-1 narrow:w-full h-16
                bg-transparent
                border-4 border-white
                flex items-center justify-center gap-3
                active:bg-white active:text-[#001F3F]
                transition-all duration-200
                group
              "
            >
              <ArrowLeft size={24} strokeWidth={3} className="text-white group-active:text-[#001F3F]" />
              <span className="text-xl narrow:text-lg font-black text-white font-mono tracking-[0.15em] group-active:text-[#001F3F]">
                VOLVER
              </span>
            </button>

            <button
              onClick={() => router.push('/')}
              className="
                flex-1 narrow:w-full h-16
                bg-transparent
                border-4 border-red-500
                flex items-center justify-center gap-3
                active:bg-red-500 active:border-red-500
                transition-all duration-200
                group
              "
            >
              <X size={24} strokeWidth={3} className="text-red-500 group-active:text-white" />
              <span className="text-xl narrow:text-lg font-black text-red-500 font-mono tracking-[0.15em] group-active:text-white">
                CANCELAR
              </span>
            </button>
          </div>
        </div>
      )}
    </BlueprintPageWrapper>
  );
}
