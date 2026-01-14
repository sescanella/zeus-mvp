import { Button } from './Button';

interface Filter {
  field: string;
  value: string;
}

interface SpoolSearchProps {
  filters: Filter[];
  onFilterChange: (field: string, value: string) => void;
  onClearFilters: () => void;
  selectedCount: number;
  totalCount: number;
  filteredCount: number;
  maxSelection: number;
  isMaxReached: boolean;
  hasActiveFilters: boolean;
  onSelectAll: () => void;
  onDeselectAll: () => void;
}

/**
 * Componente de búsqueda y filtros para SpoolSelector
 *
 * Features:
 * - 2 inputs de búsqueda (NV y TAG_SPOOL)
 * - Botones de acción (Select All, Deselect All, Clear Filters)
 * - Contador de selección
 * - Mensaje de filtro activo
 */
export function SpoolSearch({
  filters,
  onFilterChange,
  onClearFilters,
  selectedCount,
  totalCount,
  filteredCount,
  maxSelection,
  isMaxReached,
  hasActiveFilters,
  onSelectAll,
  onDeselectAll,
}: SpoolSearchProps) {
  const nvFilter = filters.find(f => f.field === 'nv')?.value || '';
  const tagFilter = filters.find(f => f.field === 'tag_spool')?.value || '';

  return (
    <div className="flex flex-col gap-4">
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
            onChange={(e) => onFilterChange('nv', e.target.value)}
            placeholder="Ej: 001, 002..."
            className="
              w-full h-12 px-4 text-lg
              border-2 border-gray-300 rounded-lg
              focus:border-zeues-blue focus:outline-none
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
            onChange={(e) => onFilterChange('tag_spool', e.target.value)}
            placeholder="Ej: MK-1335-CW-25238-011"
            className="
              w-full h-12 px-4 text-lg
              border-2 border-gray-300 rounded-lg
              focus:border-zeues-blue focus:outline-none
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
            onClick={onSelectAll}
            variant="primary"
            disabled={filteredCount === 0 || isMaxReached}
            className="text-sm h-12 whitespace-nowrap"
          >
            Seleccionar Visibles
          </Button>
          <Button
            onClick={onDeselectAll}
            variant="cancel"
            disabled={selectedCount === 0}
            className="text-sm h-12 whitespace-nowrap"
          >
            Deseleccionar Todos
          </Button>
          {hasActiveFilters && (
            <Button
              onClick={onClearFilters}
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
                onClick={onClearFilters}
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
    </div>
  );
}
