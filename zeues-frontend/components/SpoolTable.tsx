import { Spool } from '@/lib/types';
import { Checkbox } from './Checkbox';

interface SpoolTableProps {
  spools: Spool[];
  selectedTags: string[];
  isMaxReached: boolean;
  onToggle: (tag: string) => void;
  hasActiveFilters: boolean;
}

/**
 * Componente de tabla de spools con checkboxes integrados
 *
 * Features:
 * - Tabla responsive con scroll (max-h-500px)
 * - Checkbox en cada fila
 * - Click en fila completa para toggle
 * - Estados visuales (selected, disabled)
 * - Sticky header
 */
export function SpoolTable({
  spools,
  selectedTags,
  isMaxReached,
  onToggle,
  hasActiveFilters,
}: SpoolTableProps) {
  if (spools.length === 0) {
    return (
      <div className="p-8 text-center text-gray-500 border-2 border-gray-200 rounded-lg">
        {hasActiveFilters
          ? 'No hay spools que coincidan con los filtros aplicados'
          : 'No hay spools disponibles'}
      </div>
    );
  }

  return (
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
          {spools.map((spool) => {
            const isSelected = selectedTags.includes(spool.tag_spool);
            const isDisabled = !isSelected && isMaxReached;

            return (
              <tr
                key={spool.tag_spool}
                onClick={() => !isDisabled && onToggle(spool.tag_spool)}
                className={`
                  cursor-pointer transition-colors h-16
                  ${isSelected
                    ? 'bg-zeues-blue/10 hover:bg-zeues-blue/20'
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
                    <span className={`text-base font-medium ${isSelected ? 'text-zeues-blue' : 'text-gray-900'}`}>
                      {spool.nv || '-'}
                    </span>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <span className={`text-base ${isSelected ? 'text-zeues-blue font-medium' : 'text-gray-700'}`}>
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
  );
}
