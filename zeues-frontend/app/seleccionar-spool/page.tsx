'use client';

import { Suspense, useState, useEffect, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Image from 'next/image';
import { Puzzle, Flame, SearchCheck, Wrench, Search, CheckSquare, Square, ArrowLeft, X, Loader2, AlertCircle, Lock } from 'lucide-react';
import { useAppState } from '@/lib/context';
import { getSpoolsDisponible, getSpoolsOcupados, getSpoolsParaIniciar, getSpoolsParaCancelar, getSpoolsReparacion, detectVersionFromSpool, iniciarSpool } from '@/lib/api';
import type { Spool, SSEEvent } from '@/lib/types';
import { useSSE } from '@/lib/hooks/useSSE';
import { ConnectionStatus } from '@/components/ConnectionStatus';

function SeleccionarSpoolContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const tipo = searchParams.get('tipo') as 'tomar' | 'pausar' | 'completar' | 'cancelar' | 'metrologia' | 'reparacion';
  const { state, setState } = useAppState();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [spools, setSpools] = useState<Spool[]>([]);
  const [raceConditionError, setRaceConditionError] = useState<string>('');

  // Local filter states
  const [searchNV, setSearchNV] = useState('');
  const [searchTag, setSearchTag] = useState('');
  const [shouldRefresh, setShouldRefresh] = useState(0);

  // SSE real-time updates
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const handleSSEMessage = useCallback((event: SSEEvent) => {
    const { type, tag_spool, estado_detalle } = event;

    switch (type) {
      case 'TOMAR':
        // Another worker took this spool - remove from available list
        setSpools(currentSpools => currentSpools.filter(s => s.tag_spool !== tag_spool));
        break;

      case 'PAUSAR':
        // Spool released - refresh list to potentially add it back
        setShouldRefresh(prev => prev + 1);
        break;

      case 'COMPLETAR':
        // Operation completed - remove from available list
        setSpools(currentSpools => currentSpools.filter(s => s.tag_spool !== tag_spool));
        break;

      case 'STATE_CHANGE':
        // Update estado_detalle for context display
        setSpools(currentSpools =>
          currentSpools.map(s =>
            s.tag_spool === tag_spool
              ? { ...s, estado_detalle }
              : s
          )
        );
        break;
    }
  }, []);

  const { isConnected } = useSSE(`${API_URL}/api/sse/stream`, {
    onMessage: handleSSEMessage,
    onError: (error) => {
      console.error('SSE connection error:', error);
    },
    openWhenHidden: false  // Close connection when page backgrounded
  });

  const fetchSpools = useCallback(async () => {
    try {
      setLoading(true);
      setError('');
      setSpools([]);

      const { selectedWorker, selectedOperation, accion } = state;

      if (!selectedOperation) {
        setError('No se ha seleccionado una operación');
        setLoading(false);
        return;
      }

      let fetchedSpools: Spool[];

      // v4.0: Handle INICIAR/FINALIZAR workflows (accion-based, no tipo parameter)
      if (accion === 'INICIAR') {
        // INICIAR shows available spools for the operation
        fetchedSpools = await getSpoolsDisponible(selectedOperation as 'ARM' | 'SOLD' | 'REPARACION');
      } else if (accion === 'FINALIZAR') {
        // FINALIZAR shows spools occupied by current worker
        if (!selectedWorker) {
          setError('No se ha seleccionado un trabajador');
          setLoading(false);
          return;
        }
        fetchedSpools = await getSpoolsOcupados(selectedWorker.id, selectedOperation as 'ARM' | 'SOLD' | 'REPARACION');
      } else if (tipo === 'metrologia') {
        // v3.0: METROLOGIA uses 'metrologia' tipo
        fetchedSpools = await getSpoolsParaIniciar('METROLOGIA' as 'ARM' | 'SOLD');
      } else if (tipo === 'reparacion') {
        // REPARACION uses dedicated endpoint - returns object with spools array
        const reparacionResponse = await getSpoolsReparacion();
        fetchedSpools = reparacionResponse.spools as unknown as Spool[];
      } else if (tipo === 'tomar') {
        // v3.0: TOMAR shows available spools for the operation
        fetchedSpools = await getSpoolsDisponible(selectedOperation as 'ARM' | 'SOLD' | 'REPARACION');
      } else if (tipo === 'pausar' || tipo === 'completar') {
        // v3.0: PAUSAR/COMPLETAR show spools occupied by current worker
        if (!selectedWorker) {
          setError('No se ha seleccionado un trabajador');
          setLoading(false);
          return;
        }
        fetchedSpools = await getSpoolsOcupados(selectedWorker.id, selectedOperation as 'ARM' | 'SOLD' | 'REPARACION');
      } else if (tipo === 'cancelar') {
        // v3.0: CANCELAR shows reparación spools occupied by current worker
        if (!selectedWorker) {
          setError('No se ha seleccionado un trabajador');
          setLoading(false);
          return;
        }
        // CANCELAR is only for REPARACION in v3.0
        if (selectedOperation === 'REPARACION') {
          fetchedSpools = await getSpoolsOcupados(selectedWorker.id, 'REPARACION');
        } else {
          // For ARM/SOLD, CANCELAR uses cancelar endpoint
          fetchedSpools = await getSpoolsParaCancelar(selectedOperation as 'ARM' | 'SOLD', selectedWorker.id);
        }
      } else {
        // Fallback for any invalid tipo/accion values
        setError('Tipo de acción no válido');
        setLoading(false);
        return;
      }

      // v4.0: Detect version from spool.total_uniones (no API calls needed)
      // Optimized: O(1) instead of O(N) API calls
      const spoolsWithVersion = fetchedSpools.map(spool => ({
        ...spool,
        version: (spool.total_uniones && spool.total_uniones > 0) ? 'v4.0' as const : 'v3.0' as const
      }));

      // v4.0: Apply filtering based on action type (INICIAR vs FINALIZAR)
      let filtered = spoolsWithVersion;

      if (accion === 'INICIAR') {
        // Show all available spools (disponibles, not occupied)
        // Backend will validate version compatibility and return clear error if v3.0 spool is used
        // Criteria: STATUS_NV='ABIERTA' AND Status_Spool='EN_PROCESO' AND Ocupado_Por IN ('','DISPONIBLE',null)
        // Note: Spool type doesn't include all backend fields, using type assertion
        filtered = spoolsWithVersion.filter(spool => {
          const ocupadoPor = (spool as { Ocupado_Por?: string }).Ocupado_Por;
          const isDisponible = !ocupadoPor || ocupadoPor === 'DISPONIBLE' || ocupadoPor === '';
          return isDisponible;
        });
      } else if (accion === 'FINALIZAR') {
        // Show only occupied by current worker
        // Criteria: Ocupado_Por contains worker_id
        if (selectedWorker) {
          const workerPattern = `(${selectedWorker.id})`;
          filtered = spoolsWithVersion.filter(spool => {
            const ocupadoPor = (spool as { Ocupado_Por?: string }).Ocupado_Por;
            return ocupadoPor && ocupadoPor.includes(workerPattern);
          });
        } else {
          filtered = [];
        }
      }
      // For v3.0 actions (tipo param) or null, show all (existing behavior)

      setSpools(filtered);
      setLoading(false);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Error desconocido';

      if (errorMessage.includes('red') || errorMessage.includes('conexión')) {
        setError('Error de conexión. Verifica que el servidor esté disponible.');
      } else if (errorMessage.includes('404') || errorMessage.includes('no encontrado')) {
        setError(errorMessage);
      } else if (errorMessage.includes('400') || errorMessage.includes('validación')) {
        setError(errorMessage);
      } else if (errorMessage.includes('503') || errorMessage.includes('servidor')) {
        setError('El servidor no está disponible. Intenta más tarde.');
      } else {
        setError(errorMessage || 'Error al cargar spools. Intenta nuevamente.');
      }

      setLoading(false);
    }
  }, [state, tipo]);

  // Initial load
  useEffect(() => {
    // Redirect if missing required state (allow EITHER tipo parameter OR accion state for v4.0 compatibility)
    if (!state.selectedWorker || !state.selectedOperation || (!tipo && !state.accion)) {
      router.push('/');
      return;
    }
    fetchSpools();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Refresh when SSE triggers PAUSAR event
  useEffect(() => {
    if (shouldRefresh > 0) {
      fetchSpools();
    }
  }, [shouldRefresh, fetchSpools]);

  // Filter spools locally (v2.1.2 - renamed variable to force rebuild)
  const spoolsFiltrados = spools.filter(s =>
    (s.nv ?? '').toLowerCase().includes(searchNV.toLowerCase()) &&
    s.tag_spool.toLowerCase().includes(searchTag.toLowerCase())
  );

  // Debug logging (v2.1.2)
  console.log('[FILTER DEBUG v2.1.2]', {
    totalSpools: spools.length,
    filteredCount: spoolsFiltrados.length,
    searchTag,
    searchNV,
    filteredTags: spoolsFiltrados.map(s => s.tag_spool)
  });

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

  // Select/Deselect all
  const handleSelectAll = () => {
    setState({ selectedSpools: spoolsFiltrados.map(s => s.tag_spool) });
  };

  const handleDeselectAll = () => {
    setState({ selectedSpools: [] });
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

    // v4.0: INICIAR workflow - call API to occupy spool, then navigate to union selection
    if (state.accion === 'INICIAR' && selectedCount === 1 && state.selectedWorker && state.selectedOperation) {
      try {
        setLoading(true);
        const tag = state.selectedSpools[0];
        const workerNombre = `${state.selectedWorker.nombre.charAt(0)}${(state.selectedWorker.apellido || '').charAt(0)}(${state.selectedWorker.id})`;

        // Call INICIAR API to occupy spool (sets Ocupado_Por, creates Redis lock)
        await iniciarSpool({
          tag_spool: tag,
          worker_id: state.selectedWorker.id,
          worker_nombre: workerNombre,
          operacion: state.selectedOperation as 'ARM' | 'SOLD'
        });

        // Set single spool selection and change accion to FINALIZAR
        // (INICIAR is complete, next step is FINALIZAR after union selection)
        setState({
          selectedSpool: tag,
          selectedSpools: [],
          batchMode: false,
          accion: 'FINALIZAR'  // Change from INICIAR to FINALIZAR for next step
        });

        // Navigate to union selection (P5) - NOT to success page
        router.push('/seleccionar-uniones');
        return;
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Error desconocido';
        setError(errorMessage);
        setLoading(false);
        return;
      }
    }

    // METROLOGIA: Navigate to resultado page (single spool only)
    if (tipo === 'metrologia') {
      if (selectedCount === 1) {
        setState({
          selectedSpool: state.selectedSpools[0],
          selectedSpools: [],
          batchMode: false
        });
        router.push('/resultado-metrologia');
      }
      return;
    }

    // REPARACION: Navigate to tipo-interaccion page (single spool only for Phase 6 simplicity)
    if (tipo === 'reparacion') {
      if (selectedCount === 1) {
        setState({
          selectedSpool: state.selectedSpools[0],
          selectedSpools: [],
          batchMode: false
        });
        router.push('/tipo-interaccion');
      }
      return;
    }

    // ARM/SOLD: Normal flow to confirmar page
    if (selectedCount === 1) {
      setState({
        selectedSpool: state.selectedSpools[0],
        selectedSpools: [],
        batchMode: false
      });
    } else {
      setState({
        selectedSpool: null,
        batchMode: true
      });
    }

    router.push(`/confirmar?tipo=${tipo}`);
  };

  if (!state.selectedWorker || !state.selectedOperation) return null;

  // v3.0: Updated action labels for new tipo values
  const actionLabel = tipo === 'tomar' ? 'TOMAR' :
                      tipo === 'pausar' ? 'PAUSAR' :
                      tipo === 'completar' ? 'COMPLETAR' :
                      tipo === 'cancelar' ? 'CANCELAR' :
                      tipo === 'metrologia' ? 'INSPECCIONAR' :
                      tipo === 'reparacion' ? 'REPARAR' : 'SELECCIONAR';
  const operationLabel = state.selectedOperation === 'ARM' ? 'ARMADO' :
                        state.selectedOperation === 'SOLD' ? 'SOLDADURA' :
                        state.selectedOperation === 'METROLOGIA' ? 'METROLOGÍA' : 'REPARACIÓN';

  // v3.0/v4.0: Dynamic page title based on tipo or accion
  const getPageTitle = () => {
    // v4.0: Check accion first (INICIAR/FINALIZAR)
    if (state.accion === 'INICIAR') {
      return `SELECCIONAR SPOOL PARA INICIAR - ${operationLabel}`;
    }
    if (state.accion === 'FINALIZAR') {
      return `SELECCIONAR SPOOL PARA FINALIZAR - ${operationLabel}`;
    }

    // v3.0: Fall back to tipo-based titles
    switch (tipo) {
      case 'tomar':
        return `SELECCIONAR SPOOL PARA TOMAR - ${operationLabel}`;
      case 'pausar':
        return `SELECCIONAR SPOOL PARA PAUSAR - ${operationLabel}`;
      case 'completar':
        return `SELECCIONAR SPOOL PARA COMPLETAR - ${operationLabel}`;
      case 'cancelar':
        return state.selectedOperation === 'REPARACION'
          ? 'SELECCIONAR REPARACIÓN PARA CANCELAR'
          : `SELECCIONAR SPOOL PARA CANCELAR - ${operationLabel}`;
      case 'metrologia':
        return 'SELECCIONAR SPOOL PARA INSPECCIÓN';
      case 'reparacion':
        return 'SELECCIONAR SPOOL PARA REPARAR';
      default:
        return `${operationLabel} - ${actionLabel}`;
    }
  };

  // v3.0/v4.0: Dynamic empty state message based on tipo or accion
  const getEmptyMessage = () => {
    // v4.0: Check accion first (INICIAR/FINALIZAR)
    if (state.accion === 'INICIAR') {
      return `No hay spools disponibles para iniciar en ${operationLabel}`;
    }
    if (state.accion === 'FINALIZAR') {
      return `No tienes spools ocupados actualmente para ${operationLabel}`;
    }

    // v3.0: Fall back to tipo-based messages
    switch (tipo) {
      case 'tomar':
        return `No hay spools disponibles para ${operationLabel}`;
      case 'pausar':
        return 'No tienes spools en progreso para pausar';
      case 'completar':
        return 'No tienes spools en progreso para completar';
      case 'cancelar':
        return state.selectedOperation === 'REPARACION'
          ? 'No tienes reparaciones en progreso para cancelar'
          : 'No tienes spools en progreso para cancelar';
      case 'metrologia':
        return 'No hay spools disponibles para inspección de metrología';
      case 'reparacion':
        return 'No hay spools rechazados disponibles para reparación';
      default:
        return 'No hay spools disponibles';
    }
  };

  const OperationIcon = state.selectedOperation === 'ARM' ? Puzzle :
                        state.selectedOperation === 'SOLD' ? Flame :
                        state.selectedOperation === 'METROLOGIA' ? SearchCheck : Wrench;

  const selectedCount = (state.selectedSpools || []).length;

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
      {/* Connection Status */}
      <ConnectionStatus connected={isConnected} />

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

      {/* Header */}
      <div className="px-10 tablet:px-6 narrow:px-5 py-6 tablet:py-4 border-b-4 border-white/30">
        <div className="flex items-center justify-center gap-4 mb-4">
          <OperationIcon size={48} strokeWidth={3} className="text-zeues-orange" />
          <h2 className="text-3xl narrow:text-2xl font-black text-white tracking-[0.25em] font-mono">
            {getPageTitle()}
          </h2>
        </div>
      </div>

      {/* Content */}
      <div className="p-8 tablet:p-5 tablet:pb-footer">
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

        {/* Race Condition Warning */}
        {raceConditionError && !loading && (
          <div className="border-4 border-zeues-orange p-8 mb-6 bg-zeues-orange/10">
            <div className="flex items-center gap-4 mb-4">
              <AlertCircle size={48} className="text-zeues-orange" strokeWidth={3} />
              <h3 className="text-2xl font-black text-zeues-orange font-mono">AVISO</h3>
            </div>
            <p className="text-lg text-white font-mono mb-6">{raceConditionError}</p>
            <button
              onClick={() => {
                setRaceConditionError('');
                fetchSpools();
              }}
              className="px-6 py-3 border-4 border-white text-white font-mono font-black active:bg-white active:text-[#001F3F]"
            >
              ACTUALIZAR LISTA
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
            <p className="text-lg text-white/70 font-mono">{getEmptyMessage()}</p>
          </div>
        )}

        {/* Main Content - VAR-1 Table */}
        {!loading && !error && spools.length > 0 && (
          <>
            {/* Version Info Message */}
            {(() => {
              const allSameVersion = spools.every(s => s.version === spools[0]?.version);
              const v4Count = spools.filter(s => s.version === 'v4.0').length;

              if (allSameVersion && spools.length > 0) {
                return (
                  <div className="mb-4 border-2 border-white/30 p-3 bg-white/5">
                    <span className="text-sm font-black text-white/70 font-mono">
                      Todos los spools son versión {spools[0].version}
                    </span>
                  </div>
                );
              } else if (v4Count > 0) {
                return (
                  <div className="mb-4 border-2 border-green-500/50 p-3 bg-green-500/10">
                    <span className="text-sm font-black text-green-400 font-mono">
                      {v4Count} spool{v4Count !== 1 ? 's' : ''} v4.0 (con uniones), {spools.length - v4Count} v3.0
                    </span>
                  </div>
                );
              }
              return null;
            })()}

            <div className="mb-6 tablet:mb-4">
              <div className="border-4 border-white p-6 tablet:p-4 narrow:p-4 mb-4">
                <div className="grid grid-cols-2 narrow:grid-cols-1 gap-4 tablet:gap-3 mb-4 tablet:mb-3">
                  <div>
                    <label className="block text-xs font-black text-white/50 font-mono mb-2">BUSCAR NV</label>
                    <div className="relative">
                      <Search size={20} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/50" />
                      <input
                        type="text"
                        value={searchNV}
                        onChange={(e) => setSearchNV(e.target.value)}
                        placeholder="NV-2024-..."
                        className="w-full h-12 pl-12 narrow:pl-10 pr-4 bg-transparent border-2 border-white text-white font-mono placeholder:text-white/30 focus:outline-none focus:border-zeues-orange"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs font-black text-white/50 font-mono mb-2">BUSCAR TAG</label>
                    <div className="relative">
                      <Search size={20} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/50" />
                      <input
                        type="text"
                        value={searchTag}
                        onChange={(e) => setSearchTag(e.target.value)}
                        placeholder="Buscar TAG..."
                        className="w-full h-12 pl-12 narrow:pl-10 pr-4 bg-transparent border-2 border-white text-white font-mono placeholder:text-white/30 focus:outline-none focus:border-zeues-orange"
                      />
                    </div>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-black text-white/70 font-mono">
                    SELECCIONADOS: {selectedCount} / {spoolsFiltrados.length} FILTRADOS (v2.1.4)
                  </span>
                  <div className="flex gap-2">
                    <button
                      onClick={handleSelectAll}
                      className="px-4 py-2 border-2 border-white text-white font-mono text-xs font-black active:bg-white active:text-[#001F3F]"
                    >
                      TODOS
                    </button>
                    <button
                      onClick={handleDeselectAll}
                      className="px-4 py-2 border-2 border-red-500 text-red-500 font-mono text-xs font-black active:bg-red-500 active:text-white"
                    >
                      NINGUNO
                    </button>
                  </div>
                </div>
              </div>

              {/* Tabla */}
              <div className="border-4 border-white overflow-hidden max-h-96 overflow-y-auto custom-scrollbar">
                <table className="w-full" key={`table-${spoolsFiltrados.length}-${searchTag}-${searchNV}`}>
                  <thead className="sticky top-0 bg-[#001F3F] border-b-4 border-white">
                    <tr>
                      <th className="p-3 text-left text-xs font-black text-white/70 font-mono border-r-2 border-white/30">SEL</th>
                      <th className="p-3 text-left text-xs font-black text-white/70 font-mono border-r-2 border-white/30">TAG SPOOL</th>
                      <th className="p-3 text-left text-xs font-black text-white/70 font-mono border-r-2 border-white/30">VERSION</th>
                      <th className="p-3 text-left text-xs font-black text-white/70 font-mono">{tipo === 'reparacion' ? 'CICLO/ESTADO' : 'NV'}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {/* Render only filtered spools (v2.1.3 - debug render) */}
                    {spoolsFiltrados.map((spool, index) => {
                      console.log(`[RENDER v2.1.3] Row ${index}:`, spool.tag_spool);
                      const isSelected = (state.selectedSpools || []).includes(spool.tag_spool);
                      const isBloqueado = tipo === 'reparacion' && (spool as unknown as { bloqueado?: boolean }).bloqueado;
                      const cycle = tipo === 'reparacion' ? (spool as unknown as { cycle?: number }).cycle : null;

                      // Detect version from spool data (v4.0 Phase 9)
                      const version = spool.version || detectVersionFromSpool(spool);

                      return (
                        <tr
                          key={spool.tag_spool}
                          onClick={() => !isBloqueado && toggleSelect(spool.tag_spool)}
                          className={`border-t-2 border-white/30 transition-colors ${
                            isBloqueado
                              ? 'bg-red-500/20 border-red-500 cursor-not-allowed'
                              : isSelected
                              ? 'bg-zeues-orange/20 cursor-pointer'
                              : 'hover:bg-white/5 cursor-pointer'
                          }`}
                        >
                          <td className="p-3 border-r-2 border-white/30">
                            {isBloqueado ? (
                              <Lock size={24} className="text-red-500" strokeWidth={3} />
                            ) : isSelected ? (
                              <CheckSquare size={24} className="text-zeues-orange" strokeWidth={3} />
                            ) : (
                              <Square size={24} className="text-white/50" strokeWidth={3} />
                            )}
                          </td>
                          <td className="p-3 border-r-2 border-white/30">
                            <span className={`text-lg font-black font-mono ${isBloqueado ? 'text-red-500' : 'text-white'}`}>
                              {spool.tag_spool}
                            </span>
                          </td>
                          <td className="p-3 border-r-2 border-white/30">
                            {/* Version badge - v4.0 green, v3.0 gray */}
                            <span className={`px-2 py-1 text-xs font-black font-mono rounded border-2 ${
                              version === 'v4.0'
                                ? 'bg-green-500/20 text-green-400 border-green-500'
                                : 'bg-gray-500/20 text-gray-400 border-gray-500'
                            }`}>
                              {version}
                            </span>
                          </td>
                          <td className="p-3">
                            {tipo === 'reparacion' ? (
                              <div className="flex items-center gap-2">
                                {isBloqueado ? (
                                  <span className="text-sm font-black text-red-500 font-mono">
                                    BLOQUEADO - Supervisor
                                  </span>
                                ) : (
                                  <span className="text-sm font-black text-yellow-500 font-mono">
                                    Ciclo {cycle}/3
                                  </span>
                                )}
                              </div>
                            ) : (
                              <span className="text-sm font-black text-white/70 font-mono">{spool.nv}</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Fixed Navigation Footer */}
      {!loading && !error && (
        <div className="fixed bottom-0 left-0 right-0 bg-[#001F3F] z-50 border-t-4 border-white/30 p-6 tablet:p-5">
          <div className="flex flex-col gap-4 tablet:gap-3">
            {/* Botón Continuar - Primera fila (only show if spools available) */}
            {spools.length > 0 && (
              <button
                onClick={handleContinueWithBatch}
                disabled={selectedCount === 0}
                className="w-full h-16 tablet:h-14 bg-transparent border-4 border-white flex items-center justify-center gap-4 cursor-pointer active:bg-zeues-orange active:border-zeues-orange transition-all disabled:opacity-30 disabled:cursor-not-allowed group"
              >
                <span className="text-xl tablet:text-lg narrow:text-lg font-black text-white font-mono tracking-[0.2em] group-active:text-white">
                  CONTINUAR CON {selectedCount} SPOOL{selectedCount !== 1 ? 'S' : ''}
                </span>
              </button>
            )}

            {/* Botones Volver/Inicio - Always show */}
            <div className="flex gap-4 tablet:gap-3 narrow:flex-col narrow:gap-3">
              <button
                onClick={() => router.back()}
                className="flex-1 narrow:w-full h-16 tablet:h-14 bg-transparent border-4 border-white flex items-center justify-center gap-3 active:bg-white active:text-[#001F3F] transition-all group"
              >
                <ArrowLeft size={24} strokeWidth={3} className="text-white group-active:text-[#001F3F]" />
                <span className="text-xl tablet:text-lg narrow:text-lg font-black text-white font-mono tracking-[0.15em] group-active:text-[#001F3F]">
                  VOLVER
                </span>
              </button>

              <button
                onClick={() => router.push('/')}
                className="flex-1 narrow:w-full h-16 tablet:h-14 bg-transparent border-4 border-red-500 flex items-center justify-center gap-3 active:bg-red-500 active:border-red-500 transition-all group"
              >
                <X size={24} strokeWidth={3} className="text-red-500 group-active:text-white" />
                <span className="text-xl tablet:text-lg narrow:text-lg font-black text-red-500 font-mono tracking-[0.15em] group-active:text-white">
                  INICIO
                </span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function SeleccionarSpoolPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-[#001F3F] flex items-center justify-center">
        <Loader2 size={64} className="text-zeues-orange animate-spin" strokeWidth={3} />
      </div>
    }>
      <SeleccionarSpoolContent />
    </Suspense>
  );
}
