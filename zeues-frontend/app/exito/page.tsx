'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components';
import { useAppState } from '@/lib/context';

export default function ExitoPage() {
  const router = useRouter();
  const { state, resetState } = useAppState();
  const [countdown, setCountdown] = useState(5);

  const tipo = state.selectedTipo;
  const batchResults = state.batchResults;
  const isBatchMode = batchResults !== null;

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
      <div className="max-w-4xl mx-auto">
        {isBatchMode && batchResults ? (
          // v2.0: Batch results view
          <div className="text-center">
            {/* Icon - Success si todos exitosos, Warning si hay fallos */}
            <div className="mb-6">
              {batchResults.fallidos > 0 ? (
                <svg className="w-32 h-32 mx-auto text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              ) : (
                <svg className="w-32 h-32 mx-auto text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              )}
            </div>

            {/* Título con stats */}
            <h1 className={`text-3xl font-bold mb-4 ${batchResults.fallidos > 0 ? 'text-yellow-600' : 'text-green-600'}`}>
              {batchResults.fallidos > 0 ? 'Operación parcialmente exitosa' : 'Operación batch exitosa'}
            </h1>

            {/* Stats */}
            <div className="mb-6 text-xl text-gray-700">
              <p>
                <span className="font-bold text-green-600">{batchResults.exitosos} exitosos</span>
                {' / '}
                <span className="font-bold text-red-600">{batchResults.fallidos} fallidos</span>
                {' de '}
                <span className="font-bold">{batchResults.total} spools</span>
              </p>
            </div>

            {/* Resultados detallados */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6 text-left">
              {/* Exitosos */}
              {batchResults.exitosos > 0 && (
                <div className="bg-green-50 border-2 border-green-600 rounded-lg p-4">
                  <h2 className="text-lg font-bold text-green-800 mb-3 flex items-center gap-2">
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                    Exitosos ({batchResults.exitosos})
                  </h2>
                  <div className="max-h-60 overflow-y-auto space-y-1">
                    {batchResults.resultados
                      .filter(r => r.success)
                      .map((resultado) => (
                        <div key={resultado.tag_spool} className="text-sm text-green-900">
                          ✓ {resultado.tag_spool}
                        </div>
                      ))
                    }
                  </div>
                </div>
              )}

              {/* Fallidos */}
              {batchResults.fallidos > 0 && (
                <div className="bg-red-50 border-2 border-red-600 rounded-lg p-4">
                  <h2 className="text-lg font-bold text-red-800 mb-3 flex items-center gap-2">
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                    </svg>
                    Fallidos ({batchResults.fallidos})
                  </h2>
                  <div className="max-h-60 overflow-y-auto space-y-2">
                    {batchResults.resultados
                      .filter(r => !r.success)
                      .map((resultado) => (
                        <div key={resultado.tag_spool} className="text-sm">
                          <div className="font-semibold text-red-900">✗ {resultado.tag_spool}</div>
                          <div className="text-red-700 ml-4">{resultado.message}</div>
                        </div>
                      ))
                    }
                  </div>
                </div>
              )}
            </div>

            {/* Countdown */}
            <p className="text-lg text-gray-500 mb-8">
              Volviendo al inicio en {countdown} {countdown === 1 ? 'segundo' : 'segundos'}...
            </p>

            {/* Botones */}
            <div className="space-y-3">
              <Button onClick={handleFinish}>REGISTRAR OTRA</Button>
              <Button variant="cancel" onClick={handleFinish}>FINALIZAR</Button>
            </div>
          </div>
        ) : (
          // Single mode - Comportamiento original
          <div className="text-center">
            {/* Icon SVG Grande - Dinámico según tipo */}
            <div className="mb-6">
              {tipo === 'cancelar' ? (
                <svg className="w-32 h-32 mx-auto text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              ) : (
                <svg className="w-32 h-32 mx-auto text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              )}
            </div>

            {/* Mensaje Principal */}
            <h1 className={`text-3xl font-bold mb-4 ${tipo === 'cancelar' ? 'text-yellow-600' : 'text-green-600'}`}>
              {tipo === 'iniciar' && '¡Acción iniciada exitosamente!'}
              {tipo === 'completar' && '¡Acción completada exitosamente!'}
              {tipo === 'cancelar' && '⚠️ Acción cancelada'}
            </h1>

            {/* Mensaje Secundario */}
            <p className="text-xl text-gray-700 mb-2">
              {tipo === 'cancelar' ? 'El spool vuelve a estado PENDIENTE' : 'El spool ha sido actualizado en Google Sheets'}
            </p>

            {/* Countdown */}
            <p className="text-lg text-gray-500 mb-8">
              Volviendo al inicio en {countdown} {countdown === 1 ? 'segundo' : 'segundos'}...
            </p>

            {/* Botones */}
            <div className="space-y-3">
              <Button onClick={handleFinish}>REGISTRAR OTRA</Button>
              <Button variant="cancel" onClick={handleFinish}>FINALIZAR</Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
