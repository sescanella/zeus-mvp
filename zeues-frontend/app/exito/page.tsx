'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components';
import { useAppState } from '@/lib/context';

export default function ExitoPage() {
  const router = useRouter();
  const { resetState } = useAppState();
  const [countdown, setCountdown] = useState(5);

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

  return (
    <div className="min-h-screen bg-slate-50 p-6 flex items-center justify-center">
      <div className="max-w-2xl mx-auto text-center">
        {/* Checkmark SVG Grande */}
        <div className="mb-6">
          <svg
            className="w-32 h-32 mx-auto text-green-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M5 13l4 4L19 7"
            />
          </svg>
        </div>

        {/* Mensaje Principal */}
        <h1 className="text-3xl font-bold text-green-600 mb-4">
          ¡Acción completada exitosamente!
        </h1>

        {/* Mensaje Secundario */}
        <p className="text-xl text-gray-700 mb-2">
          El spool ha sido actualizado en Google Sheets
        </p>

        {/* Countdown */}
        <p className="text-lg text-gray-500 mb-8">
          Volviendo al inicio en {countdown} {countdown === 1 ? 'segundo' : 'segundos'}...
        </p>

        {/* Botones */}
        <div className="space-y-3">
          <Button onClick={handleFinish}>
            REGISTRAR OTRA
          </Button>
          <Button variant="cancel" onClick={handleFinish}>
            FINALIZAR
          </Button>
        </div>
      </div>
    </div>
  );
}
