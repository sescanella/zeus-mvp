'use client';

import React from 'react';
import { CheckSquare, Square, Lock } from 'lucide-react';

interface Union {
  id: string; // Composite ID: TAG_SPOOL+N_UNION (e.g., 'OT-123+5')
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
  selectedUnions?: string[]; // Union IDs (format: "OT-123+5")
  onSelectionChange?: (selected: string[]) => void;
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
  const handleCheckboxChange = (unionId: string, isChecked: boolean) => {
    if (onSelectionChange) {
      const newSelection = isChecked
        ? [...selectedUnions, unionId]
        : selectedUnions.filter(id => id !== unionId);
      onSelectionChange(newSelection);
    }
  };

  const isUnionCompleted = (union: Union) => {
    if (operacion === 'ARM') {
      return !!union.arm_fecha_fin;
    }
    return !!union.sol_fecha_fin;
  };

  if (unions.length === 0) {
    return (
      <div className="border-4 border-white/50 p-8 bg-white/5">
        <p className="text-lg text-white/70 font-mono text-center">
          NO HAY UNIONES DISPONIBLES
        </p>
      </div>
    );
  }

  return (
    <div className="border-4 border-white overflow-hidden max-h-[calc(100dvh-26rem)] overflow-y-auto">
      <table className="w-full border-collapse">
        <thead className="sticky top-0 bg-[#001F3F] border-b-4 border-white z-10">
          <tr>
            <th scope="col" className="p-3 text-center text-xs font-black text-white/70 font-mono border-r-2 border-white/30">
              SEL
            </th>
            <th scope="col" className="p-3 text-left text-xs font-black text-white/70 font-mono border-r-2 border-white/30">
              N° UNIÓN
            </th>
            <th scope="col" className="p-3 text-left text-xs font-black text-white/70 font-mono border-r-2 border-white/30">
              DN
            </th>
            <th scope="col" className="p-3 text-left text-xs font-black text-white/70 font-mono">
              TIPO
            </th>
          </tr>
        </thead>
        <tbody>
          {sortedUnions.map((union) => {
            const isCompleted = isUnionCompleted(union);
            const isSelected = selectedUnions.includes(union.id);
            const isRowDisabled = disabled || isCompleted;

            return (
              <tr
                key={union.id}
                onClick={() => !isRowDisabled && handleCheckboxChange(union.id, !isSelected)}
                className={`
                  border-t-2 border-white/30 transition-colors cursor-pointer
                  ${isCompleted ? 'opacity-30 cursor-not-allowed' : ''}
                  ${isSelected && !isCompleted ? 'bg-zeues-orange/20' : 'hover:bg-white/5'}
                `}
              >
                <td className="p-3 border-r-2 border-white/30 text-center">
                  {isCompleted ? (
                    <Lock size={24} className="text-white/30 inline-block" strokeWidth={3} />
                  ) : isSelected ? (
                    <CheckSquare size={24} className="text-zeues-orange inline-block" strokeWidth={3} />
                  ) : (
                    <Square size={24} className="text-white/50 inline-block" strokeWidth={3} />
                  )}
                </td>
                <td className="p-3 border-r-2 border-white/30">
                  <span className={`text-lg font-black font-mono ${isCompleted ? 'line-through text-white/30' : 'text-white'}`}>
                    {union.n_union}
                  </span>
                </td>
                <td className="p-3 border-r-2 border-white/30">
                  <span className={`text-lg font-black font-mono ${isCompleted ? 'line-through text-white/30' : 'text-white'}`}>
                    {union.dn_union}&quot;
                  </span>
                </td>
                <td className="p-3">
                  <div className="flex items-center gap-2">
                    <span className={`text-base font-black font-mono ${isCompleted ? 'line-through text-white/30' : 'text-white/70'}`}>
                      {union.tipo_union}
                    </span>
                    {isCompleted && (
                      <span className="px-2 py-1 text-xs font-black font-mono border-2 border-green-500/50 text-green-400 bg-green-500/10">
                        ✓ {operacion === 'ARM' ? 'ARMADA' : 'SOLDADA'}
                      </span>
                    )}
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
