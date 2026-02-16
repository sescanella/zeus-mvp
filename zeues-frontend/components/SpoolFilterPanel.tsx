'use client';

import { useRef, useEffect } from 'react';
import { Search, ChevronDown, X } from 'lucide-react';
import { Modal } from '@/components/Modal';

interface SpoolFilterPanelProps {
  isOpen: boolean;
  onOpen: () => void;
  onClose: () => void;
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
  isOpen,
  onOpen,
  onClose,
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
  const triggerRef = useRef<HTMLButtonElement>(null);
  const nvInputRef = useRef<HTMLInputElement>(null);

  // Auto-focus NV input when modal opens
  useEffect(() => {
    if (isOpen) {
      // Small delay to allow portal to mount
      const timer = setTimeout(() => {
        nvInputRef.current?.focus();
      }, 50);
      return () => clearTimeout(timer);
    }
  }, [isOpen]);

  // Return focus to trigger when modal closes
  const handleClose = () => {
    onClose();
    // Small delay to allow modal to unmount
    setTimeout(() => {
      triggerRef.current?.focus();
    }, 50);
  };

  return (
    <>
      {/* Trigger bar (always visible) */}
      <div className="border-4 border-white mb-4">
        <button
          ref={triggerRef}
          onClick={onOpen}
          aria-haspopup="dialog"
          aria-label="Abrir filtros de busqueda"
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

            {/* Right: Open icon */}
            <ChevronDown size={24} className="text-white" strokeWidth={3} />
          </div>
        </button>
      </div>

      {/* Filter modal */}
      <Modal
        isOpen={isOpen}
        onClose={handleClose}
        ariaLabel="Filtros de busqueda"
        className="bg-[#001F3F] border-4 border-white rounded-none max-w-lg"
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <span className="text-xs font-black text-white/50 font-mono">FILTROS DE BUSQUEDA</span>
          <button
            onClick={handleClose}
            aria-label="Cerrar filtros de busqueda"
            className="p-1 text-white/50 hover:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset"
          >
            <X size={24} strokeWidth={3} />
          </button>
        </div>

        {/* Search inputs grid */}
        <div className="grid grid-cols-2 narrow:grid-cols-1 gap-4 tablet:gap-3 mb-4 tablet:mb-3">
          <div>
            <label htmlFor="filter-nv" className="block text-xs font-black text-white/50 font-mono mb-2">
              BUSCAR NV
            </label>
            <div className="relative">
              <Search size={20} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/50" aria-hidden="true" />
              <input
                ref={nvInputRef}
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
      </Modal>
    </>
  );
}
