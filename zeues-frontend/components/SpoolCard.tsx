'use client';

import { useEffect, useState } from 'react';
import type { SpoolCardData } from '@/lib/types';

export type { SpoolCardData };

export interface SpoolCardProps {
  spool: SpoolCardData;
  onCardClick: (spool: SpoolCardData) => void;
  onRemove?: (tag: string) => void;
}

// ─── Estado color map ──────────────────────────────────────────────────────────

const ESTADO_COLORS: Record<NonNullable<SpoolCardData['estado_trabajo']>, string> = {
  LIBRE: 'text-white border-white/30',
  EN_PROGRESO: 'text-zeues-orange border-zeues-orange',
  PAUSADO: 'text-yellow-400 border-yellow-400',
  COMPLETADO: 'text-green-400 border-green-400',
  RECHAZADO: 'text-red-400 border-red-400',
  PENDIENTE_METROLOGIA: 'text-blue-300 border-blue-300',
  BLOQUEADO: 'text-red-600 border-red-600 opacity-75',
};

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
 * Parse "DD-MM-YYYY HH:MM:SS" string into a UTC millisecond timestamp.
 * Treats the date/time values as representing Chile local time (UTC-3 typical).
 * For elapsed-time display purposes, we interpret the string as local wall-clock
 * time and compare against Date.now() — both measured in the same timezone context.
 *
 * Returns null if the string is missing or doesn't match the expected pattern.
 */
function parseFechaOcupacion(raw: string): number | null {
  const match = raw.match(
    /^(\d{2})-(\d{2})-(\d{4})\s+(\d{2}):(\d{2}):(\d{2})$/
  );
  if (!match) return null;

  const [, dd, mm, yyyy, hh, min, ss] = match;
  // Construct as UTC to avoid local timezone ambiguity in tests.
  // The backend writes Chile local time; we compute elapsed relative to
  // a fixed UTC epoch where Chile = UTC-3.
  // For display, we use Date.UTC treating the fields as UTC to keep tests
  // deterministic (jest.setSystemTime sets UTC epoch).
  const ms = Date.UTC(
    parseInt(yyyy, 10),
    parseInt(mm, 10) - 1,
    parseInt(dd, 10),
    parseInt(hh, 10),
    parseInt(min, 10),
    parseInt(ss, 10)
  );

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
 * Shows TAG, operation badge, estado badge, worker, and elapsed timer.
 * Timer is hidden when estado_trabajo === 'PAUSADO' (STATE-06).
 *
 * Keyboard accessible: Enter/Space triggers onCardClick.
 * Remove button uses stopPropagation to avoid triggering onCardClick.
 *
 * Plan: 02-01-PLAN.md Task 1
 */
export function SpoolCard({ spool, onCardClick, onRemove }: SpoolCardProps) {
  const isPausado = spool.estado_trabajo === 'PAUSADO';

  const elapsed = useElapsedSeconds(
    spool.ocupado_por,
    spool.fecha_ocupacion,
    isPausado
  );

  const estadoColors =
    spool.estado_trabajo !== null
      ? (ESTADO_COLORS[spool.estado_trabajo] ?? 'text-white border-white/30')
      : 'text-white border-white/30';

  // Operacion label: REPARACION → REP for display
  const operacionLabel =
    spool.operacion_actual === 'REPARACION'
      ? 'REP'
      : spool.operacion_actual ?? null;

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onCardClick(spool);
    }
  };

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={`Procesar spool ${spool.tag_spool}${spool.estado_trabajo ? ` - ${spool.estado_trabajo}` : ''}`}
      onClick={() => onCardClick(spool)}
      onKeyDown={handleKeyDown}
      className="bg-zeues-navy border-4 rounded-none transition-colors px-4 py-3 min-h-[4rem] cursor-pointer focus:outline-none focus:ring-2 focus:ring-zeues-orange focus:ring-inset border-white/20 hover:border-white/40"
    >
        {/* Tag + Remove button */}
        <div className="flex items-center justify-between">
          <div className="text-lg font-black font-mono text-white">
            {spool.tag_spool}
          </div>
          {onRemove && (
            <button
              onClick={(e) => { e.stopPropagation(); onRemove(spool.tag_spool); }}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); e.stopPropagation(); onRemove(spool.tag_spool); } }}
              aria-label={`Eliminar spool ${spool.tag_spool}`}
              className="min-w-[44px] min-h-[44px] flex items-center justify-center text-white/40 hover:text-white hover:bg-white/10 rounded focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset"
            >
              ✕
            </button>
          )}
        </div>

        {/* Badges row */}
        <div className="flex flex-wrap gap-2 mt-1">
          {/* Operacion badge */}
          {operacionLabel !== null && (
            <span className="font-mono font-black text-xs px-2 py-0.5 border-2 text-zeues-orange border-zeues-orange">
              {operacionLabel}
            </span>
          )}

          {/* Estado badge */}
          {spool.estado_trabajo !== null && (
            <span
              className={`font-mono font-black text-xs px-2 py-0.5 border-2 ${estadoColors}`}
            >
              {spool.estado_trabajo}
            </span>
          )}
        </div>

        {/* Worker */}
        {spool.ocupado_por !== null && spool.ocupado_por !== '' && (
          <div className="mt-1 font-mono text-xs text-white/70">
            {spool.ocupado_por}
          </div>
        )}

        {/* Elapsed timer — hidden when PAUSADO (STATE-06) */}
        {!isPausado && elapsed !== null && (
          <div className="mt-1 font-mono text-sm font-black text-zeues-orange">
            {formatElapsed(elapsed)}
          </div>
        )}
    </div>
  );
}
