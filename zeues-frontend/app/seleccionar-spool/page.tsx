'use client';

import { Suspense, useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { List, Loading, ErrorMessage } from '@/components';
import { useAppState } from '@/lib/context';
import { getSpoolsParaIniciar, getSpoolsParaCompletar } from '@/lib/api';
import type { Spool } from '@/lib/types';

function SeleccionarSpoolContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const tipo = searchParams.get('tipo') as 'iniciar' | 'completar';
  const { state, setState } = useAppState();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [errorType, setErrorType] = useState<'network' | 'not-found' | 'validation' | 'forbidden' | 'server' | 'generic'>('generic');
  const [spools, setSpools] = useState<Spool[]>([]);

  useEffect(() => {
    if (!state.selectedWorker || !state.selectedOperation || !tipo) {
      router.push('/');
      return;
    }
    fetchSpools();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchSpools = async () => {
    try {
      setLoading(true);
      setError('');
      setSpools([]);

      const { selectedWorker, selectedOperation } = state;

      if (!selectedOperation) {
        setError('No se ha seleccionado una operación');
        setErrorType('validation');
        setLoading(false);
        return;
      }

      let fetchedSpools: Spool[];

      if (tipo === 'iniciar') {
        // Llamar API para obtener spools disponibles para iniciar
        fetchedSpools = await getSpoolsParaIniciar(selectedOperation as 'ARM' | 'SOLD');
      } else {
        // Llamar API para obtener spools que el trabajador puede completar
        if (!selectedWorker) {
          setError('No se ha seleccionado un trabajador');
          setErrorType('validation');
          setLoading(false);
          return;
        }
        fetchedSpools = await getSpoolsParaCompletar(selectedOperation as 'ARM' | 'SOLD', selectedWorker);
      }

      setSpools(fetchedSpools);
      setLoading(false);
    } catch (err) {
      // Determinar tipo de error según el mensaje
      const errorMessage = err instanceof Error ? err.message : 'Error desconocido';

      if (errorMessage.includes('red') || errorMessage.includes('conexión')) {
        setErrorType('network');
        setError('Error de conexión. Verifica que el servidor esté disponible.');
      } else if (errorMessage.includes('404') || errorMessage.includes('no encontrado')) {
        setErrorType('not-found');
        setError(errorMessage);
      } else if (errorMessage.includes('400') || errorMessage.includes('validación')) {
        setErrorType('validation');
        setError(errorMessage);
      } else if (errorMessage.includes('503') || errorMessage.includes('servidor')) {
        setErrorType('server');
        setError('El servidor no está disponible. Intenta más tarde.');
      } else {
        setErrorType('generic');
        setError(errorMessage || 'Error al cargar spools. Intenta nuevamente.');
      }

      setLoading(false);
    }
  };

  const getEmptyMessage = () => {
    const { selectedOperation } = state;

    if (tipo === 'iniciar') {
      return selectedOperation === 'ARM'
        ? 'No hay spools disponibles para INICIAR ARMADO'
        : 'No hay spools listos para INICIAR SOLDADO (requieren armado completo)';
    } else {
      return selectedOperation === 'ARM'
        ? 'No tienes spools en progreso de ARMADO'
        : 'No tienes spools en progreso de SOLDADO';
    }
  };

  const handleSelectSpool = (tag: string) => {
    setState({ selectedSpool: tag });
    router.push(`/confirmar?tipo=${tipo}`);
  };

  if (!state.selectedWorker || !state.selectedOperation) return null;

  const title = tipo === 'iniciar'
    ? `Selecciona spool para INICIAR ${state.selectedOperation}`
    : `Selecciona TU spool para COMPLETAR ${state.selectedOperation}`;

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <button
        onClick={() => router.back()}
        className="text-cyan-600 font-semibold mb-6 text-xl"
      >
        ← Volver
      </button>

      <div className="max-w-2xl mx-auto">
        <h1 className="text-2xl font-semibold text-center mb-6">
          {title}
        </h1>

        {loading && <Loading />}
        {error && <ErrorMessage message={error} type={errorType} onRetry={fetchSpools} />}

        {!loading && !error && (
          <List
            items={spools.map((s) => ({
              id: s.tag_spool,
              label: s.tag_spool,
              subtitle: s.tag_spool,
            }))}
            onItemClick={handleSelectSpool}
            emptyMessage={getEmptyMessage()}
          />
        )}
      </div>
    </div>
  );
}

export default function SeleccionarSpoolPage() {
  return (
    <Suspense fallback={<Loading />}>
      <SeleccionarSpoolContent />
    </Suspense>
  );
}
