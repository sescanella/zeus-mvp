'use client';

import { PackageOpen } from 'lucide-react';
import { SpoolCard } from '@/components/SpoolCard';
import type { SpoolCardData, EstadoTrabajo } from '@/lib/types';
import { useSpoolList } from '@/lib/SpoolListContext';
import { ESTADO_LABELS } from '@/lib/constants';

interface SpoolCardListProps {
  spools: SpoolCardData[];
  onCardClick: (spool: SpoolCardData) => void;
  onRemove?: (tag: string) => void;
  onUnionesClick?: (spool: SpoolCardData) => void;
  estadoFilter?: EstadoTrabajo | null;
  /** v5.1 UX-1a: substring match against tag_spool, case insensitive. Trimmed before comparison. */
  searchText?: string;
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
export function SpoolCardList({ spools, onCardClick, onRemove, onUnionesClick, estadoFilter, searchText }: SpoolCardListProps) {
  const { priorities, setPriority } = useSpoolList();

  if (spools.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 gap-4">
        <PackageOpen
          className="text-white/40"
          size={48}
          aria-hidden="true"
        />
        <p className="text-white/70 font-mono font-black text-base">
          No hay spools en tu lista
        </p>
        <p className="text-white/60 font-mono text-sm">
          Usa el botón Añadir Spool para comenzar
        </p>
      </div>
    );
  }

  const trimmedSearch = (searchText ?? '').trim().toLowerCase();
  const filtered = spools
    .filter((s) => !estadoFilter || s.estado_trabajo === estadoFilter)
    .filter((s) => !trimmedSearch || s.tag_spool.toLowerCase().includes(trimmedSearch));

  if (filtered.length === 0) {
    const rawSearch = searchText?.trim();
    let message: string;
    if (trimmedSearch && estadoFilter) {
      message = `Sin spools "${ESTADO_LABELS[estadoFilter]}" que coincidan con "${rawSearch}"`;
    } else if (trimmedSearch) {
      message = `Sin spools que coincidan con "${rawSearch}"`;
    } else {
      message = 'Sin spools con ese estado';
    }
    return (
      <div className="flex flex-col items-center justify-center py-16 gap-4">
        <p className="text-white/70 font-mono font-black text-base">{message}</p>
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
