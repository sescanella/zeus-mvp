'use client';

import { Search, ChevronDown, ChevronUp } from 'lucide-react';

interface SpoolFilterPanelProps {
  isExpanded: boolean;
  onToggleExpand: () => void;
  searchNV: string;
  onSearchNVChange: (value: string) => void;
  searchTag: string;
  onSearchTagChange: (value: string) => void;
  selectedCount: number;
  filteredCount: number;
  activeFiltersCount: number;
  onSelectAll: () => void;
  onDeselectAll: () => void;
  onClearFilters: () => void;
}

export function SpoolFilterPanel({
  isExpanded,
  onToggleExpand,
  searchNV,
  onSearchNVChange,
  searchTag,
  onSearchTagChange,
  selectedCount,
  filteredCount,
  activeFiltersCount,
  onSelectAll,
  onDeselectAll,
  onClearFilters,
}: SpoolFilterPanelProps) {
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onToggleExpand();
    }
  };

  return (
    <div className="border-4 border-white overflow-hidden transition-all duration-300 ease-in-out mb-4">
      {/* COMPACT VIEW (60px height - default) */}
      {!isExpanded && (
        <button
          onClick={onToggleExpand}
          onKeyDown={handleKeyDown}
          aria-expanded={false}
          aria-controls="filter-panel"
          aria-label="Mostrar filtros de busqueda"
          className="w-full p-4 cursor-pointer hover:bg-white/5 transition-colors focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset"
        >
          <div className="flex items-center justify-between">
            {/* Left: Selection counter */}
            <span className="text-sm font-black text-white/70 font-mono">
              SELECCIONADOS: {selectedCount} / {filteredCount}
            </span>

            {/* Center: Active filters indicator */}
            {activeFiltersCount > 0 && (
              <span className="text-xs font-black text-zeues-orange font-mono px-3 py-1 border border-zeues-orange">
                {activeFiltersCount} FILTRO{activeFiltersCount !== 1 ? 'S' : ''}
              </span>
            )}

            {/* Right: Expand icon */}
            <ChevronDown size={24} className="text-white" strokeWidth={3} />
          </div>
        </button>
      )}

      {/* EXPANDED VIEW (full filters + controls) */}
      {isExpanded && (
        <div id="filter-panel" className="p-6 tablet:p-4 narrow:p-4" role="region" aria-label="Panel de filtros">
          {/* Header with collapse button */}
          <button
            onClick={onToggleExpand}
            onKeyDown={handleKeyDown}
            aria-expanded={true}
            aria-controls="filter-panel"
            aria-label="Ocultar filtros de busqueda"
            className="w-full flex items-center justify-between mb-4 cursor-pointer hover:bg-white/5 transition-colors p-2 -m-2 focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset"
          >
            <span className="text-xs font-black text-white/50 font-mono">FILTROS DE BUSQUEDA</span>
            <ChevronUp size={24} className="text-white" strokeWidth={3} />
          </button>

          {/* Search inputs grid */}
          <div className="grid grid-cols-2 narrow:grid-cols-1 gap-4 tablet:gap-3 mb-4 tablet:mb-3">
            <div>
              <label htmlFor="filter-nv" className="block text-xs font-black text-white/50 font-mono mb-2">
                BUSCAR NV
              </label>
              <div className="relative">
                <Search size={20} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/50" aria-hidden="true" />
                <input
                  id="filter-nv"
                  type="text"
                  value={searchNV}
                  onChange={(e) => onSearchNVChange(e.target.value)}
                  placeholder="NV-2024-..."
                  aria-label="Buscar por numero de nota de venta"
                  className="w-full h-12 pl-12 narrow:pl-10 pr-4 bg-transparent border-2 border-white text-white font-mono placeholder:text-white/30 focus:outline-none focus:border-zeues-orange"
                />
              </div>
            </div>
            <div>
              <label htmlFor="filter-tag" className="block text-xs font-black text-white/50 font-mono mb-2">
                BUSCAR TAG
              </label>
              <div className="relative">
                <Search size={20} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/50" aria-hidden="true" />
                <input
                  id="filter-tag"
                  type="text"
                  value={searchTag}
                  onChange={(e) => onSearchTagChange(e.target.value)}
                  placeholder="Buscar TAG..."
                  aria-label="Buscar por TAG de spool"
                  className="w-full h-12 pl-12 narrow:pl-10 pr-4 bg-transparent border-2 border-white text-white font-mono placeholder:text-white/30 focus:outline-none focus:border-zeues-orange"
                />
              </div>
            </div>
          </div>

          {/* Controls row */}
          <div className="flex items-center justify-between flex-wrap gap-3">
            <span className="text-sm font-black text-white/70 font-mono">
              SELECCIONADOS: {selectedCount} / {filteredCount} FILTRADOS
            </span>
            <div className="flex gap-2 flex-wrap">
              <button
                onClick={onSelectAll}
                className="px-4 py-2 border-2 border-white text-white font-mono text-xs font-black active:bg-white active:text-[#001F3F] transition-colors"
                aria-label="Seleccionar todos los spools filtrados"
              >
                TODOS
              </button>
              <button
                onClick={onDeselectAll}
                disabled={selectedCount === 0}
                className="px-4 py-2 border-2 border-red-500 text-red-500 font-mono text-xs font-black active:bg-red-500 active:text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                aria-label="Deseleccionar todos los spools"
              >
                NINGUNO
              </button>
              {activeFiltersCount > 0 && (
                <button
                  onClick={onClearFilters}
                  className="px-4 py-2 border-2 border-yellow-500 text-yellow-500 font-mono text-xs font-black active:bg-yellow-500 active:text-white transition-colors"
                  aria-label="Limpiar todos los filtros de busqueda"
                >
                  LIMPIAR FILTROS
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
