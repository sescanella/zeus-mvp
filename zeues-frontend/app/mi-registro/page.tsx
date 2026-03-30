'use client';

/**
 * /mi-registro — Personal worker registry page
 *
 * Read-only view of a worker's daily union work.
 * Designed for personal phones (not the work tablet).
 * No React Context, no modal stack, no polling.
 *
 * Three visual states:
 * 1. Worker Selection (no worker selected)
 * 2. Today View (default after selecting worker)
 * 3. Loading (fetching data)
 */

import React, { useState, useEffect, useCallback } from 'react';
import { getWorkers, getRegistro } from '@/lib/api';
import type { Worker, RegistroResponse, SpoolGroup } from '@/lib/types';

// ─── Blueprint grid overlay (matches BlueprintPageWrapper) ───────────────────

const BLUEPRINT_GRID_STYLE: React.CSSProperties = {
  backgroundImage: `
    linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)
  `,
  backgroundSize: '50px 50px',
};

// ─── Constants ────────────────────────────────────────────────────────────────

const LS_KEY = 'zeues_mi_registro_worker';

// ─── Date helpers ─────────────────────────────────────────────────────────────

/** Convert YYYY-MM-DD (native input) to DD-MM-YYYY (API format) */
function toChileanDate(isoDate: string): string {
  const [y, m, d] = isoDate.split('-');
  return `${d}-${m}-${y}`;
}

/** Get today as YYYY-MM-DD */
function todayIso(): string {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, '0');
  const d = String(now.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

// ─── Worker Selection State ──────────────────────────────────────────────────

function WorkerSelection({
  onSelect,
}: {
  onSelect: (worker: Worker) => void;
}) {
  const [workers, setWorkers] = useState<Worker[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    getWorkers()
      .then((allWorkers) => {
        if (cancelled) return;
        setWorkers(allWorkers.filter((w) => w.activo));
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const msg =
          err instanceof Error ? err.message : 'Error al cargar trabajadores';
        setError(msg);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const filtered = workers.filter((w) => {
    const q = search.toLowerCase();
    const fullName = `${w.nombre} ${w.apellido || ''} ${w.nombre_completo}`.toLowerCase();
    return fullName.includes(q);
  });

  return (
    <div className="min-h-screen bg-zeues-navy text-white font-mono" style={BLUEPRINT_GRID_STYLE}>
      <header className="p-4 text-center border-b-4 border-white/30">
        <h1 className="text-xl font-black tracking-widest uppercase">
          MI REGISTRO
        </h1>
        <p className="text-white/70 text-sm mt-1">Selecciona tu nombre</p>
      </header>

      <div className="max-w-md mx-auto px-4 py-4">
        {/* Search input */}
        <input
          type="text"
          placeholder="Buscar trabajador..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full h-12 px-4 bg-white/10 border border-white/30 text-white font-mono text-sm placeholder:text-white/40 focus:outline-none focus:ring-2 focus:ring-zeues-orange focus:ring-inset"
          aria-label="Buscar trabajador por nombre"
        />

        {/* Worker list */}
        <div className="flex flex-col gap-2 mt-4">
          {loading && (
            <div className="flex justify-center py-8" role="status" aria-label="Cargando trabajadores">
              <div className="w-8 h-8 border-2 border-white/30 border-t-white rounded-full animate-spin" aria-hidden="true" />
            </div>
          )}

          {error && (
            <p role="alert" className="text-red-400 font-mono text-sm font-black text-center py-4">
              {error}
            </p>
          )}

          {!loading && !error && filtered.map((worker) => (
            <button
              key={worker.id}
              onClick={() => onSelect(worker)}
              className="w-full h-14 px-4 text-left font-mono font-black text-white bg-white/5 border border-white/20 cursor-pointer hover:bg-white/10 focus:outline-none focus:ring-2 focus:ring-zeues-orange focus:ring-inset transition-colors"
              aria-label={`Seleccionar ${worker.nombre} ${worker.apellido || ''}`}
            >
              <span className="text-base">{worker.nombre} {worker.apellido || ''}</span>
              <span className="text-white/40 text-sm ml-2">{worker.nombre_completo}</span>
            </button>
          ))}

          {!loading && !error && filtered.length === 0 && (
            <p className="text-white/70 text-sm text-center py-8">
              No se encontraron trabajadores
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Spool Card ──────────────────────────────────────────────────────────────

function SpoolCard({ group }: { group: SpoolGroup }) {
  const opColor =
    group.operacion === 'ARM'
      ? 'bg-zeues-blue text-white'
      : 'bg-zeues-orange text-white';

  const unionNumbers = group.uniones.map((u) => u.n_union).join(', ');

  // Get date range from first/last union
  const fechas = group.uniones
    .filter((u) => u.fecha_inicio || u.fecha_fin)
    .sort((a, b) => (a.n_union ?? 0) - (b.n_union ?? 0));

  const fechaInicio = fechas.length > 0 ? fechas[0].fecha_inicio : null;
  const fechaFin = fechas.length > 0 ? fechas[fechas.length - 1].fecha_fin : null;

  return (
    <div className="bg-white/5 border border-white/20 p-4">
      {/* Header row */}
      <div className="flex items-center justify-between gap-2">
        <span className="text-white font-black text-base tracking-wider">
          {group.tag_spool}
        </span>
        <span
          className={`px-2 py-0.5 text-xs font-black tracking-widest ${opColor}`}
        >
          {group.operacion}
        </span>
      </div>

      {/* Unions list */}
      <p className="text-white/70 text-sm mt-2">
        Uniones: {unionNumbers}
      </p>

      {/* PD for this spool */}
      <p className="text-zeues-orange font-black text-sm mt-1">
        {group.pd_total} PD
      </p>

      {/* Other worker */}
      <p className="text-white/40 text-xs mt-1">
        Otro: {group.otro_trabajador || 'Pendiente'}
      </p>

      {/* Date range */}
      {(fechaInicio || fechaFin) && (
        <p className="text-white/40 text-xs mt-1">
          {fechaInicio ?? '—'} → {fechaFin ?? '—'}
        </p>
      )}
    </div>
  );
}

// ─── Today View ──────────────────────────────────────────────────────────────

function TodayView({
  worker,
  onChangeWorker,
}: {
  worker: Worker;
  onChangeWorker: () => void;
}) {
  const [dateIso, setDateIso] = useState(todayIso());
  const [data, setData] = useState<RegistroResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(
    async (isoDate: string) => {
      setLoading(true);
      setError(null);

      try {
        const chileanDate = toChileanDate(isoDate);
        const result = await getRegistro(worker.id, chileanDate);
        setData(result);
      } catch (err: unknown) {
        const msg =
          err instanceof Error ? err.message : 'Error al cargar registro';
        setError(msg);
        setData(null);
      } finally {
        setLoading(false);
      }
    },
    [worker.id],
  );

  useEffect(() => {
    fetchData(dateIso);
  }, [dateIso, fetchData]);

  const isToday = dateIso === todayIso();

  return (
    <div className="min-h-screen bg-zeues-navy text-white font-mono" style={BLUEPRINT_GRID_STYLE}>
      {/* Header */}
      <header className="p-4 border-b-4 border-white/30">
        <div className="max-w-md mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-lg font-black tracking-widest uppercase">
              MI REGISTRO
            </h1>
            <p className="text-white/70 text-sm mt-0.5">
              {worker.nombre} {worker.apellido || ''}{' '}
              <span className="text-white/40">{worker.nombre_completo}</span>
            </p>
          </div>
          <button
            onClick={onChangeWorker}
            className="px-3 py-2 text-xs font-black text-white/70 border border-white/30 cursor-pointer hover:text-white hover:border-white/50 focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset transition-colors"
            aria-label="Cambiar trabajador"
          >
            CAMBIAR
          </button>
        </div>
      </header>

      <div className="max-w-md mx-auto px-4 py-4">
        {/* Big PD number */}
        {!loading && data && (
          <div className="text-center py-4">
            <p className="text-5xl font-black text-zeues-orange leading-none">
              {data.resumen.pd_total}
            </p>
            <p className="text-white/70 text-sm mt-1 tracking-widest uppercase">
              PD {isToday ? 'HOY' : data.resumen.fecha}
            </p>
            <p className="text-white/40 text-xs mt-1">
              {data.resumen.total_uniones} uniones en{' '}
              {data.resumen.total_spools} spools
            </p>
          </div>
        )}

        {/* Date navigation */}
        <div className="flex gap-2 mt-2">
          <input
            type="date"
            value={dateIso}
            onChange={(e) => setDateIso(e.target.value)}
            className="flex-1 h-12 px-3 bg-white/10 border border-white/30 text-white font-mono text-sm focus:outline-none focus:ring-2 focus:ring-zeues-orange focus:ring-inset [color-scheme:dark]"
            aria-label="Seleccionar fecha"
          />
          <button
            onClick={() => setDateIso(todayIso())}
            disabled={isToday}
            className="h-12 px-4 font-black text-sm tracking-widest border border-white/30 cursor-pointer hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset transition-colors"
            aria-label="Ir a fecha de hoy"
          >
            HOY
          </button>
        </div>

        {/* Loading */}
        {loading && (
          <div
            className="flex justify-center py-12"
            role="status"
            aria-label="Cargando registro"
          >
            <div className="w-8 h-8 border-2 border-white/30 border-t-white rounded-full animate-spin" aria-hidden="true" />
          </div>
        )}

        {/* Error */}
        {error && (
          <p
            role="alert"
            className="text-red-400 font-mono text-sm font-black text-center py-8"
          >
            {error}
          </p>
        )}

        {/* Spool cards */}
        {!loading && !error && data && data.spools.length > 0 && (
          <div className="flex flex-col gap-3 mt-4">
            {data.spools.map((group, idx) => (
              <SpoolCard
                key={`${group.tag_spool}-${group.operacion}-${idx}`}
                group={group}
              />
            ))}
          </div>
        )}

        {/* Empty state */}
        {!loading && !error && data && data.spools.length === 0 && (
          <p className="text-white/70 text-sm text-center py-12">
            No hay uniones registradas para esta fecha.
          </p>
        )}
      </div>
    </div>
  );
}

// ─── Page (default export) ───────────────────────────────────────────────────

export default function MiRegistroPage() {
  const [worker, setWorker] = useState<Worker | null>(null);
  const [initialized, setInitialized] = useState(false);

  // Restore last selected worker from localStorage
  useEffect(() => {
    try {
      const stored = localStorage.getItem(LS_KEY);
      if (stored) {
        const parsed = JSON.parse(stored) as Worker;
        if (parsed && typeof parsed.id === 'number') {
          setWorker(parsed);
        }
      }
    } catch {
      // Invalid stored data — ignore
    }
    setInitialized(true);
  }, []);

  const handleSelectWorker = (w: Worker) => {
    setWorker(w);
    try {
      localStorage.setItem(LS_KEY, JSON.stringify(w));
    } catch {
      // localStorage full or unavailable — ignore
    }
  };

  const handleChangeWorker = () => {
    setWorker(null);
    try {
      localStorage.removeItem(LS_KEY);
    } catch {
      // ignore
    }
  };

  // Don't render until we've checked localStorage
  if (!initialized) {
    return (
      <div className="min-h-screen bg-zeues-navy flex items-center justify-center" style={BLUEPRINT_GRID_STYLE} role="status" aria-label="Cargando">
        <div className="w-8 h-8 border-2 border-white/30 border-t-white rounded-full animate-spin" aria-hidden="true" />
      </div>
    );
  }

  if (!worker) {
    return <WorkerSelection onSelect={handleSelectWorker} />;
  }

  return <TodayView worker={worker} onChangeWorker={handleChangeWorker} />;
}
