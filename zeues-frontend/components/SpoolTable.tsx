'use client';

import { CheckSquare, Square, Lock } from 'lucide-react';
import type { Spool, ReparacionSpool } from '@/lib/types';

type TipoParam = 'tomar' | 'pausar' | 'completar' | 'cancelar' | 'metrologia' | 'reparacion' | null;

interface SpoolTableProps {
  spools: (Spool | ReparacionSpool)[];
  selectedSpools: string[];
  onToggleSelect: (tag: string) => void;
  /** Legacy prop: passed by call-sites but no longer used for rendering. */
  tipo?: TipoParam;
  disabledSpools?: string[];
  maxHeight?: string;
}

export function SpoolTable({ spools, selectedSpools, onToggleSelect, disabledSpools = [], maxHeight = 'max-h-96' }: SpoolTableProps) {
  return (
    <div className={`border-4 border-white overflow-hidden ${maxHeight} overflow-y-auto custom-scrollbar`}>
      <table className="w-full">
        <thead className="sticky top-0 bg-zeues-navy border-b-4 border-white">
          <tr>
            <th className="p-3 text-left text-xs font-black text-white/70 font-mono border-r-2 border-white/30">SEL</th>
            <th className="p-3 text-left text-xs font-black text-white/70 font-mono border-r-2 border-white/30">NV</th>
            <th className="p-3 text-left text-xs font-black text-white/70 font-mono">TAG SPOOL</th>
          </tr>
        </thead>
        <tbody>
          {spools.map((spool, index) => {
            const isSelected = selectedSpools.includes(spool.tag_spool);
            const isDisabled = disabledSpools.includes(spool.tag_spool);

            return (
              <tr
                key={`${spool.tag_spool}-${index}`}
                role="button"
                tabIndex={isDisabled ? -1 : 0}
                aria-label={`${isSelected ? 'Deseleccionar' : 'Seleccionar'} spool ${spool.tag_spool}${isDisabled ? ' (ya agregado)' : ''}`}
                aria-disabled={isDisabled ? true : undefined}
                onClick={() => !isDisabled && onToggleSelect(spool.tag_spool)}
                onKeyDown={(e) => {
                  if (isDisabled) return;
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    onToggleSelect(spool.tag_spool);
                  }
                }}
                className={`border-t-2 border-white/30 transition-colors focus:outline-none focus:ring-2 focus:ring-zeues-orange focus:ring-inset ${
                  isDisabled
                    ? 'bg-white/10 opacity-50 cursor-not-allowed'
                    : isSelected
                    ? 'bg-zeues-orange/20 cursor-pointer'
                    : 'hover:bg-white/5 cursor-pointer'
                }`}
              >
                <td className="p-3 border-r-2 border-white/30">
                  {isDisabled ? (
                    <Lock size={24} className="text-white/40" strokeWidth={3} />
                  ) : isSelected ? (
                    <CheckSquare size={24} className="text-zeues-orange" strokeWidth={3} />
                  ) : (
                    <Square size={24} className="text-white/70" strokeWidth={3} />
                  )}
                </td>
                <td className="p-3 border-r-2 border-white/30">
                  <span className="text-sm font-black text-white/70 font-mono">{'nv' in spool ? spool.nv : ''}</span>
                </td>
                <td className="p-3">
                  <span className="text-lg font-black font-mono text-white">
                    {spool.tag_spool}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
