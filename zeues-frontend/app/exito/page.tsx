'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';
import { CheckCircle, AlertCircle } from 'lucide-react';
import { useAppState } from '@/lib/context';

export default function ExitoPage() {
  const router = useRouter();
  const { state, resetState } = useAppState();
  const [countdown, setCountdown] = useState(5);

  const tipo = state.selectedTipo;

  const handleFinish = useCallback(() => {
    resetState();
    router.push('/');
  }, [resetState, router]);

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

  // Determinar mensaje y color según tipo
  const isCancelAction = tipo === 'cancelar';
  const isSuccess = !isCancelAction;
  const mensaje = tipo === 'iniciar' ? 'INICIADO' :
                  tipo === 'completar' ? 'COMPLETADO' : 'CANCELADO';

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
      <div className="flex-1 flex flex-col items-center justify-center px-8 narrow:px-5 gap-20">
        {/* Check - Verde para éxito, Amarillo para cancelar */}
        {isSuccess ? (
          <CheckCircle size={160} strokeWidth={3} className="text-green-500 narrow:w-[120px] narrow:h-[120px]" />
        ) : (
          <AlertCircle size={160} strokeWidth={3} className="text-yellow-500 narrow:w-[120px] narrow:h-[120px]" />
        )}

        {/* Mensaje */}
        <h1 className="text-5xl narrow:text-4xl sm:text-6xl md:text-7xl font-black text-white font-mono tracking-[0.3em] text-center">
          {mensaje}
        </h1>

        {/* Countdown con "SEGUNDOS" */}
        <div className="text-center">
          <div className="text-6xl narrow:text-5xl sm:text-7xl md:text-8xl font-black text-zeues-orange font-mono">{countdown}</div>
          <div className="text-xl sm:text-2xl font-black text-white/50 font-mono mt-4">SEGUNDOS</div>
        </div>

        {/* Botón */}
        <button
          onClick={handleFinish}
          className="w-full max-w-2xl h-24 border-4 border-white flex items-center justify-center active:bg-white active:text-[#001F3F] group"
        >
          <span className="text-3xl narrow:text-2xl font-black text-white font-mono group-active:text-[#001F3F]">
            CONTINUAR
          </span>
        </button>
      </div>
    </div>
  );
}
