'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components';
import { useAppState } from '@/lib/context';

// Mapeo de roles a operaciones permitidas
const ROLE_TO_OPERATIONS: Record<string, string[]> = {
  'Armador': ['ARM'],
  'Soldador': ['SOLD'],
  'Metrologia': ['METROLOGIA'],
  'Ayudante': ['ARM', 'SOLD'], // Ayudante puede hacer ARM y SOLD
};

export default function OperacionPage() {
  const router = useRouter();
  const { state, setState } = useAppState();
  const [allowedOperations, setAllowedOperations] = useState<string[]>([]);

  useEffect(() => {
    if (!state.selectedWorker) {
      router.push('/');
      return;
    }

    // Usar el rol del worker directamente (no llamar API)
    const workerRole = state.selectedWorker.rol;
    const ops = ROLE_TO_OPERATIONS[workerRole] || [];
    setAllowedOperations(ops);
  }, [state.selectedWorker, router]);

  const handleSelectOperation = (operacion: 'ARM' | 'SOLD') => {
    setState({ selectedOperation: operacion });
    router.push('/tipo-interaccion');
  };

  if (!state.selectedWorker) return null;

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <button
        onClick={() => router.back()}
        className="text-cyan-600 font-semibold mb-6"
      >
        ← Volver
      </button>

      <div className="max-w-2xl mx-auto">
        <h1 className="text-2xl font-semibold text-center mb-2">
          Hola {state.selectedWorker.nombre_completo},
        </h1>
        <h2 className="text-xl text-center text-gray-600 mb-8">
          ¿Qué vas a hacer?
        </h2>

        {allowedOperations.length === 0 ? (
          <div className="text-center p-6 bg-yellow-50 border border-yellow-200 rounded-lg">
            <p className="text-yellow-800 font-medium">
              Tu rol ({state.selectedWorker.rol}) no tiene operaciones disponibles.
            </p>
            <p className="text-yellow-700 text-sm mt-2">
              Contacta a tu supervisor si crees que esto es un error.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {allowedOperations.includes('ARM') && (
              <Button onClick={() => handleSelectOperation('ARM')}>
                🔧 ARMADO (ARM)
              </Button>
            )}
            {allowedOperations.includes('SOLD') && (
              <Button onClick={() => handleSelectOperation('SOLD')}>
                🔥 SOLDADO (SOLD)
              </Button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
