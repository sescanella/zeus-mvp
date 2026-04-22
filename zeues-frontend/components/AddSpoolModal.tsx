'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Search, X } from 'lucide-react';
import { Modal } from '@/components/Modal';
import { SpoolTable } from '@/components/SpoolTable';
import { getSpoolsParaIniciar } from '@/lib/api';
import { classifyApiError } from '@/lib/error-classifier';
import type { Spool } from '@/lib/types';

interface AddSpoolModalProps {
  isOpen: boolean;
  /** Callback when the user adds a single spool (non-batch mode). */
  onAdd: (tag: string) => void;
  /**
   * Callback when the user confirms a batch selection to assign an armador to.
   * Called with the list of TAGs; the parent is responsible for opening the
   * worker picker and dispatching INICIAR per spool.
   * v5.1 UX-2 (batch ingreso Escenario A).
   */
  onBatchAdd?: (tags: string[]) => void;
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
 * Two modes:
 *  - Default "add-only": each tap on a row adds the spool to the tracked
 *    list immediately. Modal stays open for adding more. Operator then
 *    opens each card individually to start work (legacy flow).
 *  - Batch mode (v5.1 UX-2): operator toggles "ASIGNAR ARMADOR AHORA" and
 *    the table switches to multi-select. A confirm button at the bottom
 *    fires `onBatchAdd(tags)` with every selected TAG so the parent can
 *    pick an armador once and INICIAR all of them with that worker.
 *
 * If `onBatchAdd` is not provided, the batch toggle is hidden (backward
 * compatible with any future caller that wants add-only).
 */
export function AddSpoolModal({
  isOpen,
  onAdd,
  onBatchAdd,
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

  // Multi-add session state (add-only mode)
  const [addedThisSession, setAddedThisSession] = useState<string[]>([]);

  // Batch-mode state (v5.1 UX-2)
  const batchEnabled = Boolean(onBatchAdd);
  const [batchMode, setBatchMode] = useState(false);
  const [batchSelected, setBatchSelected] = useState<string[]>([]);

  const nvInputRef = useRef<HTMLInputElement>(null);

  const fetchSpools = useCallback(async () => {
    setFetchState('loading');
    setErrorMessage('');
    try {
      const data = await getSpoolsParaIniciar('ARM');
      setSpools(data);
      setFetchState('success');
    } catch (err) {
      setErrorMessage(classifyApiError(err).userMessage);
      setFetchState('error');
    }
  }, []);

  // Fetch when modal opens, reset session counter and filters
  useEffect(() => {
    if (isOpen) {
      setAddedThisSession([]);
      setBatchMode(false);
      setBatchSelected([]);
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

  // Toggling out of batch mode discards any pending multi-selection so
  // the row-tap contract (add-only) is never ambiguous.
  function handleToggleBatchMode() {
    setBatchMode((prev) => {
      const next = !prev;
      if (!next) setBatchSelected([]);
      return next;
    });
  }

  // Require at least 2 characters in either field before showing results.
  // This prevents rendering 2,000+ rows on low-end tablets when the list is unfiltered.
  const hasMinInput = searchTag.trim().length >= 2 || searchNV.trim().length >= 2;
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
    if (batchMode) {
      setBatchSelected((prev) =>
        prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
      );
      return;
    }
    setAddedThisSession((prev) => [...prev, tag]);
    onAdd(tag);
  };

  function handleConfirmBatch() {
    if (!onBatchAdd || batchSelected.length === 0) return;
    onBatchAdd(batchSelected);
    // Parent owns the flow from here. Close the modal so the worker picker
    // isn't stacked underneath.
    onClose();
  }

  // Combine alreadyTracked with spools added this session for disabling
  const allDisabled = [...new Set([...alreadyTracked, ...addedThisSession])];

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      ariaLabel="Añadir spool"
      isTopOfStack={isTopOfStack}
      className="bg-zeues-navy border-4 border-white max-w-2xl !p-4"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-xl font-black text-white font-mono tracking-widest">AÑADIR SPOOL</h2>
        <button
          onClick={onClose}
          aria-label="Cerrar modal"
          className="min-w-[44px] min-h-[44px] flex items-center justify-center text-white/70 hover:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset"
        >
          <X size={24} strokeWidth={3} />
        </button>
      </div>

      {fetchState === 'loading' && (
        <div className="py-8 text-center" role="status" aria-label="Cargando">
          <p className="text-white/70 font-mono font-black tracking-widest" aria-hidden="true">CARGANDO...</p>
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
            className="px-6 py-3 border-2 border-white text-white font-mono font-black text-sm cursor-pointer active:bg-white active:text-zeues-navy transition-colors focus:outline-none focus:ring-2 focus:ring-zeues-orange focus:ring-inset"
          >
            REINTENTAR
          </button>
        </div>
      )}

      {fetchState === 'success' && (
        <>
          {/* Batch-mode toggle (v5.1 UX-2). Rendered only when the parent
              wired the batch callback. Defaults OFF — legacy add-one-at-a-time
              behavior is preserved. */}
          {batchEnabled && (
            <div className="mb-3">
              <button
                type="button"
                onClick={handleToggleBatchMode}
                role="switch"
                aria-checked={batchMode}
                className={`w-full h-12 px-4 font-mono font-black text-sm tracking-widest border-2 cursor-pointer transition-colors focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset flex items-center justify-between ${
                  batchMode
                    ? 'bg-zeues-orange/10 border-zeues-orange text-zeues-orange'
                    : 'border-white/30 text-white/70 hover:border-white/50'
                }`}
              >
                <span>ASIGNAR ARMADOR AHORA</span>
                <span
                  className={`inline-flex items-center justify-center w-10 h-6 border-2 rounded-full ${
                    batchMode ? 'bg-zeues-orange border-zeues-orange' : 'border-white/40'
                  }`}
                  aria-hidden="true"
                >
                  <span
                    className={`w-4 h-4 rounded-full bg-white transition-transform ${
                      batchMode ? 'translate-x-2' : '-translate-x-2'
                    }`}
                  />
                </span>
              </button>
              {batchMode && (
                <p className="mt-1 text-xs font-mono text-white/60">
                  Selecciona varios spools y asigna un armador en un solo paso.
                </p>
              )}
            </div>
          )}

          {/* Session counter (add-only mode) */}
          {!batchMode && addedThisSession.length > 0 && (
            <div className="mb-3 px-3 py-2 bg-green-900/30 border-2 border-green-400/40 font-mono text-sm text-green-400 font-black">
              {addedThisSession.length} spool{addedThisSession.length > 1 ? 's' : ''} agregado{addedThisSession.length > 1 ? 's' : ''}
            </div>
          )}

          {/* Batch selection counter */}
          {batchMode && batchSelected.length > 0 && (
            <div className="mb-3 px-3 py-2 bg-zeues-orange/10 border-2 border-zeues-orange/50 font-mono text-sm text-zeues-orange font-black">
              {batchSelected.length} spool{batchSelected.length > 1 ? 's' : ''} seleccionado{batchSelected.length > 1 ? 's' : ''}
            </div>
          )}

          {/* Inline search fields — always visible */}
          <div className="grid grid-cols-2 gap-3 mb-3">
            <div>
              <label htmlFor="add-filter-nv" className="block text-xs font-black text-white/70 font-mono mb-1">
                NV
              </label>
              <div className="relative">
                <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40" aria-hidden="true" />
                <input
                  ref={nvInputRef}
                  id="add-filter-nv"
                  type="text"
                  value={searchNV}
                  onChange={(e) => setSearchNV(e.target.value)}
                  placeholder="Ej: NV0642"
                  aria-label="Buscar por número de nota de venta"
                  className="w-full h-12 pl-10 pr-4 bg-transparent border-2 border-white text-white font-mono font-black placeholder:text-white/40 focus:outline-none focus:border-zeues-orange"
                />
              </div>
            </div>
            <div>
              <label htmlFor="add-filter-tag" className="block text-xs font-black text-white/70 font-mono mb-1">
                TAG SPOOL
              </label>
              <div className="relative">
                <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40" aria-hidden="true" />
                <input
                  id="add-filter-tag"
                  type="text"
                  value={searchTag}
                  onChange={(e) => setSearchTag(e.target.value)}
                  placeholder="Ej: MK-1923"
                  aria-label="Buscar por TAG de spool"
                  className="w-full h-12 pl-10 pr-4 bg-transparent border-2 border-white text-white font-mono font-black placeholder:text-white/40 focus:outline-none focus:border-zeues-orange"
                />
              </div>
            </div>
          </div>

          {/* Result count + clear filters */}
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-black text-white/70 font-mono">
              {hasMinInput
                ? `${filteredSpools.length} RESULTADO${filteredSpools.length !== 1 ? 'S' : ''}`
                : `${spools.length} SPOOLS DISPONIBLES`}
            </span>
            {hasFilter && (
              <button
                onClick={handleClearFilters}
                className="text-xs font-black text-yellow-500 font-mono px-3 py-2 min-h-[44px] border border-yellow-500 active:bg-yellow-500 active:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-yellow-500 focus:ring-inset cursor-pointer"
                aria-label="Limpiar filtros de búsqueda"
              >
                LIMPIAR
              </button>
            )}
          </div>

          {/* Spool table — only rendered once the worker has typed 2+ characters */}
          {!hasMinInput ? (
            <div className="border-4 border-white/30 py-8 text-center" role="status" aria-live="polite">
              <p className="text-white/70 font-mono font-black text-sm">
                INGRESA NV O TAG PARA BUSCAR
              </p>
            </div>
          ) : filteredSpools.length > 0 ? (
            <SpoolTable
              spools={filteredSpools}
              selectedSpools={batchMode ? batchSelected : []}
              onToggleSelect={handleRowClick}
              tipo={null}
              disabledSpools={allDisabled}
              maxHeight="max-h-[50vh]"
            />
          ) : (
            <div className="border-4 border-white/30 py-8 text-center">
              <p className="text-white/70 font-mono font-black text-sm">
                SIN RESULTADOS
              </p>
            </div>
          )}

          {/* Primary action — its label depends on the mode. */}
          {batchMode ? (
            <button
              type="button"
              onClick={handleConfirmBatch}
              disabled={batchSelected.length === 0}
              className="w-full h-14 mt-3 bg-zeues-orange text-white font-mono font-black text-lg tracking-widest focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
              aria-label={
                batchSelected.length === 0
                  ? 'Selecciona al menos un spool para asignar armador'
                  : `Asignar armador a ${batchSelected.length} spools`
              }
            >
              {batchSelected.length === 0
                ? 'SELECCIONA SPOOLS'
                : `ASIGNAR ARMADOR (${batchSelected.length})`}
            </button>
          ) : (
            <button
              type="button"
              onClick={onClose}
              className="w-full h-14 mt-3 bg-zeues-orange text-white font-mono font-black text-lg tracking-widest focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset cursor-pointer"
              aria-label="Cerrar modal de agregar spools"
            >
              LISTO
            </button>
          )}
        </>
      )}
    </Modal>
  );
}
