'use client';

import { Suspense, useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { List, Loading, ErrorMessage, Button } from '@/components';
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
  const [isBatchMode, setIsBatchMode] = useState(false);

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

  const getEmptyMessage = () => {
    const { selectedOperation } = state;

    if (tipo === 'iniciar') {
      return selectedOperation === 'ARM'
        ? 'No hay spools disponibles para INICIAR ARMADO'
        : 'No hay spools listos para INICIAR SOLDADO (requieren armado completo)';
    } else if (tipo === 'completar') {
      return selectedOperation === 'ARM'
        ? 'No tienes spools en progreso de ARMADO'
        : 'No tienes spools en progreso de SOLDADO';
    } else {
      // tipo === 'cancelar'
      return selectedOperation === 'ARM'
        ? 'No tienes spools en progreso de ARMADO para cancelar'
        : 'No tienes spools en progreso de SOLDADO para cancelar';
    }
  };

  const handleSelectSpool = (tag: string) => {
    setState({ selectedSpool: tag, batchMode: false });
    router.push(`/confirmar?tipo=${tipo}`);
  };

  // v2.0: Toggle batch mode
  const handleToggleBatchMode = () => {
    const newBatchMode = !isBatchMode;
    setIsBatchMode(newBatchMode);

    if (newBatchMode) {
      // Entering batch mode - clear single selection, keep empty array
      setState({
        selectedSpool: null,
        selectedSpools: [],
        batchMode: true
      });
    } else {
      // Exiting batch mode - clear array, keep single selection null
      setState({
        selectedSpool: null,
        selectedSpools: [],
        batchMode: false
      });
    }
  };

  // v2.0: Handle batch selection changes
  const handleBatchSelectionChange = (tags: string[]) => {
    setState({ selectedSpools: tags });
  };

  // v2.0: Navigate with batch selections
  const handleContinueWithBatch = () => {
    if (state.selectedSpools.length > 0) {
      setState({ batchMode: true });
      router.push(`/confirmar?tipo=${tipo}`);
    }
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

        {/* v2.0: Batch mode toggle */}
        {!loading && !error && spools.length > 0 && (
          <div className="mb-6 flex items-center justify-center gap-4 p-4 bg-white rounded-lg border-2 border-gray-200">
            <label htmlFor="batch-mode-toggle" className="text-lg font-medium text-gray-900">
              Modo selección:
            </label>
            <button
              id="batch-mode-toggle"
              onClick={handleToggleBatchMode}
              className={`
                relative inline-flex h-8 w-16 items-center rounded-full transition-colors
                ${isBatchMode ? 'bg-cyan-600' : 'bg-gray-300'}
              `}
              aria-label={isBatchMode ? 'Desactivar modo múltiple' : 'Activar modo múltiple'}
            >
              <span
                className={`
                  inline-block h-6 w-6 transform rounded-full bg-white transition-transform
                  ${isBatchMode ? 'translate-x-9' : 'translate-x-1'}
                `}
              />
            </button>
            <span className="text-base text-gray-700">
              {isBatchMode ? 'Múltiple (hasta 50)' : 'Individual'}
            </span>
          </div>
        )}

        {loading && <Loading />}
        {error && <ErrorMessage message={error} type={errorType} onRetry={fetchSpools} />}

        {!loading && !error && (
          <>
            {isBatchMode ? (
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
            ) : (
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
          </>
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
