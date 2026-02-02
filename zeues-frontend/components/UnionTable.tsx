'use client';

import React from 'react';

interface Union {
  n_union: number;
  dn_union: number;
  tipo_union: string;
  is_completed?: boolean;
  arm_fecha_fin?: string;
  sol_fecha_fin?: string;
}

interface UnionTableProps {
  unions: Union[];
  operacion: 'ARM' | 'SOLD';
  selectedUnions?: number[];
  onSelectionChange?: (selected: number[]) => void;
  disabled?: boolean;
}

export function UnionTable({
  unions,
  operacion,
  selectedUnions = [],
  onSelectionChange,
  disabled = false,
}: UnionTableProps) {
  // Sort unions by n_union ascending
  const sortedUnions = [...unions].sort((a, b) => a.n_union - b.n_union);

  // Handle checkbox selection change
  const handleCheckboxChange = (n_union: number, isChecked: boolean) => {
    if (onSelectionChange) {
      const newSelection = isChecked
        ? [...selectedUnions, n_union]
        : selectedUnions.filter(n => n !== n_union);
      onSelectionChange(newSelection);
    }
  };

  // Determine completion status based on operacion
  const getCompletionBadge = (union: Union) => {
    if (operacion === 'ARM' && union.arm_fecha_fin) {
      return (
        <span className="inline-flex items-center px-2 py-1 text-xs font-medium text-green-700 bg-green-100 rounded">
          ✓ Armada
        </span>
      );
    }
    if (operacion === 'SOLD' && union.sol_fecha_fin) {
      return (
        <span className="inline-flex items-center px-2 py-1 text-xs font-medium text-green-700 bg-green-100 rounded">
          ✓ Soldada
        </span>
      );
    }
    return null;
  };

  const isUnionCompleted = (union: Union) => {
    if (operacion === 'ARM') {
      return !!union.arm_fecha_fin;
    }
    return !!union.sol_fecha_fin;
  };

  if (unions.length === 0) {
    return (
      <div className="p-8 text-center text-gray-500 border-2 border-gray-200 rounded-lg">
        No hay uniones disponibles
      </div>
    );
  }

  return (
    <div className="overflow-auto border-2 border-gray-200 rounded-lg max-h-[500px]">
      <table className="w-full border-collapse">
        <thead className="bg-gray-50 border-b sticky top-0 z-10">
          <tr>
            <th scope="col" className="w-16 py-3 text-center text-sm font-semibold text-gray-900 uppercase tracking-wider">
              Seleccionar
            </th>
            <th scope="col" className="px-4 py-3 text-left text-sm font-semibold text-gray-900 uppercase tracking-wider">
              N° Unión
            </th>
            <th scope="col" className="px-4 py-3 text-left text-sm font-semibold text-gray-900 uppercase tracking-wider">
              DN
            </th>
            <th scope="col" className="px-4 py-3 text-left text-sm font-semibold text-gray-900 uppercase tracking-wider">
              Tipo
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {sortedUnions.map((union) => {
            const isCompleted = isUnionCompleted(union);
            const isSelected = selectedUnions.includes(union.n_union);
            const isRowDisabled = disabled || isCompleted;

            return (
              <tr
                key={union.n_union}
                className={`
                  border-b min-h-[64px] transition-colors
                  ${isCompleted ? 'opacity-50' : 'hover:bg-gray-50 transition-colors'}
                `}
              >
                <td className="w-16 text-center">
                  <input
                    type="checkbox"
                    checked={isSelected}
                    disabled={isRowDisabled}
                    onChange={(e) => handleCheckboxChange(union.n_union, e.target.checked)}
                    className="w-14 h-14 cursor-pointer transition-opacity duration-150 disabled:cursor-not-allowed"
                    aria-label={`Seleccionar unión ${union.n_union}`}
                  />
                </td>
                <td className="px-4 py-3">
                  <span className={`text-base font-medium ${isCompleted ? 'line-through' : 'text-gray-900'}`}>
                    {union.n_union}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className={`text-base ${isCompleted ? 'line-through' : 'text-gray-700'}`}>
                    {union.dn_union}&quot;
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <span className={`text-base ${isCompleted ? 'line-through' : 'text-gray-700'}`}>
                      {union.tipo_union}
                    </span>
                    {getCompletionBadge(union)}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
