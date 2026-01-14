'use client';

import { useState, useMemo } from 'react';
import { Spool } from '@/lib/types';
import { SpoolSearch } from './SpoolSearch';
import { SpoolTable } from './SpoolTable';

interface SpoolSelectorProps {
  spools: Spool[];
  selectedTags: string[];
  onSelectChange: (tags: string[]) => void;
  maxSelection?: number;
  className?: string;
}

/**
 * Filter interface para sistema multidimensional escalable
 */
interface Filter {
  field: keyof Spool;
  value: string;
}

/**
 * SpoolSelector component - Orquestador principal (v2.0)
 *
 * Responsabilidades:
 * - Gestionar estado de filtros
 * - Computar spools filtrados (useMemo)
 * - Lógica de selección (toggle, select all, deselect all)
 * - Componer SpoolSearch + SpoolTable
 *
 * Features:
 * - Sistema filters[] genérico (escalable para más dimensiones)
 * - Multiselect hasta 50 spools (default)
 * - Filtros AND (NV + TAG_SPOOL)
 * - Select/Deselect All sobre spools visibles
 *
 * @example
 * <SpoolSelector
 *   spools={availableSpools}
 *   selectedTags={state.selectedSpools}
 *   onSelectChange={(tags) => setState({ selectedSpools: tags })}
 *   maxSelection={50}
 * />
 */
export function SpoolSelector({
  spools,
  selectedTags,
  onSelectChange,
  maxSelection = 50,
  className = '',
}: SpoolSelectorProps) {
  // Sistema de filtros genérico escalable
  const [filters, setFilters] = useState<Filter[]>([
    { field: 'nv', value: '' },
    { field: 'tag_spool', value: '' },
  ]);

  /**
   * Aplicar filtros multidimensionales (lógica AND)
   * Filtros vacíos son ignorados automáticamente
   */
  const filteredSpools = useMemo(() => {
    // Si todos los filtros están vacíos, retornar todo
    const activeFilters = filters.filter(f => f.value.trim() !== '');
    if (activeFilters.length === 0) return spools;

    return spools.filter(spool => {
      // Lógica AND: TODOS los filtros activos deben coincidir
      return activeFilters.every(filter => {
        const fieldValue = spool[filter.field];
        if (fieldValue === undefined || fieldValue === null) return false;

        // Búsqueda case-insensitive con includes
        return String(fieldValue)
          .toLowerCase()
          .includes(filter.value.toLowerCase());
      });
    });
  }, [spools, filters]);

  const isMaxReached = selectedTags.length >= maxSelection;
  const hasActiveFilters = filters.some(f => f.value.trim() !== '');

  /**
   * Actualizar un filtro específico
   */
  const updateFilter = (field: string, value: string) => {
    setFilters(prev =>
      prev.map(f => (f.field === field ? { ...f, value } : f))
    );
  };

  /**
   * Limpiar todos los filtros
   */
  const clearFilters = () => {
    setFilters(prev => prev.map(f => ({ ...f, value: '' })));
  };

  /**
   * Toggle individual spool (click en fila)
   */
  const handleToggle = (tag: string) => {
    const isSelected = selectedTags.includes(tag);

    if (isSelected) {
      // Deseleccionar
      onSelectChange(selectedTags.filter(t => t !== tag));
    } else {
      // Seleccionar si no alcanzamos el límite
      if (!isMaxReached) {
        onSelectChange([...selectedTags, tag]);
      }
    }
  };

  /**
   * Seleccionar todos los spools VISIBLES/FILTRADOS (hasta el límite)
   */
  const handleSelectAll = () => {
    const tagsToAdd = filteredSpools
      .map(s => s.tag_spool)
      .filter(tag => !selectedTags.includes(tag));

    const remainingSlots = maxSelection - selectedTags.length;
    const newTags = tagsToAdd.slice(0, remainingSlots);

    onSelectChange([...selectedTags, ...newTags]);
  };

  /**
   * Deseleccionar todos los spools VISIBLES/FILTRADOS
   */
  const handleDeselectAll = () => {
    const filteredTagSet = new Set(filteredSpools.map(s => s.tag_spool));
    onSelectChange(selectedTags.filter(tag => !filteredTagSet.has(tag)));
  };

  const selectedCount = selectedTags.length;
  const totalCount = spools.length;
  const filteredCount = filteredSpools.length;

  return (
    <div className={`flex flex-col gap-4 ${className}`}>
      {/* Componente de búsqueda y controles */}
      <SpoolSearch
        filters={filters}
        onFilterChange={updateFilter}
        onClearFilters={clearFilters}
        selectedCount={selectedCount}
        totalCount={totalCount}
        filteredCount={filteredCount}
        maxSelection={maxSelection}
        isMaxReached={isMaxReached}
        hasActiveFilters={hasActiveFilters}
        onSelectAll={handleSelectAll}
        onDeselectAll={handleDeselectAll}
      />

      {/* Componente de tabla de spools */}
      <SpoolTable
        spools={filteredSpools}
        selectedTags={selectedTags}
        isMaxReached={isMaxReached}
        onToggle={handleToggle}
        hasActiveFilters={hasActiveFilters}
      />
    </div>
  );
}
