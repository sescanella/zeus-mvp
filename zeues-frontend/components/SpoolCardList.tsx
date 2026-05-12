'use client';

import { PackageOpen } from 'lucide-react';
import { SpoolCard } from '@/components/SpoolCard';
import type { SpoolCardData, EstadoTrabajo } from '@/lib/types';
import { ESTADO_LABELS } from '@/lib/constants';

interface SpoolCardListProps {
  spools: SpoolCardData[];
  onCardClick: (spool: SpoolCardData) => void;
  onRemove?: (tag: string) => void;
  onUnionesClick?: (spool: SpoolCardData) => void;
  onNotasClick?: (spool: SpoolCardData) => void;
  estadoFilter?: EstadoTrabajo | null;
  /** v5.1 UX-1a: substring match against tag_spool, case insensitive. Trimmed before comparison. */
  searchText?: string;
  /** v5.1 UX-1d: exact match against ocupado_por (format "INICIALES(ID)", e.g. "MR(93)"). */
  workerFilter?: string | null;
}

/**
 * Container for SpoolCard components with empty state and time-based sorting.
 *
 * When spools array is empty, shows a centered empty-state message with
 * a PackageOpen icon and instructions to add a spool.
 *
 * When non-empty, sorts by fecha_ocupacion descending (newest first; nulls
 * sort last). Renders one SpoolCard per spool in a vertical flex layout.
 *
 * onCardClick is forwarded to each card — opens the modal chain for that spool.
 */
export function SpoolCardList({ spools, onCardClick, onRemove, onUnionesClick, onNotasClick, estadoFilter, searchText, workerFilter }: SpoolCardListProps) {
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
    .filter((s) => !trimmedSearch || s.tag_spool.toLowerCase().includes(trimmedSearch))
    .filter((s) => !workerFilter || s.ocupado_por === workerFilter);

  if (filtered.length === 0) {
    const rawSearch = searchText?.trim();
    // Compose the message by describing each active filter in natural Spanish.
    // Listing every active filter avoids the user thinking only the text search
    // excluded everything when estado/worker filters also narrowed the list.
    const parts: string[] = [];
    if (estadoFilter) parts.push(`en estado "${ESTADO_LABELS[estadoFilter]}"`);
    if (workerFilter) parts.push(`de ${workerFilter}`);
    if (trimmedSearch) parts.push(`que coincidan con "${rawSearch}"`);
    const message =
      parts.length > 0 ? `Sin spools ${parts.join(' ')}` : 'Sin spools';
    return (
      <div className="flex flex-col items-center justify-center py-16 gap-4">
        <p className="text-white/70 font-mono font-black text-base">{message}</p>
      </div>
    );
  }

  // Sort by fecha_ocupacion descending (newest first); empty strings sort last.
  const sorted = [...filtered].sort((a, b) => {
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
          onCardClick={onCardClick}
          onRemove={onRemove}
          onUnionesClick={onUnionesClick}
          onNotasClick={onNotasClick}
        />
      ))}
    </div>
  );
}
