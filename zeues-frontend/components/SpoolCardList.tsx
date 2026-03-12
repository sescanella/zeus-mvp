'use client';

import { PackageOpen } from 'lucide-react';
import { SpoolCard } from '@/components/SpoolCard';
import type { SpoolCardData } from '@/lib/types';

interface SpoolCardListProps {
  spools: SpoolCardData[];
  selectedTags?: Set<string>;
  onCardClick: (spool: SpoolCardData) => void;
  onRemove?: (tag: string) => void;
}

/**
 * Container for SpoolCard components with empty state.
 *
 * When spools array is empty, shows a centered empty-state message with
 * a PackageOpen icon and instructions to add a spool.
 *
 * When non-empty, renders one SpoolCard per spool in a vertical flex layout.
 * onCardClick is forwarded to each card.
 * selectedTags set controls which cards show the selected highlight.
 *
 * Plan: 02-01-PLAN.md Task 2
 */
export function SpoolCardList({ spools, selectedTags, onCardClick, onRemove }: SpoolCardListProps) {
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

  return (
    <div className="flex flex-col gap-4">
      {spools.map((spool) => (
        <SpoolCard
          key={spool.tag_spool}
          spool={spool}
          isSelected={selectedTags?.has(spool.tag_spool) ?? false}
          onCardClick={onCardClick}
          onRemove={onRemove}
        />
      ))}
    </div>
  );
}
