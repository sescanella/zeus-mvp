'use client';

import { Suspense, useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Image from 'next/image';
import { Puzzle, Flame, SearchCheck, Search, CheckSquare, Square, ArrowLeft, X, Loader2, AlertCircle } from 'lucide-react';
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
  const [spools, setSpools] = useState<Spool[]>([]);

  // Local filter states
  const [searchNV, setSearchNV] = useState('');
  const [searchTag, setSearchTag] = useState('');

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
        setLoading(false);
        return;
      }

      let fetchedSpools: Spool[];

      if (tipo === 'iniciar') {
        fetchedSpools = await getSpoolsParaIniciar(selectedOperation as 'ARM' | 'SOLD');
      } else if (tipo === 'completar') {
        if (!selectedWorker) {
          setError('No se ha seleccionado un trabajador');
          setLoading(false);
          return;
        }
        fetchedSpools = await getSpoolsParaCompletar(selectedOperation as 'ARM' | 'SOLD', selectedWorker.nombre_completo);
      } else {
        if (!selectedWorker) {
          setError('No se ha seleccionado un trabajador');
          setLoading(false);
          return;
        }
        fetchedSpools = await getSpoolsParaCancelar(selectedOperation as 'ARM' | 'SOLD', selectedWorker.id);
      }

      setSpools(fetchedSpools);
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
  };

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

  // v2.0: Navigate with selections (auto-detect single vs batch)
  const handleContinueWithBatch = () => {
    const selectedCount = (state.selectedSpools || []).length;

    if (selectedCount === 0) return;

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

  const actionLabel = tipo === 'iniciar' ? 'INICIAR' : tipo === 'completar' ? 'COMPLETAR' : 'CANCELAR';
  const operationLabel = state.selectedOperation === 'ARM' ? 'ARMADO' :
                        state.selectedOperation === 'SOLD' ? 'SOLDADURA' : 'METROLOGÍA';

  const OperationIcon = state.selectedOperation === 'ARM' ? Puzzle :
                        state.selectedOperation === 'SOLD' ? Flame : SearchCheck;

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
            {operationLabel} - {actionLabel}
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

        {/* Main Content - VAR-1 Table */}
        {!loading && !error && (
          <>
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
                    SELECCIONADOS: {selectedCount} / {spoolsFiltrados.length} FILTRADOS (v2.1.3)
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
                <table className="w-full">
                  <thead className="sticky top-0 bg-[#001F3F] border-b-4 border-white">
                    <tr>
                      <th className="p-3 text-left text-xs font-black text-white/70 font-mono border-r-2 border-white/30">SEL</th>
                      <th className="p-3 text-left text-xs font-black text-white/70 font-mono border-r-2 border-white/30">TAG SPOOL</th>
                      <th className="p-3 text-left text-xs font-black text-white/70 font-mono">NV</th>
                    </tr>
                  </thead>
                  <tbody>
                    {/* Render only filtered spools (v2.1.3 - debug render) */}
                    {spoolsFiltrados.map((spool, index) => {
                      console.log(`[RENDER v2.1.3] Row ${index}:`, spool.tag_spool);
                      const isSelected = (state.selectedSpools || []).includes(spool.tag_spool);
                      return (
                        <tr
                          key={spool.tag_spool}
                          onClick={() => toggleSelect(spool.tag_spool)}
                          className={`border-t-2 border-white/30 cursor-pointer transition-colors ${
                            isSelected ? 'bg-zeues-orange/20' : 'hover:bg-white/5'
                          }`}
                        >
                          <td className="p-3 border-r-2 border-white/30">
                            {isSelected ? (
                              <CheckSquare size={24} className="text-zeues-orange" strokeWidth={3} />
                            ) : (
                              <Square size={24} className="text-white/50" strokeWidth={3} />
                            )}
                          </td>
                          <td className="p-3 border-r-2 border-white/30">
                            <span className="text-lg font-black text-white font-mono">{spool.tag_spool}</span>
                          </td>
                          <td className="p-3">
                            <span className="text-sm font-black text-white/70 font-mono">{spool.nv}</span>
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

      {/* Fixed Navigation Footer with Continuar Button */}
      {!loading && !error && (
        <div className="fixed bottom-0 left-0 right-0 bg-[#001F3F] z-50 border-t-4 border-white/30 p-6 tablet:p-5">
          <div className="flex flex-col gap-4 tablet:gap-3">
            {/* Botón Continuar - Primera fila */}
            <button
              onClick={handleContinueWithBatch}
              disabled={selectedCount === 0}
              className="w-full h-16 tablet:h-14 bg-transparent border-4 border-white flex items-center justify-center gap-4 cursor-pointer active:bg-zeues-orange active:border-zeues-orange transition-all disabled:opacity-30 disabled:cursor-not-allowed group"
            >
              <span className="text-xl tablet:text-lg narrow:text-lg font-black text-white font-mono tracking-[0.2em] group-active:text-white">
                CONTINUAR CON {selectedCount} SPOOL{selectedCount !== 1 ? 'S' : ''}
              </span>
            </button>

            {/* Botones Volver/Inicio - Segunda fila */}
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
