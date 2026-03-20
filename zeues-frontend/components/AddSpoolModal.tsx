'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Search, X } from 'lucide-react';
import { Modal } from '@/components/Modal';
import { SpoolTable } from '@/components/SpoolTable';
import { getSpoolsParaIniciar } from '@/lib/api';
import type { Spool } from '@/lib/types';

interface AddSpoolModalProps {
  isOpen: boolean;
  onAdd: (tag: string) => void;
  onClose: () => void;
  alreadyTracked: string[];
  isTopOfStack?: boolean;
}

type FetchState = 'loading' | 'success' | 'error';

/** Score spool relevance: exact=3, prefix=2, contains=1, no match=0 */
function relevanceScore(spool: Spool, searchTag: string, searchNV: string): number {
  let score = 0;
  if (searchTag) {
    const tag = spool.tag_spool.toLowerCase();
    const q = searchTag.toLowerCase();
    if (tag === q) score += 3;
    else if (tag.startsWith(q)) score += 2;
    else if (tag.includes(q)) score += 1;
  }
  if (searchNV) {
    const nv = (spool.nv || '').toLowerCase();
    const q = searchNV.toLowerCase();
    if (nv === q) score += 3;
    else if (nv.startsWith(q)) score += 2;
    else if (nv.includes(q)) score += 1;
  }
  return score;
}

/**
 * AddSpoolModal — Modal for adding spools to the tracked card list.
 *
 * Inline search fields (NV + TAG) always visible at top.
 * Renders SpoolTable with alreadyTracked tags greyed out (disabledSpools).
 *
 * Multi-add: after adding a spool, the modal stays open for adding more.
 * Shows a counter of spools added in this session.
 * User closes the modal manually via the LISTO button when done.
 */
export function AddSpoolModal({
  isOpen,
  onAdd,
  onClose,
  alreadyTracked,
  isTopOfStack,
}: AddSpoolModalProps) {
  const [spools, setSpools] = useState<Spool[]>([]);
  const [fetchState, setFetchState] = useState<FetchState>('loading');
  const [errorMessage, setErrorMessage] = useState<string>('');

  // Filter state
  const [searchNV, setSearchNV] = useState('');
  const [searchTag, setSearchTag] = useState('');

  // Multi-add session state
  const [addedThisSession, setAddedThisSession] = useState<string[]>([]);

  const nvInputRef = useRef<HTMLInputElement>(null);

  const fetchSpools = useCallback(async () => {
    setFetchState('loading');
    setErrorMessage('');
    try {
      const data = await getSpoolsParaIniciar('ARM');
      setSpools(data);
      setFetchState('success');
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Error al cargar spools.';
      setErrorMessage(msg);
      setFetchState('error');
    }
  }, []);

  // Fetch when modal opens, reset session counter and filters
  useEffect(() => {
    if (isOpen) {
      setAddedThisSession([]);
      setSearchNV('');
      setSearchTag('');
      fetchSpools();
      // Auto-focus NV input after mount
      const timer = setTimeout(() => {
        nvInputRef.current?.focus();
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [isOpen, fetchSpools]);

  // Apply filters to spool list and sort by relevance (prefix > contains)
  const hasFilter = searchTag || searchNV;
  const filteredSpools = spools
    .filter((s) => {
      const tagMatch = !searchTag || s.tag_spool.toLowerCase().includes(searchTag.toLowerCase());
      const nvMatch = !searchNV || (s.nv || '').toLowerCase().includes(searchNV.toLowerCase());
      return tagMatch && nvMatch;
    })
    .sort((a, b) => {
      if (!hasFilter) return 0;
      const scoreA = relevanceScore(a, searchTag, searchNV);
      const scoreB = relevanceScore(b, searchTag, searchNV);
      return scoreB - scoreA;
    });

  const handleClearFilters = () => {
    setSearchNV('');
    setSearchTag('');
    nvInputRef.current?.focus();
  };

  const handleRowClick = (tag: string) => {
    setAddedThisSession((prev) => [...prev, tag]);
    onAdd(tag);
  };

  // Combine alreadyTracked with spools added this session for disabling
  const allDisabled = [...new Set([...alreadyTracked, ...addedThisSession])];

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      ariaLabel="Anadir spool"
      isTopOfStack={isTopOfStack}
      className="bg-zeues-navy border-4 border-white rounded-none max-w-lg !p-4"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-xl font-black text-white font-mono tracking-widest">ANADIR SPOOL</h2>
        <button
          onClick={onClose}
          aria-label="Cerrar modal"
          className="p-1 text-white/50 hover:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset"
        >
          <X size={24} strokeWidth={3} />
        </button>
      </div>

      {fetchState === 'loading' && (
        <div className="py-8 text-center">
          <p className="text-white/70 font-mono font-black tracking-widest">CARGANDO...</p>
        </div>
      )}

      {fetchState === 'error' && (
        <div className="py-8 text-center space-y-4">
          <p className="text-red-400 font-mono font-black">
            Error al cargar spools: {errorMessage}
          </p>
          <button
            onClick={fetchSpools}
            aria-label="Reintentar cargar spools"
            className="px-6 py-3 border-2 border-white text-white font-mono font-black text-sm active:bg-white active:text-zeues-navy transition-colors focus:outline-none focus:ring-2 focus:ring-zeues-orange focus:ring-inset"
          >
            REINTENTAR
          </button>
        </div>
      )}

      {fetchState === 'success' && (
        <>
          {/* Session counter */}
          {addedThisSession.length > 0 && (
            <div className="mb-3 px-3 py-2 bg-green-900/30 border-2 border-green-400/40 font-mono text-sm text-green-400 font-black">
              {addedThisSession.length} spool{addedThisSession.length > 1 ? 's' : ''} agregado{addedThisSession.length > 1 ? 's' : ''}
            </div>
          )}

          {/* Inline search fields — always visible */}
          <div className="grid grid-cols-2 gap-3 mb-3">
            <div>
              <label htmlFor="add-filter-nv" className="block text-xs font-black text-white/50 font-mono mb-1">
                NV
              </label>
              <div className="relative">
                <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40" aria-hidden="true" />
                <input
                  ref={nvInputRef}
                  id="add-filter-nv"
                  type="text"
                  inputMode="numeric"
                  value={searchNV}
                  onChange={(e) => setSearchNV(e.target.value)}
                  placeholder="Ej: 123"
                  aria-label="Buscar por numero de nota de venta"
                  className="w-full h-12 pl-10 pr-4 bg-transparent border-2 border-white text-white font-mono font-black placeholder:text-white/30 focus:outline-none focus:border-zeues-orange"
                />
              </div>
            </div>
            <div>
              <label htmlFor="add-filter-tag" className="block text-xs font-black text-white/50 font-mono mb-1">
                TAG SPOOL
              </label>
              <div className="relative">
                <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40" aria-hidden="true" />
                <input
                  id="add-filter-tag"
                  type="text"
                  inputMode="numeric"
                  value={searchTag}
                  onChange={(e) => setSearchTag(e.target.value)}
                  placeholder="Ej: 1234"
                  aria-label="Buscar por TAG de spool"
                  className="w-full h-12 pl-10 pr-4 bg-transparent border-2 border-white text-white font-mono font-black placeholder:text-white/30 focus:outline-none focus:border-zeues-orange"
                />
              </div>
            </div>
          </div>

          {/* Result count + clear filters */}
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-black text-white/50 font-mono">
              {hasFilter ? `${filteredSpools.length} RESULTADO${filteredSpools.length !== 1 ? 'S' : ''}` : `${spools.length} SPOOLS`}
            </span>
            {hasFilter && (
              <button
                onClick={handleClearFilters}
                className="text-xs font-black text-yellow-500 font-mono px-2 py-1 border border-yellow-500 active:bg-yellow-500 active:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-yellow-500 focus:ring-inset cursor-pointer"
                aria-label="Limpiar filtros de busqueda"
              >
                LIMPIAR
              </button>
            )}
          </div>

          {/* Spool table — taller to show more results */}
          {filteredSpools.length > 0 ? (
            <SpoolTable
              spools={filteredSpools}
              selectedSpools={[]}
              onToggleSelect={handleRowClick}
              tipo={null}
              disabledSpools={allDisabled}
              maxHeight="max-h-[50vh]"
            />
          ) : (
            <div className="border-4 border-white/30 py-8 text-center">
              <p className="text-white/50 font-mono font-black text-sm">
                {hasFilter ? 'SIN RESULTADOS' : 'NO HAY SPOOLS DISPONIBLES'}
              </p>
            </div>
          )}

          {/* LISTO button */}
          <button
            onClick={onClose}
            className="w-full h-14 mt-3 bg-zeues-orange text-white font-mono font-black text-lg tracking-widest focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset cursor-pointer"
            aria-label="Cerrar modal de agregar spools"
          >
            LISTO
          </button>
        </>
      )}
    </Modal>
  );
}
