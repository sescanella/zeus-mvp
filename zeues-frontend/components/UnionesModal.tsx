'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Modal } from '@/components/Modal';
import { getTodasUniones, guardarUniones } from '@/lib/api';
import type { SpoolCardData } from '@/lib/types';

// ─── Constants ──────────────────────────────────────────────────────────────────

const TIPO_UNION_OPTIONS = ['BW', 'SO', 'FILL', 'BR'] as const;
const DN_UNION_OPTIONS = Array.from({ length: 50 }, (_, i) => i + 1);
const MAX_UNIONS = 20;

// ─── Types ──────────────────────────────────────────────────────────────────────

interface UnionRow {
  n_union: number;
  dn_union: number | null;
  tipo_union: string | null;
  has_work: boolean;
}

interface UnionesModalProps {
  isOpen: boolean;
  spool: SpoolCardData;
  onComplete: () => void;
  onClose: () => void;
  isTopOfStack?: boolean;
}

// ─── Component ──────────────────────────────────────────────────────────────────

export function UnionesModal({ isOpen, spool, onComplete, onClose, isTopOfStack = true }: UnionesModalProps) {
  const [rows, setRows] = useState<UnionRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<number | null>(null);
  const [defaultDn, setDefaultDn] = useState<number | null>(null);
  const [defaultTipo, setDefaultTipo] = useState<string | null>(null);
  const [flashedRows, setFlashedRows] = useState<Set<number>>(new Set());
  const [countUnlocked, setCountUnlocked] = useState(false);
  const cardRefs = useRef<Map<number, HTMLDivElement>>(new Map());
  const prevRowCountRef = useRef(0);

  const loadUnions = useCallback(async () => {
    if (!spool.tag_spool) return;

    const hasExisting = spool.total_uniones !== null && spool.total_uniones > 0;
    if (!hasExisting) {
      setRows([{ n_union: 1, dn_union: null, tipo_union: null, has_work: false }]);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const data = await getTodasUniones(spool.tag_spool);
      const loaded: UnionRow[] = data.unions.map((u) => ({
        n_union: u.n_union,
        dn_union: u.dn_union,
        tipo_union: u.tipo_union,
        has_work: u.has_work,
      }));
      setRows(loaded.length > 0 ? loaded : [{ n_union: 1, dn_union: null, tipo_union: null, has_work: false }]);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Error al cargar uniones';
      setError(msg);
      setRows([{ n_union: 1, dn_union: null, tipo_union: null, has_work: false }]);
    } finally {
      setLoading(false);
    }
  }, [spool.tag_spool]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (isOpen) {
      setRows([]);
      setDefaultDn(null);
      setDefaultTipo(null);
      setFlashedRows(new Set());
      setCountUnlocked(false);
      loadUnions();
      setConfirmDelete(null);
    }
  }, [isOpen, loadUnions]);

  // Auto-scroll to newly added row
  useEffect(() => {
    if (rows.length > prevRowCountRef.current && rows.length > 0) {
      const lastCard = cardRefs.current.get(rows.length);
      if (lastCard) {
        lastCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    }
    prevRowCountRef.current = rows.length;
  }, [rows.length]);

  const renumber = (currentRows: UnionRow[]): UnionRow[] =>
    currentRows.map((r, i) => ({ ...r, n_union: i + 1 }));

  const handleCountChange = (newCount: number) => {
    if (!countUnlocked) return;
    if (newCount < 1 || newCount > MAX_UNIONS) return;
    setRows(prev => {
      if (newCount > prev.length) {
        const toAdd = Array.from({ length: newCount - prev.length }, (_, i) => ({
          n_union: prev.length + i + 1,
          dn_union: null as number | null,
          tipo_union: null as string | null,
          has_work: false,
        }));
        return [...prev, ...toAdd];
      }
      if (newCount < prev.length) {
        const minProtected = prev.reduce(
          (max, r) => (r.has_work && r.n_union > max ? r.n_union : max), 0
        );
        if (newCount < minProtected) return prev;
        return renumber(prev.slice(0, newCount));
      }
      return prev;
    });
  };

  const handleDeleteRow = (n_union: number) => {
    const row = rows.find((r) => r.n_union === n_union);
    if (!row || row.has_work) return;

    const isExisting = spool.total_uniones !== null && spool.total_uniones > 0 && n_union <= spool.total_uniones;
    if (isExisting && confirmDelete !== n_union) {
      setConfirmDelete(n_union);
      return;
    }

    setConfirmDelete(null);
    const filtered = rows.filter((r) => r.n_union !== n_union);
    setRows(renumber(filtered));
  };

  const handleDnChange = (n_union: number, value: string) => {
    setRows(rows.map((r) =>
      r.n_union === n_union ? { ...r, dn_union: value === '' ? null : parseInt(value, 10) } : r
    ));
  };

  const handleTipoChange = (n_union: number, value: string) => {
    setRows(rows.map((r) =>
      r.n_union === n_union ? { ...r, tipo_union: value === '' ? null : value } : r
    ));
  };

  const applyDefaultToEmpty = (field: 'dn_union' | 'tipo_union', value: number | string) => {
    setRows(prev => {
      const affected = new Set<number>();
      const updated = prev.map(r => {
        if (r.has_work) return r;
        if (r[field] !== null) return r;
        affected.add(r.n_union);
        return { ...r, [field]: value };
      });
      if (affected.size > 0) {
        setFlashedRows(affected);
        setTimeout(() => setFlashedRows(new Set()), 400);
      }
      return updated;
    });
  };

  const handleDefaultDnChange = (value: string) => {
    const parsed = value === '' ? null : parseInt(value, 10);
    setDefaultDn(parsed);
    if (parsed !== null) applyDefaultToEmpty('dn_union', parsed);
  };

  const handleDefaultTipoChange = (value: string) => {
    const val = value === '' ? null : value;
    setDefaultTipo(val);
    if (val !== null) applyDefaultToEmpty('tipo_union', val);
  };

  const isRowComplete = (row: UnionRow): boolean =>
    row.dn_union !== null && row.tipo_union !== null;

  const completedCount = rows.filter(isRowComplete).length;

  const handleGuardar = async () => {
    setError(null);
    if (rows.length === 0) return;

    setSaving(true);
    try {
      await guardarUniones({
        tag_spool: spool.tag_spool,
        unions: rows.map((r) => ({
          n_union: r.n_union,
          dn_union: r.dn_union,
          tipo_union: r.tipo_union,
        })),
      });
      onComplete();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Error al guardar uniones';
      setError(msg);
    } finally {
      setSaving(false);
    }
  };

  const setCardRef = useCallback((n_union: number, el: HTMLDivElement | null) => {
    if (el) {
      cardRefs.current.set(n_union, el);
    } else {
      cardRefs.current.delete(n_union);
    }
  }, []);

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      ariaLabel={`Gestionar uniones del spool ${spool.tag_spool}`}
      isTopOfStack={isTopOfStack}
      className="bg-zeues-navy border-4 border-white max-w-lg !p-0 flex flex-col max-h-[85vh]"
    >
      {/* ═══ FIXED TOP ZONE ═══ */}
      <div className="shrink-0 p-4 pb-2">
        {/* Title row */}
        <div className="flex items-center justify-between mb-2">
          <div>
            <h2 className="font-mono font-black text-lg text-white">UNIONES</h2>
            <p className="font-mono text-sm text-white/70">{spool.tag_spool}</p>
          </div>
          <span className="font-mono text-sm text-white/70">
            {completedCount} de {rows.length}
          </span>
        </div>

        {/* Quantity + Fill — single row */}
        <div className="flex items-center gap-2 mt-2">
          {/* Quantity control */}
          {!countUnlocked ? (
            <button
              onClick={() => setCountUnlocked(true)}
              aria-label="Desbloquear cambio de cantidad"
              className="h-10 px-3 border-2 border-white/30 text-white/50 font-mono font-black text-xs cursor-pointer hover:border-white/50 hover:text-white/70 focus:outline-none focus:ring-2 focus:ring-zeues-orange focus:ring-inset shrink-0"
            >
              TOTAL {rows.length}
            </button>
          ) : (
            <div className="flex items-center shrink-0">
              <button
                onClick={() => handleCountChange(rows.length - 1)}
                disabled={rows.length <= 1}
                aria-label="Reducir cantidad de uniones"
                className="h-10 w-10 border-2 border-white text-white font-mono font-black text-lg disabled:opacity-30 disabled:cursor-not-allowed hover:bg-white/10 focus:outline-none focus:ring-2 focus:ring-zeues-orange focus:ring-inset"
              >
                -
              </button>
              <input
                type="number"
                inputMode="numeric"
                min={1}
                max={MAX_UNIONS}
                value={rows.length}
                onChange={(e) => {
                  const val = parseInt(e.target.value, 10);
                  if (!isNaN(val)) handleCountChange(val);
                }}
                aria-label="Cantidad total de uniones"
                className="h-10 w-12 bg-zeues-navy border-y-2 border-white text-white font-mono font-black text-base text-center focus:outline-none focus:ring-2 focus:ring-zeues-orange focus:ring-inset [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
              />
              <button
                onClick={() => handleCountChange(rows.length + 1)}
                disabled={rows.length >= MAX_UNIONS}
                aria-label="Aumentar cantidad de uniones"
                className="h-10 w-10 border-2 border-white text-white font-mono font-black text-lg disabled:opacity-30 disabled:cursor-not-allowed hover:bg-white/10 focus:outline-none focus:ring-2 focus:ring-zeues-orange focus:ring-inset"
              >
                +
              </button>
              <button
                onClick={() => setCountUnlocked(false)}
                aria-label="Bloquear cantidad"
                className="ml-1 h-10 px-2 border-2 border-white/30 text-white/50 font-mono text-xs cursor-pointer hover:border-white/50 focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset"
              >
                OK
              </button>
            </div>
          )}

          {/* Separator */}
          <div className="w-px h-8 bg-white/20 shrink-0" />

          {/* Fill dropdowns */}
          {!loading && rows.length > 0 && (
            <>
              <select
                value={defaultDn ?? ''}
                onChange={(e) => handleDefaultDnChange(e.target.value)}
                aria-label="DN por defecto para uniones vacias"
                className="h-10 flex-1 min-w-0 bg-zeues-navy border border-white/40 text-white font-mono text-sm cursor-pointer focus:outline-none focus:ring-2 focus:ring-zeues-orange focus:ring-inset"
              >
                <option value="">DN</option>
                {DN_UNION_OPTIONS.map((dn) => (
                  <option key={dn} value={dn}>{dn}</option>
                ))}
              </select>
              <select
                value={defaultTipo ?? ''}
                onChange={(e) => handleDefaultTipoChange(e.target.value)}
                aria-label="Tipo por defecto para uniones vacias"
                className="h-10 flex-1 min-w-0 bg-zeues-navy border border-white/40 text-white font-mono text-sm cursor-pointer focus:outline-none focus:ring-2 focus:ring-zeues-orange focus:ring-inset"
              >
                <option value="">TIPO</option>
                {TIPO_UNION_OPTIONS.map((tipo) => (
                  <option key={tipo} value={tipo}>{tipo}</option>
                ))}
              </select>
            </>
          )}
        </div>

        {/* Progress bar */}
        {!loading && rows.length > 0 && (
          <div className="mt-2">
            <div className="h-1 bg-white/10 rounded-full overflow-hidden">
              <div
                className="h-full bg-zeues-orange transition-all duration-300"
                style={{ width: `${rows.length > 0 ? (completedCount / rows.length) * 100 : 0}%` }}
              />
            </div>
          </div>
        )}

        {/* Column headers */}
        {!loading && rows.length > 0 && (
          <div className="flex items-center gap-2 px-1.5 pt-2 pb-1 border-b border-white/10">
            <span className="font-mono font-black text-xs text-white/40 min-w-[2rem] text-center">#</span>
            <span className="font-mono font-black text-xs text-white/40 flex-1">DN</span>
            <span className="font-mono font-black text-xs text-white/40 flex-1">TIPO</span>
            <span className="min-w-[44px]" />
          </div>
        )}
      </div>

      {/* ═══ SCROLLABLE MIDDLE ZONE ═══ */}
      {loading && (
        <div className="flex items-center justify-center py-8">
          <div className="w-8 h-8 border-2 border-white/30 border-t-white rounded-full animate-spin" />
        </div>
      )}

      {error && (
        <div role="alert" className="text-red-400 font-mono font-black text-sm px-4 py-2">
          {error}
        </div>
      )}

      {!loading && (
        <div className="flex-1 overflow-y-auto px-4">
          <div className="flex flex-col gap-1.5 pr-1">
            {rows.map((row, index) => {
              const complete = isRowComplete(row);
              const isConfirmingThis = confirmDelete === row.n_union;

              const isFlashing = flashedRows.has(row.n_union);
              const isEven = index % 2 === 0;
              let borderClass = 'border-white/20';
              let bgClass = isEven ? 'bg-white/[0.02]' : '';
              if (isFlashing) {
                borderClass = 'border-zeues-orange';
                bgClass = 'bg-zeues-orange/10';
              } else if (row.has_work) {
                borderClass = 'border-white/10';
                bgClass = 'bg-white/5';
              } else if (!complete) {
                borderClass = 'border-yellow-400/60';
              }

              return (
                <div
                  key={row.n_union}
                  ref={(el) => setCardRef(row.n_union, el)}
                  className={`border p-1.5 flex items-center gap-2 transition-colors duration-300 ${borderClass} ${bgClass}`}
                >
                  <span className="font-mono font-black text-sm text-white min-w-[2rem] h-7 flex items-center justify-center bg-white/10 rounded">
                    {row.n_union}
                  </span>

                  <select
                    value={row.dn_union ?? ''}
                    onChange={(e) => handleDnChange(row.n_union, e.target.value)}
                    disabled={row.has_work}
                    aria-label={`DN union ${row.n_union}`}
                    className="h-10 flex-1 bg-zeues-navy border border-white/60 text-white font-mono text-sm cursor-pointer focus:outline-none focus:ring-2 focus:ring-zeues-orange focus:ring-inset disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    <option value="">DN</option>
                    {DN_UNION_OPTIONS.map((dn) => (
                      <option key={dn} value={dn}>{dn}</option>
                    ))}
                  </select>

                  <select
                    value={row.tipo_union ?? ''}
                    onChange={(e) => handleTipoChange(row.n_union, e.target.value)}
                    disabled={row.has_work}
                    aria-label={`Tipo union ${row.n_union}`}
                    className="h-10 flex-1 bg-zeues-navy border border-white/60 text-white font-mono text-sm cursor-pointer focus:outline-none focus:ring-2 focus:ring-zeues-orange focus:ring-inset disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    <option value="">TIPO</option>
                    {TIPO_UNION_OPTIONS.map((tipo) => (
                      <option key={tipo} value={tipo}>{tipo}</option>
                    ))}
                  </select>

                  {!row.has_work && !isConfirmingThis && (
                    <button
                      onClick={() => handleDeleteRow(row.n_union)}
                      aria-label={`Eliminar union ${row.n_union}`}
                      className="min-w-[44px] min-h-[44px] flex items-center justify-center text-white/30 hover:text-red-400 hover:bg-white/10 font-mono font-black text-sm focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset"
                    >
                      X
                    </button>
                  )}
                  {!row.has_work && isConfirmingThis && (
                    <div className="flex gap-1">
                      <button
                        onClick={() => handleDeleteRow(row.n_union)}
                        aria-label={`Confirmar eliminar union ${row.n_union}`}
                        className="min-h-[44px] px-2 flex items-center justify-center text-red-400 font-mono font-black text-xs border border-red-400 hover:bg-red-400/20 focus:outline-none focus:ring-2 focus:ring-red-400 focus:ring-inset"
                      >
                        Si
                      </button>
                      <button
                        onClick={() => setConfirmDelete(null)}
                        aria-label="Cancelar eliminacion"
                        className="min-w-[44px] min-h-[44px] flex items-center justify-center text-white/40 hover:text-white hover:bg-white/10 font-mono font-black text-xs focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset"
                      >
                        No
                      </button>
                    </div>
                  )}
                  {row.has_work && (
                    <span className="min-w-[44px] min-h-[44px]" />
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ═══ FIXED BOTTOM ZONE ═══ */}
      {!loading && (
        <div className="shrink-0 p-4 pt-3 border-t border-white/10 flex flex-col gap-2">
          <button
            onClick={handleGuardar}
            disabled={saving || rows.length === 0}
            aria-label="Guardar uniones"
            className="w-full h-14 bg-zeues-orange text-white font-mono font-black text-lg disabled:opacity-40 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset"
          >
            {saving ? 'GUARDANDO...' : 'GUARDAR'}
          </button>
          <button
            onClick={onClose}
            aria-label="Cancelar y cerrar"
            className="w-full h-10 border border-white/30 text-white/70 font-mono text-sm hover:border-white/50 focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset"
          >
            CANCELAR
          </button>
        </div>
      )}
    </Modal>
  );
}
