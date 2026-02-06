'use client';

import { useState, useEffect, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';
import { Puzzle, Flame, ArrowLeft, X } from 'lucide-react';
import { useAppState } from '@/lib/context';
import { UnionTable } from '@/components/UnionTable';
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
    if (!state.selectedSpool || !state.selectedOperation || state.selectedOperation === 'METROLOGIA') {
      router.push('/');
    }
  }, [state.selectedSpool, state.selectedOperation, router]);

  // Clear any legacy selections on mount (before session storage restoration)
  useEffect(() => {
    setState({ selectedUnions: [], pulgadasCompletadas: 0 });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Run only once on mount

  // Restore selection from session storage on mount if exists
  useEffect(() => {
    if (state.selectedSpool) {
      const saved = sessionStorage.getItem(`unions_selection_${state.selectedSpool}`);
      if (saved) {
        try {
          const parsed = JSON.parse(saved);
          // Validate format: must be array of strings (IDs like "TEST-03+1")
          // Legacy format was array of numbers [1, 2, 3] - clear those
          if (Array.isArray(parsed) && parsed.every(item => typeof item === 'string')) {
            setState({ selectedUnions: parsed });
          } else {
            // Clear legacy number-based selection
            sessionStorage.removeItem(`unions_selection_${state.selectedSpool}`);
            setState({ selectedUnions: [] });
          }
        } catch {
          // Invalid JSON, ignore and clear
          sessionStorage.removeItem(`unions_selection_${state.selectedSpool}`);
        }
      }
    }
  }, [state.selectedSpool, setState]);

  // Save selection to session storage on change
  useEffect(() => {
    if (state.selectedSpool && state.selectedUnions.length > 0) {
      sessionStorage.setItem(
        `unions_selection_${state.selectedSpool}`,
        JSON.stringify(state.selectedUnions)
      );
    }
  }, [state.selectedUnions, state.selectedSpool]);

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

        // Sort by n_union ascending
        const sorted = response.unions.sort((a, b) => a.n_union - b.n_union);

        // Mark completed unions based on operation
        const unionsWithCompletionStatus = sorted.map(u => ({
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
      .filter(u => state.selectedUnions.includes(u.id))
      .reduce((sum, u) => sum + u.dn_union, 0);

    return Math.round(total * 10) / 10; // 1 decimal precision
  }, [unions, state.selectedUnions]);

  // Handle "Seleccionar Todas" button
  const handleSelectAll = () => {
    const availableIds = availableUnions.map(u => u.id);
    setState({ selectedUnions: availableIds });
  };

  // Handle continue button click
  const handleContinue = async () => {
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
  const handleSelectionChange = (newSelection: string[]) => {
    setState({ selectedUnions: newSelection });
  };

  if (!state.selectedSpool || !state.selectedOperation) {
    return null;
  }

  // Determine operation icon
  const OperationIcon = state.selectedOperation === 'ARM' ? Puzzle : Flame;

  return (
    <div
      className="min-h-screen bg-[#001F3F]"
      style={{
        backgroundImage: `
          linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
          linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)
        `,
        backgroundSize: '50px 50px'
      }}
    >
      {/* Logo */}
      <div className="flex justify-center pt-8 pb-6 tablet:header-compact border-b-4 border-white/30">
        <Image
          src="/logos/logo-grisclaro-F8F9FA.svg"
          alt="Kronos Mining"
          width={200}
          height={80}
          priority
        />
      </div>

      {/* Header con operación */}
      <div className="px-10 tablet:px-6 narrow:px-5 py-6 tablet:py-4 border-b-4 border-white/30">
        <div className="flex items-center justify-center gap-4 mb-4">
          <OperationIcon size={48} strokeWidth={3} className="text-zeues-orange" />
          <h2 className="text-3xl narrow:text-2xl font-black text-white tracking-[0.25em] font-mono">
            SELECCIONAR UNIONES - {state.selectedSpool}
          </h2>
        </div>
        <p className="text-xl narrow:text-lg text-center text-white/70 font-mono tracking-[0.15em]">
          OPERACIÓN: {state.selectedOperation}
        </p>
      </div>

      {/* Sticky Counter */}
      <div className="sticky top-0 z-10 bg-[#001F3F] border-b-4 border-zeues-orange p-4 shadow-md">
        <div className="text-xl narrow:text-lg font-black text-center text-white font-mono tracking-[0.15em]">
          SELECCIONADAS: {state.selectedUnions.length}/{availableUnions.length} | PULGADAS: {selectedPulgadas.toFixed(1)}&quot;
        </div>
      </div>

      {/* Content */}
      <div className="p-8 tablet:p-5 tablet:pb-footer">
        {/* Loading State */}
        {loading && (
          <div className="flex flex-col items-center justify-center py-20">
            <div className="text-xl font-black text-white font-mono">CARGANDO UNIONES...</div>
          </div>
        )}

        {/* Error State */}
        {error && !loading && (
          <div className="border-4 border-red-500 p-8 mb-6 bg-red-500/10">
            <h3 className="text-2xl font-black text-red-500 font-mono mb-4">ERROR</h3>
            <p className="text-lg text-white font-mono mb-6">{error}</p>
            <button
              onClick={() => window.location.reload()}
              className="px-6 py-3 border-4 border-white text-white font-mono font-black active:bg-white active:text-[#001F3F] transition-all"
            >
              REINTENTAR
            </button>
          </div>
        )}

        {/* Main Content - Union Selection */}
        {!loading && !error && (
          <>
            {/* "Seleccionar Todas" Button */}
            {availableUnions.length > 0 && (
              <div className="mb-6">
                <button
                  onClick={handleSelectAll}
                  className="
                    w-full h-16 tablet:h-14
                    bg-transparent
                    border-4 border-white
                    flex items-center justify-center
                    active:bg-zeues-orange active:border-zeues-orange
                    transition-all duration-200
                    group
                  "
                >
                  <span className="text-xl narrow:text-lg font-black text-white font-mono tracking-[0.15em] group-active:text-white">
                    SELECCIONAR TODAS ({availableUnions.length} DISPONIBLES)
                  </span>
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
          </>
        )}
      </div>

      {/* Fixed Navigation Footer */}
      {!loading && !error && (
        <div className="fixed bottom-0 left-0 right-0 bg-[#001F3F] z-50 border-t-4 border-white/30 p-6 tablet:p-5">
          <div className="flex flex-col gap-4 tablet:gap-3">
            {/* Botón Continuar */}
            <button
              onClick={handleContinue}
              className="
                w-full h-16 tablet:h-14
                bg-transparent
                border-4 border-white
                flex items-center justify-center
                active:bg-zeues-orange active:border-zeues-orange
                transition-all duration-200
                group
              "
            >
              <span className="text-xl narrow:text-lg font-black text-white font-mono tracking-[0.15em] group-active:text-white">
                CONTINUAR
              </span>
            </button>

            {/* Botones Volver */}
            <div className="flex gap-4 tablet:gap-3 narrow:flex-col narrow:gap-3">
              <button
                onClick={() => router.back()}
                className="
                  flex-1 narrow:w-full h-16 tablet:h-14
                  bg-transparent
                  border-4 border-white
                  flex items-center justify-center gap-3
                  active:bg-white active:text-[#001F3F]
                  transition-all duration-200
                  group
                "
              >
                <ArrowLeft size={24} strokeWidth={3} className="text-white group-active:text-[#001F3F]" />
                <span className="text-xl narrow:text-lg font-black text-white font-mono tracking-[0.15em] group-active:text-[#001F3F]">
                  VOLVER
                </span>
              </button>

              <button
                onClick={() => router.push('/')}
                className="
                  flex-1 narrow:w-full h-16 tablet:h-14
                  bg-transparent
                  border-4 border-red-500
                  flex items-center justify-center gap-3
                  active:bg-red-500 active:border-red-500
                  transition-all duration-200
                  group
                "
              >
                <X size={24} strokeWidth={3} className="text-red-500 group-active:text-white" />
                <span className="text-xl narrow:text-lg font-black text-red-500 font-mono tracking-[0.15em] group-active:text-white">
                  INICIO
                </span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Zero-Selection Modal */}
      {showZeroModal && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-6">
          <div className="bg-[#001F3F] border-4 border-white p-8 max-w-lg w-full">
            <h3 className="text-2xl font-black text-white font-mono tracking-[0.15em] mb-4 text-center">
              ¿LIBERAR SIN REGISTRAR?
            </h3>
            <p className="text-lg text-white/70 font-mono mb-8 text-center">
              No has seleccionado ninguna unión. El spool será liberado sin registrar trabajo.
            </p>
            <div className="flex gap-4">
              <button
                onClick={() => setShowZeroModal(false)}
                className="
                  flex-1 h-14
                  bg-transparent
                  border-4 border-white
                  active:bg-white active:text-[#001F3F]
                  transition-all duration-200
                "
              >
                <span className="text-lg font-black text-white font-mono tracking-[0.15em]">
                  CANCELAR
                </span>
              </button>
              <button
                onClick={handleLiberarSpool}
                className="
                  flex-1 h-14
                  bg-transparent
                  border-4 border-zeues-orange
                  active:bg-zeues-orange
                  transition-all duration-200
                "
              >
                <span className="text-lg font-black text-zeues-orange font-mono tracking-[0.15em]">
                  LIBERAR SPOOL
                </span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
