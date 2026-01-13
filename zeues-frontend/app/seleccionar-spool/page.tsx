'use client';

import { Suspense, useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Loading, ErrorMessage, Button } from '@/components';
import { SpoolSelector } from '@/components/SpoolSelector';
import { useAppState } from '@/lib/context';
import { getSpoolsParaIniciar, getSpoolsParaCompletar, getSpoolsParaCancelar } from '@/lib/api';
import type { Spool } from '@/lib/types';

function SeleccionarSpoolContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const tipo = searchParams.get('tipo') as 'iniciar' | 'completar' | 'cancelar';
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
      } else if (tipo === 'completar') {
        // Llamar API para obtener spools que el trabajador puede completar
        if (!selectedWorker) {
          setError('No se ha seleccionado un trabajador');
          setErrorType('validation');
          setLoading(false);
          return;
        }
        fetchedSpools = await getSpoolsParaCompletar(selectedOperation as 'ARM' | 'SOLD', selectedWorker.nombre_completo);
      } else {
        // tipo === 'cancelar' - Llamar API para obtener spools que el trabajador puede cancelar
        if (!selectedWorker) {
          setError('No se ha seleccionado un trabajador');
          setErrorType('validation');
          setLoading(false);
          return;
        }
        fetchedSpools = await getSpoolsParaCancelar(selectedOperation as 'ARM' | 'SOLD', selectedWorker.id);
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

  // v2.0: Handle batch selection changes
  const handleBatchSelectionChange = (tags: string[]) => {
    setState({ selectedSpools: tags });
  };

  // v2.0: Navigate with selections (auto-detect single vs batch)
  const handleContinueWithBatch = () => {
    const selectedCount = state.selectedSpools.length;

    if (selectedCount === 0) return; // No hacer nada si no hay selección

    if (selectedCount === 1) {
      // Single mode - compatibilidad con backend/API
      setState({
        selectedSpool: state.selectedSpools[0],
        selectedSpools: [],
        batchMode: false
      });
    } else {
      // Batch mode - 2+ spools
      setState({
        selectedSpool: null,
        batchMode: true
      });
    }

    router.push(`/confirmar?tipo=${tipo}`);
  };

  if (!state.selectedWorker || !state.selectedOperation) return null;

  const title = tipo === 'iniciar'
    ? `Selecciona spool para INICIAR ${state.selectedOperation}`
    : tipo === 'completar'
    ? `Selecciona TU spool para COMPLETAR ${state.selectedOperation}`
    : `Selecciona TU spool para CANCELAR ${state.selectedOperation}`;

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <button
        onClick={() => router.back()}
        className="text-cyan-600 font-semibold mb-6 text-xl"
      >
        ← Volver
      </button>

      <div className="max-w-4xl mx-auto">
        <h1 className="text-2xl font-semibold text-center mb-6">
          {title}
        </h1>

        {loading && <Loading />}
        {error && <ErrorMessage message={error} type={errorType} onRetry={fetchSpools} />}

        {!loading && !error && (
          <div className="space-y-4">
            <SpoolSelector
              spools={spools}
              selectedTags={state.selectedSpools}
              onSelectChange={handleBatchSelectionChange}
              maxSelection={50}
            />
            <div className="flex justify-center pt-4">
              <Button
                onClick={handleContinueWithBatch}
                variant="primary"
                disabled={state.selectedSpools.length === 0}
                className="w-full max-w-md"
              >
                Continuar con {state.selectedSpools.length} spool{state.selectedSpools.length !== 1 ? 's' : ''}
              </Button>
            </div>
          </div>
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
