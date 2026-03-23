'use client';

import { PackageOpen } from 'lucide-react';
import { SpoolCard } from '@/components/SpoolCard';
import type { SpoolCardData, EstadoTrabajo } from '@/lib/types';
import { useSpoolList } from '@/lib/SpoolListContext';

interface SpoolCardListProps {
  spools: SpoolCardData[];
  onCardClick: (spool: SpoolCardData) => void;
  onRemove?: (tag: string) => void;
  onUnionesClick?: (spool: SpoolCardData) => void;
  estadoFilter?: EstadoTrabajo | null;
}

/**
 * Container for SpoolCard components with empty state and priority-based sorting.
 *
 * When spools array is empty, shows a centered empty-state message with
 * a PackageOpen icon and instructions to add a spool.
 *
 * When non-empty, sorts spools by priority (1 first, then 2, then 3, then null),
 * with ties broken by fecha_ocupacion ascending (oldest first = longest wait).
 * Renders one SpoolCard per spool in a vertical flex layout.
 *
 * onCardClick is forwarded to each card — opens the modal chain for that spool.
 * Priority state is read from and written to SpoolListContext.
 *
 * Plan: 02-01-PLAN.md Task 2
 */
export function SpoolCardList({ spools, onCardClick, onRemove, onUnionesClick, estadoFilter }: SpoolCardListProps) {
  const { priorities, setPriority } = useSpoolList();

  if (spools.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 gap-4">
        <PackageOpen
          className="text-white/30"
          size={48}
          aria-hidden="true"
        />
        <p className="text-white/50 font-mono font-black text-base">
          No hay spools en tu lista
        </p>
        <p className="text-white/30 font-mono text-sm">
          Usa el botón Añadir Spool para comenzar
        </p>
      </div>
    );
  }

  const filtered = estadoFilter
    ? spools.filter((s) => s.estado_trabajo === estadoFilter)
    : spools;

  if (filtered.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 gap-4">
        <p className="text-white/50 font-mono font-black text-base">
          Sin spools con ese estado
        </p>
      </div>
    );
  }

  // Sort: priority 1 > 2 > 3 > null (99), then by fecha_ocupacion newest first (nulls last)
  const sorted = [...filtered].sort((a, b) => {
    const pa = priorities.get(a.tag_spool) ?? 99;
    const pb = priorities.get(b.tag_spool) ?? 99;
    if (pa !== pb) return pa - pb;
    const fa = a.fecha_ocupacion ?? '';
    const fb = b.fecha_ocupacion ?? '';
    return fb.localeCompare(fa);
  });

  return (
    <div className="flex flex-col gap-4">
      {sorted.map((spool) => (
        <SpoolCard
          key={spool.tag_spool}
          spool={spool}
          priority={priorities.get(spool.tag_spool) ?? null}
          onCardClick={onCardClick}
          onRemove={onRemove}
          onUnionesClick={onUnionesClick}
          onPriorityChange={setPriority}
        />
      ))}
    </div>
  );
}
