'use client';

import { useState, useEffect, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { useAppState } from '@/lib/context';
import { UnionTable } from '@/components/UnionTable';
import { Modal } from '@/components/Modal';
import { Button } from '@/components/Button';
import { getDisponiblesUnions } from '@/lib/api';
import type { Union } from '@/lib/types';

export default function SeleccionarUnionesPage() {
  const router = useRouter();
  const { state, setState } = useAppState();

  const [unions, setUnions] = useState<Union[]>([]);
  const [loading, setLoading] = useState(true);
  const [showZeroModal, setShowZeroModal] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Redirect if missing required context
  useEffect(() => {
    if (!state.selectedSpool || !state.selectedOperation) {
      router.push('/');
    }
  }, [state.selectedSpool, state.selectedOperation, router]);

  // Fetch unions on mount (IMPORTANT: Fresh API call for P5 data accuracy)
  useEffect(() => {
    const fetchUnions = async () => {
      if (!state.selectedSpool || !state.selectedOperation) return;

      try {
        setLoading(true);
        setError(null);

        const response = await getDisponiblesUnions(
          state.selectedSpool,
          state.selectedOperation as 'ARM' | 'SOLD'
        );

        // Mark completed unions based on operation
        const unionsWithCompletionStatus = response.uniones.map(u => ({
          ...u,
          is_completed: state.selectedOperation === 'ARM'
            ? !!u.arm_fecha_fin
            : !!u.sol_fecha_fin
        }));

        setUnions(unionsWithCompletionStatus);
      } catch (err) {
        console.error('Error fetching unions:', err);
        setError(err instanceof Error ? err.message : 'Error al cargar uniones');
      } finally {
        setLoading(false);
      }
    };

    fetchUnions();
  }, [state.selectedSpool, state.selectedOperation]);

  // Calculate available unions (non-completed)
  const availableUnions = useMemo(() => {
    return unions.filter(u => !u.is_completed);
  }, [unions]);

  // Calculate selected pulgadas in real-time
  const selectedPulgadas = useMemo(() => {
    if (state.selectedUnions.length === 0) return 0;

    const total = unions
      .filter(u => state.selectedUnions.includes(u.n_union))
      .reduce((sum, u) => sum + u.dn_union, 0);

    return Math.round(total * 10) / 10; // 1 decimal precision
  }, [unions, state.selectedUnions]);

  // Handle "Seleccionar Todas" button
  const handleSelectAll = () => {
    const availableNumbers = availableUnions.map(u => u.n_union);
    setState({ selectedUnions: availableNumbers });
  };

  // Handle continue button click
  const handleContinue = () => {
    if (state.selectedUnions.length === 0) {
      // Show zero-selection modal
      setShowZeroModal(true);
    } else {
      // Navigate to confirmar with selections
      setState({ pulgadasCompletadas: selectedPulgadas });
      router.push('/confirmar');
    }
  };

  // Handle "Liberar Spool" confirmation (zero-selection flow)
  const handleLiberarSpool = () => {
    setState({
      selectedUnions: [],
      pulgadasCompletadas: 0
    });
    router.push('/confirmar');
  };

  // Handle selection change from UnionTable
  const handleSelectionChange = (newSelection: number[]) => {
    setState({ selectedUnions: newSelection });
  };

  if (!state.selectedSpool || !state.selectedOperation) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <div className="bg-white border-b-2 border-gray-200 px-6 py-4">
        <h1 className="text-2xl font-bold text-gray-900">
          Seleccionar Uniones - {state.selectedSpool}
        </h1>
        <p className="text-sm text-gray-600 mt-1">
          Operación: {state.selectedOperation}
        </p>
      </div>

      {/* Sticky Counter */}
      <div className="sticky top-0 z-10 bg-white border-b p-4 shadow-sm">
        <div className="text-lg font-medium text-gray-900">
          Seleccionadas: {state.selectedUnions.length}/{availableUnions.length} | Pulgadas: {selectedPulgadas.toFixed(1)}&quot;
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center h-64">
          <div className="text-gray-500 text-lg">Cargando uniones...</div>
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="mx-6 mt-6">
          <div className="bg-red-50 border border-red-200 rounded p-4">
            <p className="text-red-700">{error}</p>
          </div>
        </div>
      )}

      {/* Main Content - Union Selection */}
      {!loading && !error && (
        <div className="flex-1 px-6 py-4 overflow-auto">
          {/* "Seleccionar Todas" Button */}
          {availableUnions.length > 0 && (
            <div className="mb-4">
              <button
                onClick={handleSelectAll}
                className="px-6 py-3 bg-blue-600 text-white font-medium rounded hover:bg-blue-700 transition-colors"
              >
                Seleccionar Todas ({availableUnions.length} disponibles)
              </button>
            </div>
          )}

          {/* Union Table */}
          <UnionTable
            unions={unions}
            operacion={state.selectedOperation as 'ARM' | 'SOLD'}
            selectedUnions={state.selectedUnions}
            onSelectionChange={handleSelectionChange}
            disabled={false}
          />
        </div>
      )}

      {/* Sticky Continue Button */}
      {!loading && !error && (
        <div className="sticky bottom-0 z-10 bg-white p-4 border-t shadow-lg">
          <Button
            onClick={handleContinue}
            variant="primary"
            className="h-20 text-xl"
          >
            Continuar
          </Button>
        </div>
      )}

      {/* Zero-Selection Modal */}
      <Modal
        isOpen={showZeroModal}
        onClose={() => setShowZeroModal(false)}
        onBackdropClick={null}
      >
        <div className="text-center">
          <h3 className="text-lg font-semibold mb-4">¿Liberar sin registrar?</h3>
          <p className="text-gray-600 mb-6">
            No has seleccionado ninguna unión. El spool será liberado sin registrar trabajo.
          </p>
          <div className="flex gap-4 justify-center">
            <Button
              variant="cancel"
              onClick={() => setShowZeroModal(false)}
              className="h-14 px-6"
            >
              Cancelar
            </Button>
            <Button
              variant="primary"
              onClick={handleLiberarSpool}
              className="h-14 px-6"
            >
              Liberar Spool
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
