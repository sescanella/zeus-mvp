'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Modal } from '@/components/Modal';
import { SpoolTable } from '@/components/SpoolTable';
import { SpoolFilterPanel } from '@/components/SpoolFilterPanel';
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
 * Fetches all available spools via getSpoolsParaIniciar('ARM').
 * Renders SpoolFilterPanel (showSelectionControls=false) + SpoolTable
 * with alreadyTracked tags greyed out (disabledSpools).
 * Clicking a non-disabled row fires onAdd(tag).
 *
 * Plan: 03-01-PLAN.md Task 1
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
  const [isFilterOpen, setIsFilterOpen] = useState(false);
  const [searchNV, setSearchNV] = useState('');
  const [searchTag, setSearchTag] = useState('');

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

  // Fetch when modal opens
  useEffect(() => {
    if (isOpen) {
      fetchSpools();
    }
  }, [isOpen, fetchSpools]);

  // Apply filters to spool list and sort by relevance (prefix > contains)
  const filteredSpools = spools
    .filter((s) => {
      const tagMatch = !searchTag || s.tag_spool.toLowerCase().includes(searchTag.toLowerCase());
      const nvMatch = !searchNV || (s.nv || '').toLowerCase().includes(searchNV.toLowerCase());
      return tagMatch && nvMatch;
    })
    .sort((a, b) => {
      if (!searchTag && !searchNV) return 0;
      const scoreA = relevanceScore(a, searchTag, searchNV);
      const scoreB = relevanceScore(b, searchTag, searchNV);
      return scoreB - scoreA;
    });

  const activeFiltersCount = (searchNV ? 1 : 0) + (searchTag ? 1 : 0);

  const handleClearFilters = () => {
    setSearchNV('');
    setSearchTag('');
  };

  const handleRowClick = (tag: string) => {
    onAdd(tag);
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      ariaLabel="Anadir spool"
      isTopOfStack={isTopOfStack}
      className="bg-zeues-navy border-4 border-white rounded-none max-w-lg"
    >
      {/* Header */}
      <div className="mb-4">
        <h2 className="text-xl font-black text-white font-mono tracking-widest">ANADIR SPOOL</h2>
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
          <SpoolFilterPanel
            isOpen={isFilterOpen}
            onOpen={() => setIsFilterOpen(true)}
            onClose={() => setIsFilterOpen(false)}
            searchNV={searchNV}
            onSearchNVChange={setSearchNV}
            searchTag={searchTag}
            onSearchTagChange={setSearchTag}
            selectedCount={0}
            filteredCount={filteredSpools.length}
            activeFiltersCount={activeFiltersCount}
            onSelectAll={() => {}}
            onDeselectAll={() => {}}
            onClearFilters={handleClearFilters}
            showSelectionControls={false}
          />

          <SpoolTable
            spools={filteredSpools}
            selectedSpools={[]}
            onToggleSelect={handleRowClick}
            tipo={null}
            disabledSpools={alreadyTracked}
          />
        </>
      )}
    </Modal>
  );
}
