'use client';

import { Suspense, useState, useEffect, useCallback, useMemo } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Image from 'next/image';
import { Loader2, AlertCircle } from 'lucide-react';
import { useAppState } from '@/lib/context';
import { getSpoolsDisponible, getSpoolsOcupados, getSpoolsParaIniciar, getSpoolsReparacion, iniciarSpool } from '@/lib/api';
import { detectSpoolVersion } from '@/lib/version';
import { OPERATION_ICONS } from '@/lib/operation-config';
import { classifyApiError } from '@/lib/error-classifier';
import { useDebounce } from '@/hooks/useDebounce';
import { getOperationLabel, getPageTitle, getEmptyMessage, MAX_BATCH_SELECTION } from '@/lib/spool-selection-utils';
import { BlueprintPageWrapper } from '@/components/BlueprintPageWrapper';
import { SpoolFilterPanel } from '@/components/SpoolFilterPanel';
import { SpoolTable } from '@/components/SpoolTable';
import { SpoolSelectionFooter } from '@/components/SpoolSelectionFooter';
import { BatchLimitModal } from '@/components/BatchLimitModal';
import type { Spool } from '@/lib/types';

function SeleccionarSpoolContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const tipo = searchParams.get('tipo') as 'tomar' | 'pausar' | 'completar' | 'cancelar' | 'metrologia' | 'reparacion';
  const { state, setState } = useAppState();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [spools, setSpools] = useState<Spool[]>([]);
  const [showBatchLimitModal, setShowBatchLimitModal] = useState(false);
  const [batchLimitTotal, setBatchLimitTotal] = useState(0);

  // Local filter states
  const [searchNV, setSearchNV] = useState('');
  const [searchTag, setSearchTag] = useState('');

  // Filter expansion state (sessionStorage - persists during session only)
  const [isFilterExpanded, setIsFilterExpanded] = useState(() => {
    if (typeof window !== 'undefined') {
      const stored = sessionStorage.getItem('spool-filter-expanded');
      return stored === 'true';
    }
    return false;
  });

  // Persist expansion state to sessionStorage
  useEffect(() => {
    if (typeof window !== 'undefined') {
      sessionStorage.setItem('spool-filter-expanded', String(isFilterExpanded));
    }
  }, [isFilterExpanded]);

  const fetchSpools = useCallback(async () => {
    try {
      setLoading(true);
      setError('');
      setSpools([]);

      const { selectedWorker, selectedOperation, accion } = state;

      if (!selectedOperation) {
        setError('No se ha seleccionado una operacion');
        setLoading(false);
        return;
      }

      let fetchedSpools: Spool[];

      // v4.0: Handle INICIAR/FINALIZAR workflows (accion-based, no tipo parameter)
      if (accion === 'INICIAR') {
        fetchedSpools = await getSpoolsDisponible(selectedOperation as 'ARM' | 'SOLD' | 'REPARACION');
      } else if (accion === 'FINALIZAR') {
        if (!selectedWorker) {
          setError('No se ha seleccionado un trabajador');
          setLoading(false);
          return;
        }
        fetchedSpools = await getSpoolsOcupados(selectedWorker.id, selectedOperation as 'ARM' | 'SOLD' | 'REPARACION');
      } else if (tipo === 'metrologia') {
        fetchedSpools = await getSpoolsParaIniciar('METROLOGIA' as 'ARM' | 'SOLD');
      } else if (tipo === 'reparacion') {
        const reparacionResponse = await getSpoolsReparacion();
        fetchedSpools = reparacionResponse.spools as unknown as Spool[];
      } else if (tipo === 'tomar') {
        fetchedSpools = await getSpoolsDisponible(selectedOperation as 'ARM' | 'SOLD' | 'REPARACION');
      } else if (tipo === 'pausar' || tipo === 'completar') {
        if (!selectedWorker) {
          setError('No se ha seleccionado un trabajador');
          setLoading(false);
          return;
        }
        fetchedSpools = await getSpoolsOcupados(selectedWorker.id, selectedOperation as 'ARM' | 'SOLD' | 'REPARACION');
      } else if (tipo === 'cancelar') {
        if (!selectedWorker) {
          setError('No se ha seleccionado un trabajador');
          setLoading(false);
          return;
        }
        fetchedSpools = await getSpoolsOcupados(selectedWorker.id, selectedOperation as 'ARM' | 'SOLD' | 'REPARACION');
      } else {
        setError('Tipo de accion no valido');
        setLoading(false);
        return;
      }

      // v4.0: Detect version from spool.total_uniones (no API calls needed)
      const spoolsWithVersion = fetchedSpools.map(spool => ({
        ...spool,
        version: detectSpoolVersion(spool)
      }));

      // v4.0: Apply filtering based on action type (INICIAR vs FINALIZAR)
      let filtered = spoolsWithVersion;

      if (accion === 'INICIAR') {
        filtered = spoolsWithVersion.filter(spool => {
          const isDisponible = !spool.ocupado_por || spool.ocupado_por === 'DISPONIBLE' || spool.ocupado_por === '';
          return isDisponible;
        });
      } else if (accion === 'FINALIZAR') {
        if (selectedWorker) {
          const workerPattern = `(${selectedWorker.id})`;
          filtered = spoolsWithVersion.filter(spool => {
            return spool.ocupado_por && spool.ocupado_por.includes(workerPattern);
          });
        } else {
          filtered = [];
        }
      }

      setSpools(filtered);
      setLoading(false);
    } catch (err) {
      console.error('Error fetching spools:', err);
      const classified = classifyApiError(err);
      setError(classified.userMessage);
      setLoading(false);
    }
  }, [state, tipo]);

  // Initial load
  useEffect(() => {
    if (!state.selectedWorker || !state.selectedOperation || (!tipo && !state.accion)) {
      router.push('/');
      return;
    }
    fetchSpools();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Debounced search values (500ms delay)
  const debouncedSearchNV = useDebounce(searchNV, 500);
  const debouncedSearchTag = useDebounce(searchTag, 500);

  // Filter spools with useMemo
  const spoolsFiltrados = useMemo(() => {
    return spools.filter(s =>
      (s.nv ?? '').toLowerCase().includes(debouncedSearchNV.toLowerCase()) &&
      s.tag_spool.toLowerCase().includes(debouncedSearchTag.toLowerCase())
    );
  }, [spools, debouncedSearchNV, debouncedSearchTag]);

  // Derived state: active filters count
  const activeFiltersCount = [
    debouncedSearchNV.trim() !== '',
    debouncedSearchTag.trim() !== ''
  ].filter(Boolean).length;

  // Toggle selection
  const toggleSelect = (tag: string) => {
    const currentSelected = state.selectedSpools || [];
    const isSelected = currentSelected.includes(tag);

    if (isSelected) {
      setState({ selectedSpools: currentSelected.filter(t => t !== tag) });
    } else {
      setState({ selectedSpools: [...currentSelected, tag] });
    }
  };

  // Select/Deselect all (with batch limit)
  const handleSelectAll = () => {
    const availableTags = spoolsFiltrados.map(s => s.tag_spool);
    const toSelect = availableTags.slice(0, MAX_BATCH_SELECTION);

    if (availableTags.length > MAX_BATCH_SELECTION) {
      setBatchLimitTotal(availableTags.length);
      setShowBatchLimitModal(true);
    }

    setState({ selectedSpools: toSelect });
  };

  const handleDeselectAll = () => {
    setState({ selectedSpools: [] });
  };

  const handleClearFilters = () => {
    setSearchNV('');
    setSearchTag('');
  };

  // v2.0/v4.0: Navigate with selections (auto-detect single vs batch)
  const handleContinueWithBatch = async () => {
    const selectedCount = (state.selectedSpools || []).length;

    if (selectedCount === 0) return;

    // Cache version per session (v4.0 Phase 9)
    state.selectedSpools?.forEach((tag) => {
      const spool = spools.find(s => s.tag_spool === tag);
      if (spool?.version) {
        sessionStorage.setItem(`spool_version_${tag}`, spool.version);
      }
    });

    // v4.0: INICIAR workflow - call API to occupy spool, then navigate to success
    if (state.accion === 'INICIAR' && selectedCount === 1 && state.selectedWorker && state.selectedOperation) {
      try {
        setLoading(true);
        const tag = state.selectedSpools[0];
        const workerNombre = `${state.selectedWorker.nombre.charAt(0)}${(state.selectedWorker.apellido || '').charAt(0)}(${state.selectedWorker.id})`;

        await iniciarSpool({
          tag_spool: tag,
          worker_id: state.selectedWorker.id,
          worker_nombre: workerNombre,
          operacion: state.selectedOperation as 'ARM' | 'SOLD'
        });

        setState({
          selectedSpool: tag,
          selectedSpools: [],
        });

        router.push('/exito');
        return;
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Error desconocido';
        setError(errorMessage);
        setLoading(false);
        return;
      }
    }

    // v4.0: FINALIZAR workflow - navigate based on spool version
    if (state.accion === 'FINALIZAR' && selectedCount === 1) {
      const tag = state.selectedSpools[0];
      const selectedSpool = spools.find(s => s.tag_spool === tag);
      const isV4 = selectedSpool?.version === 'v4.0';

      setState({
        selectedSpool: tag,
        selectedSpools: [],
      });

      // REPARACION: skip union selection (operates at spool level)
      if (state.selectedOperation === 'REPARACION') {
        router.push('/confirmar');
      } else if (isV4) {
        router.push('/seleccionar-uniones');
      } else {
        router.push('/confirmar');
      }
      return;
    }

    // METROLOGIA: Navigate to resultado page (single spool only)
    if (tipo === 'metrologia') {
      if (selectedCount === 1) {
        setState({
          selectedSpool: state.selectedSpools[0],
          selectedSpools: [],
        });
        router.push('/resultado-metrologia');
      }
      return;
    }

    // REPARACION: Navigate to confirmar page (single spool only)
    if (tipo === 'reparacion') {
      if (selectedCount === 1) {
        setState({
          selectedSpool: state.selectedSpools[0],
          selectedSpools: [],
        });
        router.push('/confirmar?tipo=reparacion');
      }
      return;
    }

    // ARM/SOLD: Normal flow to confirmar page
    if (selectedCount === 1) {
      setState({
        selectedSpool: state.selectedSpools[0],
        selectedSpools: [],
      });
    } else {
      setState({
        selectedSpool: null,
      });
    }

    router.push(`/confirmar?tipo=${tipo}`);
  };

  if (!state.selectedWorker || !state.selectedOperation) return null;

  const operationLabel = getOperationLabel(state.selectedOperation);
  const OperationIcon = OPERATION_ICONS[state.selectedOperation];
  const selectedCount = (state.selectedSpools || []).length;

  const pageTitle = getPageTitle({
    accion: state.accion,
    tipo,
    operationLabel,
    selectedOperation: state.selectedOperation,
  });

  const emptyMessage = getEmptyMessage({
    accion: state.accion,
    tipo,
    operationLabel,
    selectedOperation: state.selectedOperation,
  });

  return (
    <BlueprintPageWrapper>
      {/* Logo */}
      <div className="flex justify-center pt-4 pb-3 tablet:header-compact narrow:header-compact border-b-4 border-white/30">
        <Image
          src="/logos/logo-grisclaro-F8F9FA.svg"
          alt="Kronos Mining"
          width={140}
          height={56}
          priority
        />
      </div>

      {/* Header */}
      <div className="px-10 tablet:px-6 narrow:px-5 py-6 tablet:py-4 border-b-4 border-white/30">
        <div className="flex items-center justify-center gap-4 mb-4">
          <OperationIcon size={48} strokeWidth={3} className="text-zeues-orange" />
          <h2 className="text-3xl narrow:text-2xl font-black text-white tracking-[0.25em] font-mono">
            {pageTitle}
          </h2>
        </div>
      </div>

      {/* Content */}
      <div className="p-8 tablet:p-5 pb-footer tablet:pb-footer narrow:pb-footer">
        {/* Loading State */}
        {loading && (
          <div className="flex flex-col items-center justify-center py-20">
            <Loader2 size={64} className="text-zeues-orange animate-spin mb-4" strokeWidth={3} />
            <span className="text-xl font-black text-white font-mono">CARGANDO SPOOLS...</span>
          </div>
        )}

        {/* Error State */}
        {error && !loading && (
          <div className="border-4 border-red-500 p-8 mb-6 bg-red-500/10">
            <div className="flex items-center gap-4 mb-4">
              <AlertCircle size={48} className="text-red-500" strokeWidth={3} />
              <h3 className="text-2xl font-black text-red-500 font-mono">ERROR</h3>
            </div>
            <p className="text-lg text-white font-mono mb-6">{error}</p>
            <button
              onClick={fetchSpools}
              className="px-6 py-3 border-4 border-white text-white font-mono font-black active:bg-white active:text-[#001F3F]"
            >
              REINTENTAR
            </button>
          </div>
        )}

        {/* Empty State - No spools available */}
        {!loading && !error && spools.length === 0 && (
          <div className="border-4 border-white/50 p-8 mb-6 bg-white/5">
            <div className="flex items-center gap-4 mb-4">
              <AlertCircle size={48} className="text-white/70" strokeWidth={3} />
              <h3 className="text-2xl font-black text-white/70 font-mono">SIN SPOOLS</h3>
            </div>
            <p className="text-lg text-white/70 font-mono">{emptyMessage}</p>
          </div>
        )}

        {/* Main Content - Filter Panel + Table */}
        {!loading && !error && spools.length > 0 && (
          <div className="mb-6 tablet:mb-4">
            <SpoolFilterPanel
              isExpanded={isFilterExpanded}
              onToggleExpand={() => setIsFilterExpanded(prev => !prev)}
              searchNV={searchNV}
              onSearchNVChange={setSearchNV}
              searchTag={searchTag}
              onSearchTagChange={setSearchTag}
              selectedCount={selectedCount}
              filteredCount={spoolsFiltrados.length}
              activeFiltersCount={activeFiltersCount}
              onSelectAll={handleSelectAll}
              onDeselectAll={handleDeselectAll}
              onClearFilters={handleClearFilters}
            />

            <SpoolTable
              spools={spoolsFiltrados}
              selectedSpools={state.selectedSpools || []}
              onToggleSelect={toggleSelect}
              tipo={tipo}
            />
          </div>
        )}
      </div>

      {/* Fixed Navigation Footer */}
      {!loading && !error && (
        <SpoolSelectionFooter
          selectedCount={selectedCount}
          hasSpools={spools.length > 0}
          onContinue={handleContinueWithBatch}
          onBack={() => router.back()}
          onHome={() => router.push('/')}
        />
      )}

      {/* Batch Limit Modal (replaces native alert) */}
      <BatchLimitModal
        isOpen={showBatchLimitModal}
        onClose={() => setShowBatchLimitModal(false)}
        maxBatch={MAX_BATCH_SELECTION}
        totalAvailable={batchLimitTotal}
      />
    </BlueprintPageWrapper>
  );
}

export default function SeleccionarSpoolPage() {
  return (
    <Suspense fallback={
      <BlueprintPageWrapper>
        <div className="flex items-center justify-center min-h-screen">
          <Loader2 size={64} className="text-zeues-orange animate-spin" strokeWidth={3} />
        </div>
      </BlueprintPageWrapper>
    }>
      <SeleccionarSpoolContent />
    </Suspense>
  );
}
