'use client';

import { CheckSquare, Square, Lock } from 'lucide-react';
import type { Spool } from '@/lib/types';

type TipoParam = 'tomar' | 'pausar' | 'completar' | 'cancelar' | 'metrologia' | 'reparacion' | null;

interface SpoolTableProps {
  spools: Spool[];
  selectedSpools: string[];
  onToggleSelect: (tag: string) => void;
  tipo: TipoParam;
}

export function SpoolTable({ spools, selectedSpools, onToggleSelect, tipo }: SpoolTableProps) {
  return (
    <div className="border-4 border-white overflow-hidden max-h-96 overflow-y-auto custom-scrollbar">
      <table className="w-full">
        <thead className="sticky top-0 bg-[#001F3F] border-b-4 border-white">
          <tr>
            <th className="p-3 text-left text-xs font-black text-white/70 font-mono border-r-2 border-white/30">SEL</th>
            <th className="p-3 text-left text-xs font-black text-white/70 font-mono border-r-2 border-white/30">{tipo === 'reparacion' ? 'CICLO/ESTADO' : 'NV'}</th>
            <th className="p-3 text-left text-xs font-black text-white/70 font-mono">TAG SPOOL</th>
          </tr>
        </thead>
        <tbody>
          {spools.map((spool) => {
            const isSelected = selectedSpools.includes(spool.tag_spool);
            const isBloqueado = tipo === 'reparacion' && (spool as unknown as { bloqueado?: boolean }).bloqueado;
            const cycle = tipo === 'reparacion' ? (spool as unknown as { cycle?: number }).cycle : null;

            return (
              <tr
                key={spool.tag_spool}
                role="button"
                tabIndex={isBloqueado ? -1 : 0}
                aria-label={`${isSelected ? 'Deseleccionar' : 'Seleccionar'} spool ${spool.tag_spool}${isBloqueado ? ' (bloqueado)' : ''}`}
                aria-disabled={isBloqueado ? true : undefined}
                onClick={() => !isBloqueado && onToggleSelect(spool.tag_spool)}
                onKeyDown={(e) => {
                  if (isBloqueado) return;
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    onToggleSelect(spool.tag_spool);
                  }
                }}
                className={`border-t-2 border-white/30 transition-colors focus:outline-none focus:ring-2 focus:ring-zeues-orange focus:ring-inset ${
                  isBloqueado
                    ? 'bg-red-500/20 border-red-500 cursor-not-allowed'
                    : isSelected
                    ? 'bg-zeues-orange/20 cursor-pointer'
                    : 'hover:bg-white/5 cursor-pointer'
                }`}
              >
                <td className="p-3 border-r-2 border-white/30">
                  {isBloqueado ? (
                    <Lock size={24} className="text-red-500" strokeWidth={3} />
                  ) : isSelected ? (
                    <CheckSquare size={24} className="text-zeues-orange" strokeWidth={3} />
                  ) : (
                    <Square size={24} className="text-white/50" strokeWidth={3} />
                  )}
                </td>
                <td className="p-3 border-r-2 border-white/30">
                  {tipo === 'reparacion' ? (
                    <div className="flex items-center gap-2">
                      {isBloqueado ? (
                        <span className="text-sm font-black text-red-500 font-mono">
                          BLOQUEADO - Supervisor
                        </span>
                      ) : (
                        <span className="text-sm font-black text-yellow-500 font-mono">
                          Ciclo {cycle}/3
                        </span>
                      )}
                    </div>
                  ) : (
                    <span className="text-sm font-black text-white/70 font-mono">{spool.nv}</span>
                  )}
                </td>
                <td className="p-3">
                  <span className={`text-lg font-black font-mono ${isBloqueado ? 'text-red-500' : 'text-white'}`}>
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
