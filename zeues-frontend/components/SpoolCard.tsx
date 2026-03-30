'use client';

import { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import { hapticTap } from '@/lib/haptic';
import type { SpoolCardData } from '@/lib/types';
import { ESTADO_LABELS, ESTADO_COLORS } from '@/lib/constants';

export type { SpoolCardData };

export interface SpoolCardProps {
  spool: SpoolCardData;
  priority: number | null; // 1=urgente, 2=alta, 3=normal, null=sin prioridad
  onCardClick: (spool: SpoolCardData) => void;
  onRemove?: (tag: string) => void;
  onPriorityChange?: (tag: string, priority: number | null) => void;
  onUnionesClick?: (spool: SpoolCardData) => void;
}

const OPERACION_LABELS: Record<string, string> = {
  ARM: 'Armado',
  SOLD: 'Soldadura',
  REPARACION: 'Reparación',
};

// ─── Priority color map ────────────────────────────────────────────────────────
const PRIORITY_COLORS: Record<number, string> = {
  1: 'bg-red-600 text-white border-red-500',
  2: 'bg-zeues-orange text-white border-zeues-orange',
  3: 'bg-white/20 text-white border-white/30',
};
const PRIORITY_DEFAULT = 'bg-white/5 text-white/70 border-white/10';

// ─── Priority cycle ────────────────────────────────────────────────────────────
function nextPriority(current: number | null): number | null {
  if (current === null) return 1;
  if (current === 3) return null;
  return current + 1;
}

// ─── useElapsedSeconds ─────────────────────────────────────────────────────────

/**
 * Parses fecha_ocupacion in "DD-MM-YYYY HH:MM:SS" (Chilean) format.
 * Returns elapsed seconds since that timestamp, updating every second.
 * Returns null when no valid timestamp or when not occupied.
 *
 * NEVER uses new Date() directly on the raw string — it's not ISO format.
 */
function useElapsedSeconds(
  ocupadoPor: string | null | undefined,
  fechaOcupacion: string | null | undefined,
  isPausado: boolean
): number | null {
  const shouldTrack =
    !isPausado &&
    ocupadoPor !== null &&
    ocupadoPor !== undefined &&
    ocupadoPor !== '' &&
    fechaOcupacion !== null &&
    fechaOcupacion !== undefined;

  // Parse "DD-MM-YYYY HH:MM:SS" → timestamp ms
  const startMs: number | null = shouldTrack
    ? parseFechaOcupacion(fechaOcupacion!)
    : null;

  const [elapsed, setElapsed] = useState<number | null>(() => {
    if (startMs === null) return null;
    return Math.floor((Date.now() - startMs) / 1000);
  });

  useEffect(() => {
    if (startMs === null) {
      setElapsed(null);
      return;
    }

    // Compute initial elapsed immediately
    setElapsed(Math.floor((Date.now() - startMs) / 1000));

    const id = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startMs) / 1000));
    }, 1000);

    return () => clearInterval(id);
  }, [startMs]);

  return elapsed;
}

/**
 * Parse "DD-MM-YYYY HH:MM:SS" string into a local millisecond timestamp.
 * Constructs the Date using local time fields so that elapsed calculation
 * matches the device's clock — both start time and Date.now() are in local time.
 *
 * Returns null if the string is missing or doesn't match the expected pattern.
 */
function parseFechaOcupacion(raw: string): number | null {
  const match = raw.match(
    /^(\d{2})-(\d{2})-(\d{4})\s+(\d{2}):(\d{2}):(\d{2})$/
  );
  if (!match) return null;

  const [, dd, mm, yyyy, hh, min, ss] = match;
  const ms = new Date(
    parseInt(yyyy, 10),
    parseInt(mm, 10) - 1,
    parseInt(dd, 10),
    parseInt(hh, 10),
    parseInt(min, 10),
    parseInt(ss, 10)
  ).getTime();

  return ms;
}

// ─── Timer formatting ──────────────────────────────────────────────────────────

function formatElapsed(totalSeconds: number): string {
  if (totalSeconds < 0) totalSeconds = 0;
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  const mm = String(minutes).padStart(2, '0');
  const ss = String(seconds).padStart(2, '0');

  if (hours > 0) {
    const hh = String(hours).padStart(2, '0');
    return `${hh}:${mm}:${ss}`;
  }
  return `${mm}:${ss}`;
}

// ─── SpoolCard ─────────────────────────────────────────────────────────────────

/**
 * Individual spool card for the v5.0 single-page view.
 *
 * Layout: flex row with priority block on the left and card content on the right.
 * - Priority block: fixed w-16, clickable to cycle 1→2→3→null
 * - Content block: tag, badges, worker + timer on same row
 *
 * Timer is hidden when estado_trabajo === 'PAUSADO' (STATE-06).
 * Keyboard accessible: Enter/Space triggers onCardClick on content area.
 * Priority button uses stopPropagation to avoid triggering onCardClick.
 *
 * Plan: 02-01-PLAN.md Task 1
 */
export function SpoolCard({ spool, priority, onCardClick, onRemove, onPriorityChange, onUnionesClick }: SpoolCardProps) {
  const isPausado = spool.estado_trabajo === 'PAUSADO';
  const [confirmingRemove, setConfirmingRemove] = useState(false);

  const elapsed = useElapsedSeconds(
    spool.ocupado_por,
    spool.fecha_ocupacion,
    isPausado
  );

  const estadoColors =
    spool.estado_trabajo !== null
      ? (ESTADO_COLORS[spool.estado_trabajo] ?? 'text-white border-white/30')
      : 'text-white border-white/30';

  const operacionLabel = spool.operacion_actual
    ? (OPERACION_LABELS[spool.operacion_actual] ?? spool.operacion_actual)
    : null;

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onCardClick(spool);
    }
  };

  return (
    <div className="flex border-4 rounded-none border-white/20 min-h-[5rem]">
      {/* Priority block — left side */}
      <button
        onClick={(e) => {
          e.stopPropagation();
          hapticTap();
          onPriorityChange?.(spool.tag_spool, nextPriority(priority));
        }}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            e.stopPropagation();
            hapticTap();
            onPriorityChange?.(spool.tag_spool, nextPriority(priority));
          }
        }}
        aria-label={`Prioridad spool ${spool.tag_spool}: ${priority ?? 'sin prioridad'}. Click para cambiar`}
        className={`flex flex-col items-center justify-center w-16 shrink-0 min-h-[5rem] border-r-4 border-white/20 cursor-pointer transition-colors duration-200 hover:opacity-80 active:opacity-60 focus:outline-none focus:ring-2 focus:ring-zeues-orange focus:ring-inset ${priority !== null ? PRIORITY_COLORS[priority] : PRIORITY_DEFAULT}`}
      >
        <span className="font-mono text-sm font-black tracking-widest uppercase">PRIO</span>
        <span className="font-mono text-2xl font-black">{priority ?? '-'}</span>
      </button>

      {/* Content — right side (clickable for card action) */}
      <div
        role="button"
        tabIndex={0}
        aria-label={`Procesar spool ${spool.tag_spool}${spool.estado_trabajo ? ` - ${ESTADO_LABELS[spool.estado_trabajo] ?? spool.estado_trabajo}` : ''}`}
        onClick={() => onCardClick(spool)}
        onKeyDown={handleKeyDown}
        className="flex-1 bg-zeues-navy px-4 py-3 cursor-pointer hover:bg-white/5 active:bg-white/10 focus:outline-none focus:ring-2 focus:ring-zeues-orange focus:ring-inset"
      >
        {/* Tag + Remove button */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {spool.nv && (
              <span className="font-mono font-black text-sm px-2 py-0.5 border-2 border-white/30 text-white/70">
                {spool.nv}
              </span>
            )}
            <span className="text-lg font-black font-mono text-white">
              {spool.tag_spool}
            </span>
          </div>
          {onRemove && !confirmingRemove && (
            <button
              onClick={(e) => { e.stopPropagation(); setConfirmingRemove(true); }}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); e.stopPropagation(); setConfirmingRemove(true); } }}
              aria-label={`Quitar spool ${spool.tag_spool} de la lista`}
              className="min-w-[44px] min-h-[44px] flex items-center justify-center text-white/40 hover:text-white hover:bg-white/10 rounded focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset"
            >
              <X size={16} aria-hidden="true" />
            </button>
          )}
          {onRemove && confirmingRemove && (
            <div className="flex gap-1" onClick={(e) => e.stopPropagation()}>
              <button
                onClick={() => { onRemove(spool.tag_spool); setConfirmingRemove(false); }}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); e.stopPropagation(); onRemove(spool.tag_spool); setConfirmingRemove(false); } }}
                aria-label={`Confirmar quitar spool ${spool.tag_spool}`}
                className="min-h-[44px] px-3 flex items-center justify-center text-red-400 font-mono font-black text-sm border-2 border-red-400 hover:bg-red-400/20 rounded focus:outline-none focus:ring-2 focus:ring-red-400 focus:ring-inset"
              >
                Quitar
              </button>
              <button
                onClick={() => setConfirmingRemove(false)}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); e.stopPropagation(); setConfirmingRemove(false); } }}
                aria-label="Cancelar"
                className="min-w-[44px] min-h-[44px] flex items-center justify-center text-white/40 hover:text-white hover:bg-white/10 rounded focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset"
              >
                <X size={16} aria-hidden="true" />
              </button>
            </div>
          )}
        </div>

        {/* Badges row */}
        <div className="flex flex-wrap gap-2 mt-1">
          {/* Operacion badge */}
          {operacionLabel !== null && (
            <span className="font-mono font-black text-sm px-2 py-0.5 border-2 text-zeues-orange border-zeues-orange">
              {operacionLabel}
            </span>
          )}

          {/* Estado badge */}
          {spool.estado_trabajo !== null && (
            <span
              className={`font-mono font-black text-sm px-2 py-0.5 border-2 ${estadoColors}`}
            >
              {ESTADO_LABELS[spool.estado_trabajo] ?? spool.estado_trabajo}
            </span>
          )}

          {/* Uniones badge removed — button is on right side of card */}
        </div>

        {/* Union progress indicators (ARM/SOLD partial or complete) */}
        {spool.total_uniones !== null && spool.total_uniones > 0 && (
          <div className="flex flex-wrap gap-2 mt-1">
            {spool.uniones_arm_completadas !== null && spool.uniones_arm_completadas > 0 && (
              <span className={`font-mono text-sm px-1.5 py-0.5 border ${
                spool.uniones_arm_completadas >= spool.total_uniones
                  ? 'text-green-400 border-green-400/40'
                  : 'text-yellow-400 border-yellow-400/40'
              }`}>
                ARM {spool.uniones_arm_completadas}/{spool.total_uniones}
              </span>
            )}
            {spool.uniones_sold_completadas !== null && spool.uniones_sold_completadas > 0 && (
              <span className={`font-mono text-sm px-1.5 py-0.5 border ${
                spool.uniones_sold_completadas >= spool.total_uniones
                  ? 'text-green-400 border-green-400/40'
                  : 'text-yellow-400 border-yellow-400/40'
              }`}>
                SOLD {spool.uniones_sold_completadas}/{spool.total_uniones}
              </span>
            )}
          </div>
        )}

        {/* Completion history — computed by backend, no logic here */}
        {spool.completion_history?.length > 0 && (
          <div className="flex flex-col gap-0.5 mt-1">
            {spool.completion_history.map((entry) => (
              <span key={entry.operation} className="font-mono text-sm text-green-400">
                {entry.operation} — {entry.worker} — {entry.date}
              </span>
            ))}
          </div>
        )}

        {/* Worker + Timer on same row — only render if there's content */}
        {(() => {
          type WithDisplay = SpoolCardData & { ocupado_por_display?: string | null };
          const s = spool as WithDisplay;
          const workerName = s.ocupado_por_display ?? s.ocupado_por;
          const showTimer = !isPausado && elapsed !== null;
          if (!workerName && !showTimer) return null;
          return (
            <div className="flex items-center justify-between mt-1">
              {workerName && (
                <span className="font-mono text-sm text-white/90">{workerName}</span>
              )}
              {showTimer && (
                <span className="font-mono text-sm font-black text-zeues-orange">
                  {formatElapsed(elapsed!)}
                </span>
              )}
            </div>
          );
        })()}
      </div>

      {/* Uniones button — right side */}
      {onUnionesClick && (
        <button
          onClick={(e) => { e.stopPropagation(); onUnionesClick(spool); }}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              e.stopPropagation();
              onUnionesClick(spool);
            }
          }}
          aria-label={`Gestionar uniones spool ${spool.tag_spool}${spool.total_uniones ? `: ${spool.total_uniones} uniones` : ': sin uniones'}`}
          className="flex flex-col items-center justify-center w-20 shrink-0 min-h-[5rem] border-l-4 border-white/20 cursor-pointer transition-colors duration-200 hover:bg-white/5 active:bg-white/10 focus:outline-none focus:ring-2 focus:ring-zeues-orange focus:ring-inset"
        >
          <span className="font-mono text-sm font-black tracking-widest text-white/70">Uniones</span>
          <span className={`font-mono text-xl font-black ${
            spool.total_uniones === 0 || spool.total_uniones === null
              ? 'text-yellow-400'
              : 'text-white'
          }`}>
            {spool.total_uniones ?? 0}
          </span>
        </button>
      )}
    </div>
  );
}
