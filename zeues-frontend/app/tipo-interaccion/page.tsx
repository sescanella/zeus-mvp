'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components';
import { useAppState } from '@/lib/context';

export default function TipoInteraccionPage() {
  const router = useRouter();
  const { state, setState } = useAppState();

  useEffect(() => {
    if (!state.selectedWorker || !state.selectedOperation) {
      router.push('/');
    }
  }, [state, router]);

  const handleSelectTipo = (tipo: 'iniciar' | 'completar') => {
    setState({ selectedTipo: tipo });
    router.push(`/seleccionar-spool?tipo=${tipo}`);
  };

  if (!state.selectedWorker || !state.selectedOperation) return null;

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
          {state.selectedOperation === 'ARM' ? 'ARMADO (ARM)' : 'SOLDADO (SOLD)'}
        </h1>
        <h2 className="text-xl text-center text-gray-600 mb-8">
          ¿Qué acción realizarás?
        </h2>

        <div className="space-y-4">
          <Button
            variant="iniciar"
            onClick={() => handleSelectTipo('iniciar')}
          >
            <div className="text-left">
              <div className="text-xl font-bold mb-1">🔵 INICIAR ACCIÓN</div>
              <div className="text-sm font-normal">
                Asignar spool antes de trabajar
              </div>
            </div>
          </Button>

          <Button
            variant="completar"
            onClick={() => handleSelectTipo('completar')}
          >
            <div className="text-left">
              <div className="text-xl font-bold mb-1">✅ COMPLETAR ACCIÓN</div>
              <div className="text-sm font-normal">
                Registrar finalización del trabajo
              </div>
            </div>
          </Button>
        </div>
      </div>
    </div>
  );
}
