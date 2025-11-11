'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components';
import { useAppState } from '@/lib/context';

export default function OperacionPage() {
  const router = useRouter();
  const { state, setState } = useAppState();

  useEffect(() => {
    if (!state.selectedWorker) {
      router.push('/');
    }
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
          Hola {state.selectedWorker},
        </h1>
        <h2 className="text-xl text-center text-gray-600 mb-8">
          ¿Qué vas a hacer?
        </h2>

        <div className="space-y-4">
          <Button onClick={() => handleSelectOperation('ARM')}>
            🔧 ARMADO (ARM)
          </Button>
          <Button onClick={() => handleSelectOperation('SOLD')}>
            🔥 SOLDADO (SOLD)
          </Button>
        </div>
      </div>
    </div>
  );
}
