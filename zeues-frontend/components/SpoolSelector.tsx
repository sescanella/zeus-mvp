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
 * SpoolSelector component para multiselect de spools (v2.0 batch operations).
 *
 * Features:
 * - Búsqueda en tiempo real por TAG_SPOOL (case-insensitive)
 * - Checkboxes touch-friendly para tablet
 * - Select All / Deselect All masivos
 * - Contador de selección: "X de Y spools seleccionados"
 * - Límite máximo (default 50) con disabled cuando se alcanza
 * - Mobile-first design con Tailwind
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
  const [searchTerm, setSearchTerm] = useState('');

  // Filtrar spools por búsqueda (case-insensitive)
  const filteredSpools = useMemo(() => {
    if (!searchTerm.trim()) return spools;

    const lowerSearch = searchTerm.toLowerCase();
    return spools.filter(spool =>
      spool.tag_spool.toLowerCase().includes(lowerSearch)
    );
  }, [spools, searchTerm]);

  const isMaxReached = selectedTags.length >= maxSelection;

  // Toggle individual spool
  const handleToggle = (tag: string, checked: boolean) => {
    if (checked) {
      // Solo agregar si no alcanzamos el límite
      if (!isMaxReached) {
        onSelectChange([...selectedTags, tag]);
      }
    } else {
      // Remover
      onSelectChange(selectedTags.filter(t => t !== tag));
    }
  };

  // Seleccionar todos los spools filtrados (hasta el límite)
  const handleSelectAll = () => {
    const tagsToAdd = filteredSpools
      .map(s => s.tag_spool)
      .filter(tag => !selectedTags.includes(tag));

    const remainingSlots = maxSelection - selectedTags.length;
    const newTags = tagsToAdd.slice(0, remainingSlots);

    onSelectChange([...selectedTags, ...newTags]);
  };

  // Deseleccionar todos los spools filtrados
  const handleDeselectAll = () => {
    const filteredTagSet = new Set(filteredSpools.map(s => s.tag_spool));
    onSelectChange(selectedTags.filter(tag => !filteredTagSet.has(tag)));
  };

  const selectedCount = selectedTags.length;
  const totalCount = spools.length;
  const filteredCount = filteredSpools.length;

  return (
    <div className={`flex flex-col gap-4 ${className}`}>
      {/* Search input */}
      <div className="flex flex-col gap-2">
        <label htmlFor="search-spool" className="text-sm font-medium text-gray-700">
          Buscar por TAG_SPOOL
        </label>
        <input
          id="search-spool"
          type="text"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="Ej: MK-1335-CW-25238-011"
          className="
            w-full h-12 px-4 text-lg
            border-2 border-gray-300 rounded-lg
            focus:border-cyan-600 focus:outline-none
            placeholder:text-gray-400
          "
        />
      </div>

      {/* Counter and action buttons */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
        <div className="text-lg font-medium text-gray-900">
          {selectedCount} de {totalCount} spools seleccionados
          {isMaxReached && (
            <span className="ml-2 text-sm text-red-600 font-normal">
              (Límite máximo: {maxSelection})
            </span>
          )}
        </div>

        <div className="flex gap-2">
          <Button
            onClick={handleSelectAll}
            variant="primary"
            disabled={filteredSpools.length === 0 || isMaxReached}
            className="text-sm h-12"
          >
            Seleccionar Todos
          </Button>
          <Button
            onClick={handleDeselectAll}
            variant="cancel"
            disabled={selectedCount === 0}
            className="text-sm h-12"
          >
            Deseleccionar Todos
          </Button>
        </div>
      </div>

      {/* Info message when filtered */}
      {searchTerm && (
        <div className="text-sm text-gray-600">
          {filteredCount === 0 ? (
            <span className="text-red-600">No se encontraron spools que coincidan con &quot;{searchTerm}&quot;</span>
          ) : (
            <span>Mostrando {filteredCount} de {totalCount} spools</span>
          )}
        </div>
      )}

      {/* Spools grid */}
      {filteredSpools.length > 0 ? (
        <div className="
          grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3
          max-h-[60vh] overflow-y-auto
          p-2 border-2 border-gray-200 rounded-lg
        ">
          {filteredSpools.map((spool) => {
            const isSelected = selectedTags.includes(spool.tag_spool);
            const isDisabled = !isSelected && isMaxReached;

            return (
              <div
                key={spool.tag_spool}
                className={`
                  p-3 rounded-lg border-2 transition-colors
                  ${isSelected
                    ? 'bg-cyan-50 border-cyan-600'
                    : isDisabled
                      ? 'bg-gray-50 border-gray-200'
                      : 'bg-white border-gray-300 hover:border-cyan-400'
                  }
                `}
              >
                <Checkbox
                  id={`spool-${spool.tag_spool}`}
                  checked={isSelected}
                  onChange={(checked) => handleToggle(spool.tag_spool, checked)}
                  label={spool.tag_spool}
                  disabled={isDisabled}
                />
                {spool.proyecto && (
                  <div className="mt-1 ml-9 text-sm text-gray-500">
                    {spool.proyecto}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <div className="p-8 text-center text-gray-500 border-2 border-gray-200 rounded-lg">
          {searchTerm ? 'No hay spools que coincidan con tu búsqueda' : 'No hay spools disponibles'}
        </div>
      )}
    </div>
  );
}
