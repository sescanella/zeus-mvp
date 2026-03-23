'use client';

import { PackageOpen } from 'lucide-react';
import { SpoolCard } from '@/components/SpoolCard';
import type { SpoolCardData } from '@/lib/types';
import { useSpoolList } from '@/lib/SpoolListContext';

interface SpoolCardListProps {
  spools: SpoolCardData[];
  onCardClick: (spool: SpoolCardData) => void;
  onRemove?: (tag: string) => void;
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
export function SpoolCardList({ spools, onCardClick, onRemove }: SpoolCardListProps) {
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
          Usa el boton Anadir Spool para comenzar
        </p>
      </div>
    );
  }

  // Sort: priority 1 > 2 > 3 > null (null treated as 99), then by fecha_ocupacion oldest first
  const sorted = [...spools].sort((a, b) => {
    const pa = priorities.get(a.tag_spool) ?? 99;
    const pb = priorities.get(b.tag_spool) ?? 99;
    if (pa !== pb) return pa - pb;
    // Same priority: sort by fecha_ocupacion (oldest first, nulls last)
    const fa = a.fecha_ocupacion ?? '';
    const fb = b.fecha_ocupacion ?? '';
    return fa.localeCompare(fb);
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
          onPriorityChange={setPriority}
        />
      ))}
    </div>
  );
}
