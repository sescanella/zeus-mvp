'use client';

import { useState, useMemo } from 'react';
import { Spool } from '@/lib/types';
import { Checkbox } from './Checkbox';
import { Button } from './Button';

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
 * SpoolSelector component con tabla + filtros multidimensionales (v2.0).
 *
 * Features:
 * - Tabla responsive NV | TAG_SPOOL (mobile-first)
 * - 2 barras búsqueda: NV y TAG_SPOOL (lógica AND)
 * - Sistema filters[] genérico (escalable para más dimensiones)
 * - Checkboxes integrados en filas (row clickeable)
 * - Select All / Deselect All (solo visibles filtrados)
 * - Botón "Limpiar Filtros" cuando filtros activos
 * - Límite máximo (default 50)
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
  const updateFilter = (field: keyof Spool, value: string) => {
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

  // Obtener valores actuales de filtros
  const nvFilter = filters.find(f => f.field === 'nv')?.value || '';
  const tagFilter = filters.find(f => f.field === 'tag_spool')?.value || '';

  return (
    <div className={`flex flex-col gap-4 ${className}`}>
      {/* 2 Inputs de búsqueda horizontales */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {/* Input NV */}
        <div className="flex flex-col gap-2">
          <label htmlFor="filter-nv" className="text-sm font-medium text-gray-700">
            Buscar por NV (Nota de Venta)
          </label>
          <input
            id="filter-nv"
            type="text"
            value={nvFilter}
            onChange={(e) => updateFilter('nv', e.target.value)}
            placeholder="Ej: 001, 002..."
            className="
              w-full h-12 px-4 text-lg
              border-2 border-gray-300 rounded-lg
              focus:border-cyan-600 focus:outline-none
              placeholder:text-gray-400
            "
          />
        </div>

        {/* Input TAG_SPOOL */}
        <div className="flex flex-col gap-2">
          <label htmlFor="filter-tag" className="text-sm font-medium text-gray-700">
            Buscar por TAG_SPOOL
          </label>
          <input
            id="filter-tag"
            type="text"
            value={tagFilter}
            onChange={(e) => updateFilter('tag_spool', e.target.value)}
            placeholder="Ej: MK-1335-CW-25238-011"
            className="
              w-full h-12 px-4 text-lg
              border-2 border-gray-300 rounded-lg
              focus:border-cyan-600 focus:outline-none
              placeholder:text-gray-400
            "
          />
        </div>
      </div>

      {/* Counter, action buttons y Limpiar Filtros */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
        <div className="text-lg font-medium text-gray-900">
          {selectedCount} de {totalCount} spools seleccionados
          {isMaxReached && (
            <span className="ml-2 text-sm text-red-600 font-normal">
              (Límite máximo: {maxSelection})
            </span>
          )}
        </div>

        <div className="flex flex-nowrap gap-2">
          <Button
            onClick={handleSelectAll}
            variant="primary"
            disabled={filteredSpools.length === 0 || isMaxReached}
            className="text-sm h-12 whitespace-nowrap"
          >
            Seleccionar Visibles
          </Button>
          <Button
            onClick={handleDeselectAll}
            variant="cancel"
            disabled={selectedCount === 0}
            className="text-sm h-12 whitespace-nowrap"
          >
            Deseleccionar Todos
          </Button>
          {hasActiveFilters && (
            <Button
              onClick={clearFilters}
              variant="cancel"
              className="text-sm h-12 whitespace-nowrap"
            >
              Limpiar Filtros
            </Button>
          )}
        </div>
      </div>

      {/* Info message cuando hay filtros activos */}
      {hasActiveFilters && (
        <div className="text-sm text-gray-600">
          {filteredCount === 0 ? (
            <div className="flex flex-col gap-2 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
              <span className="text-yellow-800 font-medium">
                No se encontraron spools que coincidan con los filtros aplicados
              </span>
              <Button
                onClick={clearFilters}
                variant="cancel"
                className="text-sm h-10 w-fit"
              >
                Limpiar Filtros
              </Button>
            </div>
          ) : (
            <span>Mostrando {filteredCount} de {totalCount} spools (filtrado activo)</span>
          )}
        </div>
      )}

      {/* Tabla responsive de spools CON SCROLL */}
      {filteredSpools.length > 0 ? (
        <div className="
          max-h-[500px]
          overflow-y-auto
          overflow-x-auto
          border-2 border-gray-200 rounded-lg
        ">
          <table className="w-full min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50 sticky top-0 z-10">
              <tr>
                <th scope="col" className="px-4 py-3 text-left text-sm font-semibold text-gray-900 uppercase tracking-wider">
                  NV
                </th>
                <th scope="col" className="px-4 py-3 text-left text-sm font-semibold text-gray-900 uppercase tracking-wider">
                  TAG_SPOOL
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredSpools.map((spool) => {
                const isSelected = selectedTags.includes(spool.tag_spool);
                const isDisabled = !isSelected && isMaxReached;

                return (
                  <tr
                    key={spool.tag_spool}
                    onClick={() => !isDisabled && handleToggle(spool.tag_spool)}
                    className={`
                      cursor-pointer transition-colors h-16
                      ${isSelected
                        ? 'bg-cyan-50 hover:bg-cyan-100'
                        : isDisabled
                          ? 'bg-gray-50 cursor-not-allowed opacity-50'
                          : 'hover:bg-gray-50'
                      }
                    `}
                  >
                    <td className="px-4 py-3 whitespace-nowrap">
                      <div className="flex items-center gap-3">
                        <Checkbox
                          id={`spool-checkbox-${spool.tag_spool}`}
                          checked={isSelected}
                          onChange={() => {}} // Handled by row click
                          disabled={isDisabled}
                          className="pointer-events-none"
                        />
                        <span className={`text-base font-medium ${isSelected ? 'text-cyan-900' : 'text-gray-900'}`}>
                          {spool.nv || '-'}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-base ${isSelected ? 'text-cyan-900 font-medium' : 'text-gray-700'}`}>
                        {spool.tag_spool}
                      </span>
                      {spool.proyecto && (
                        <div className="text-sm text-gray-500 mt-1">
                          {spool.proyecto}
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="p-8 text-center text-gray-500 border-2 border-gray-200 rounded-lg">
          {hasActiveFilters
            ? 'No hay spools que coincidan con los filtros aplicados'
            : 'No hay spools disponibles'}
        </div>
      )}
    </div>
  );
}
