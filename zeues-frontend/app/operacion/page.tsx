'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button, ErrorMessage } from '@/components';
import { useAppState } from '@/lib/context';
import type { Worker } from '@/lib/types';

// Mapeo de operaciones a roles necesarios
const OPERATION_TO_ROLES: Record<string, string[]> = {
  'ARM': ['Armador', 'Ayudante'],
  'SOLD': ['Soldador', 'Ayudante'],
  'METROLOGIA': ['Metrologia'],
};

// Títulos dinámicos por operación
const OPERATION_TITLES: Record<string, string> = {
  'ARM': '🔧 ¿Quién va a armar?',
  'SOLD': '🔥 ¿Quién va a soldar?',
  'METROLOGIA': '📐 ¿Quién va a medir?',
};

export default function TrabajadorSelectionPage() {
  const router = useRouter();
  const { state, setState } = useAppState();
  const [filteredWorkers, setFilteredWorkers] = useState<Worker[]>([]);

  useEffect(() => {
    // Validar que existe operación seleccionada
    if (!state.selectedOperation) {
      router.push('/');
      return;
    }

    // Filtrar trabajadores que tienen el rol necesario para esta operación
    const requiredRoles = OPERATION_TO_ROLES[state.selectedOperation] || [];

    const eligible = state.allWorkers.filter(worker => {
      if (!worker.activo) return false;  // Solo trabajadores activos
      if (!worker.roles || worker.roles.length === 0) return false;  // Debe tener roles

      // Verificar si tiene alguno de los roles necesarios
      return worker.roles.some(role => requiredRoles.includes(role));
    });

    setFilteredWorkers(eligible);
  }, [state.selectedOperation, state.allWorkers, router]);

  const handleSelectWorker = (worker: Worker) => {
    setState({ selectedWorker: worker });
    router.push('/tipo-interaccion');
  };

  if (!state.selectedOperation) return null;

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <button
        onClick={() => router.back()}
        className="text-cyan-600 font-semibold mb-6"
      >
        ← Volver
      </button>

      <div className="max-w-2xl mx-auto">
        <h1 className="text-2xl font-semibold text-center mb-8">
          {OPERATION_TITLES[state.selectedOperation]}
        </h1>

        {filteredWorkers.length === 0 ? (
          <div>
            <ErrorMessage
              message={`No hay trabajadores disponibles para ${state.selectedOperation}`}
            />
            <div className="mt-4 text-center">
              <Button onClick={() => router.back()}>
                Volver a seleccionar operación
              </Button>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredWorkers.map((worker) => (
              <Button
                key={worker.id}
                onClick={() => handleSelectWorker(worker)}
              >
                {worker.nombre_completo}
              </Button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
