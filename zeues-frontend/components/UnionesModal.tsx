'use client';

import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { Modal } from '@/components/Modal';
import { getTodasUniones, guardarUniones } from '@/lib/api';
import { classifyApiError } from '@/lib/error-classifier';
import type { SpoolCardData } from '@/lib/types';

// ─── Constants ──────────────────────────────────────────────────────────────────

const TIPO_UNION_OPTIONS = ['BW', 'SO', 'FILL', 'BR', 'MIT'] as const;

type DnOption = { value: number; label: string; ariaLabel?: string };
const DN_UNION_OPTIONS: ReadonlyArray<DnOption> = [
  { value: 0.5,  label: '½',  ariaLabel: 'media pulgada' },
  { value: 0.75, label: '¾',  ariaLabel: 'tres cuartos de pulgada' },
  { value: 1,    label: '1' },
  { value: 1.5,  label: '1½', ariaLabel: 'una y media pulgadas' },
  { value: 1.75, label: '1¾', ariaLabel: 'una y tres cuartos pulgadas' },
  { value: 2,    label: '2' },
  { value: 2.5,  label: '2½', ariaLabel: 'dos y media pulgadas' },
  { value: 3,    label: '3' },
  { value: 3.5,  label: '3½', ariaLabel: 'tres y media pulgadas' },
  { value: 4,    label: '4' },
  { value: 5,    label: '5' },
  ...Array.from({ length: 22 }, (_, i) => {
    const v = (i + 3) * 2;
    return { value: v, label: String(v) } as DnOption;
  }), // 6, 8, 10, ..., 48
];
const MAX_UNIONS = 20;

// ─── Types ──────────────────────────────────────────────────────────────────────

interface UnionRow {
  n_union: number;
  dn_union: number | null;
  tipo_union: string | null;
  has_work: boolean;
  id: string | null;
  arm_worker: string | null;
  sol_worker: string | null;
  selected: boolean;
}

interface UnionesModalProps {
  isOpen: boolean;
  spool: SpoolCardData;
  operacion: 'ARM' | 'SOLD' | null;
  onComplete: (selectedUnionIds: string[]) => void;
  onClose: () => void;
  isTopOfStack?: boolean;
}

// ─── Helpers ────────────────────────────────────────────────────────────────────

function isRowSelectable(row: UnionRow, operacion: 'ARM' | 'SOLD' | null, spoolArmDone?: boolean): boolean {
  if (operacion === null) return false;
  if (row.dn_union === null || row.tipo_union === null) return false;
  if (operacion === 'ARM') {
    return row.arm_worker === null;
  }
  // SOLD: no SOLD yet + ARM done (either at union level or spool level for legacy spools)
  if (row.sol_worker !== null) return false;
  return row.arm_worker !== null || spoolArmDone === true;
}

// ─── Component ──────────────────────────────────────────────────────────────────

export function UnionesModal({ isOpen, spool, operacion, onComplete, onClose, isTopOfStack = true }: UnionesModalProps) {
  const spoolArmDone = Boolean(spool.fecha_armado);
  const [rows, setRows] = useState<UnionRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<number | null>(null);
  const [defaultDn, setDefaultDn] = useState<number | null>(null);
  const [defaultTipo, setDefaultTipo] = useState<string | null>(null);
  const [flashedRows, setFlashedRows] = useState<Set<number>>(new Set());
  // Local string value for the TOTAL input. Decoupled from rows.length so the
  // user can clear the field (e.g. delete the leading "1" to type "5") without
  // React snapping the "1" right back due to the controlled value. We reconcile
  // on blur: if the user leaves the input empty or invalid, fall back to
  // rows.length.
  const [countInput, setCountInput] = useState('1');
  const cardRefs = useRef<Map<number, HTMLDivElement>>(new Map());
  const prevRowCountRef = useRef(0);

  const emptyRow: UnionRow = { n_union: 1, dn_union: null, tipo_union: null, has_work: false, id: null, arm_worker: null, sol_worker: null, selected: false };

  const loadUnions = useCallback(async () => {
    if (!spool.tag_spool) return;

    setLoading(true);
    setError(null);
    try {
      const data = await getTodasUniones(spool.tag_spool);
      const loaded: UnionRow[] = data.unions.map((u) => ({
        n_union: u.n_union,
        dn_union: u.dn_union,
        tipo_union: u.tipo_union,
        has_work: u.has_work,
        id: u.id ?? null,
        arm_worker: u.arm_worker ?? null,
        sol_worker: u.sol_worker ?? null,
        selected: false,
      }));
      setRows(loaded.length > 0 ? loaded : [emptyRow]);
    } catch (err: unknown) {
      setError(classifyApiError(err).userMessage);
      setRows([{ n_union: 1, dn_union: null, tipo_union: null, has_work: false, id: null, arm_worker: null, sol_worker: null, selected: false }]);
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

  // Keep the local input string in sync with rows.length when the source of
  // truth changes from outside the input — e.g. modal opens, unions load from
  // backend, or user removes a row from the list. Skip the update while the
  // input is focused so we don't clobber what the user is actively typing.
  useEffect(() => {
    const active = typeof document !== 'undefined' ? document.activeElement : null;
    if (active && (active as HTMLElement).id === 'uniones-count') return;
    setCountInput(String(rows.length || 1));
  }, [rows.length]);

  const handleCountChange = (newCount: number) => {
    if (newCount < 1 || newCount > MAX_UNIONS) return;
    setRows(prev => {
      if (newCount > prev.length) {
        const maxExisting = prev.reduce((max, r) => Math.max(max, r.n_union), 0);
        const toAdd = Array.from({ length: newCount - prev.length }, (_, i) => ({
          n_union: maxExisting + i + 1,
          dn_union: null as number | null,
          tipo_union: null as string | null,
          has_work: false,
          id: null as string | null,
          arm_worker: null as string | null,
          sol_worker: null as string | null,
          selected: false,
        }));
        return [...prev, ...toAdd];
      }
      if (newCount < prev.length) {
        const workCount = prev.filter(r => r.has_work).length;
        if (newCount < workCount) return prev;
        const toRemove = prev.length - newCount;
        // Remove highest-numbered empty (no work) rows first
        const emptyRows = prev
          .filter(r => !r.has_work)
          .sort((a, b) => b.n_union - a.n_union);
        const removeSet = new Set(emptyRows.slice(0, toRemove).map(r => r.n_union));
        return prev.filter(r => !removeSet.has(r.n_union));
      }
      return prev;
    });
  };

  const handleDeleteRow = (n_union: number) => {
    const row = rows.find((r) => r.n_union === n_union);
    if (!row || row.has_work) return;

    const isExisting = row?.id !== null;
    if (isExisting && confirmDelete !== n_union) {
      setConfirmDelete(n_union);
      return;
    }

    setConfirmDelete(null);
    const filtered = rows.filter((r) => r.n_union !== n_union);
    setRows(filtered);
  };

  const handleDnChange = (n_union: number, value: string) => {
    setRows(rows.map((r) =>
      r.n_union === n_union ? { ...r, dn_union: value === '' ? null : parseFloat(value) } : r
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
    const parsed = value === '' ? null : parseFloat(value);
    setDefaultDn(parsed);
    if (parsed !== null) applyDefaultToEmpty('dn_union', parsed);
  };

  const handleDefaultTipoChange = (value: string) => {
    const val = value === '' ? null : value;
    setDefaultTipo(val);
    if (val !== null) applyDefaultToEmpty('tipo_union', val);
  };

  const handleToggleSelect = (n_union: number) => {
    setRows(prev => prev.map(r => {
      if (r.n_union !== n_union) return r;
      if (!isRowSelectable(r, operacion, spoolArmDone)) return r;
      return { ...r, selected: !r.selected };
    }));
  };

  const handleSelectAllAvailable = () => {
    setRows(prev => prev.map(r =>
      isRowSelectable(r, operacion, spoolArmDone)
        ? { ...r, selected: true }
        : r
    ));
  };

  const handleDeselectAll = () => {
    setRows(prev => prev.map(r => ({ ...r, selected: false })));
  };

  const isRowComplete = (row: UnionRow): boolean =>
    row.dn_union !== null && row.tipo_union !== null;

  const completedCount = rows.filter(isRowComplete).length;

  const selectedRows = useMemo(() => rows.filter(r => r.selected), [rows]);
  const selectedPD = useMemo(() => selectedRows.reduce((sum, r) => sum + (r.dn_union ?? 0), 0), [selectedRows]);
  const selectableCount = useMemo(
    () => rows.filter(r => isRowSelectable(r, operacion, spoolArmDone)).length,
    [rows, operacion, spoolArmDone]
  );
  const someSelected = selectedRows.length > 0;
  const showSelectAllButton = operacion !== null && selectableCount >= 2;

  const handleGuardar = async () => {
    setError(null);
    if (rows.length === 0) return;

    setSaving(true);
    try {
      const result = await guardarUniones({
        tag_spool: spool.tag_spool,
        unions: rows.map((r) => ({
          n_union: r.n_union,
          dn_union: r.dn_union,
          tipo_union: r.tipo_union,
        })),
      });

      if (selectedRows.length > 0) {
        // New unions get IDs from backend response, existing unions keep local IDs
        const createdIdMap = new Map(
          (result.created_ids ?? []).map(c => [c.n_union, c.id])
        );
        const selectedIds = selectedRows
          .map(r => createdIdMap.get(r.n_union) ?? r.id)
          .filter((id): id is string => id !== null);

        if (selectedIds.length !== selectedRows.length) {
          setError('Uniones guardadas, pero no se pudo identificar algunas. Cierra y vuelve a abrir para continuar.');
          return;
        }

        onComplete(selectedIds);
      } else {
        onComplete([]);
      }
    } catch (err: unknown) {
      setError(classifyApiError(err).userMessage);
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

  const guardarLabel = saving
    ? 'GUARDANDO...'
    : operacion !== null && selectedRows.length > 0
      ? `FINALIZAR ${selectedRows.length} ${selectedRows.length === 1 ? 'UNIÓN' : 'UNIONES'}`
      : 'GUARDAR';

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      ariaLabel={`Gestionar uniones del spool ${spool.tag_spool}`}
      isTopOfStack={isTopOfStack}
      className="bg-zeues-navy border-4 border-white max-w-2xl !p-0 flex flex-col max-h-[85vh]"
    >
      {/* FIXED TOP ZONE */}
      <div className="shrink-0 p-4 pb-2">
        {/* Title row */}
        <div className="flex items-center justify-between mb-2 gap-2">
          <div className="min-w-0">
            <h2 className="font-mono font-black text-lg text-white">UNIONES</h2>
            <p className="font-mono text-sm text-white/70 truncate">{spool.tag_spool}</p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {showSelectAllButton && (
              <button
                type="button"
                onClick={someSelected ? handleDeselectAll : handleSelectAllAvailable}
                aria-label={someSelected ? 'Quitar selección de todas las uniones' : 'Seleccionar todas las uniones disponibles'}
                aria-pressed={someSelected}
                className="h-9 px-3 border-2 border-zeues-orange text-zeues-orange font-mono font-black text-xs cursor-pointer hover:bg-zeues-orange/10 focus:outline-none focus:ring-2 focus:ring-zeues-orange focus:ring-inset"
              >
                {someSelected ? 'QUITAR TODAS' : 'SELECCIONAR TODAS'}
              </button>
            )}
            <span className="font-mono text-sm text-white/70">
              {completedCount} de {rows.length}
            </span>
          </div>
        </div>

        {/* Quantity + Fill -- single row */}
        <div className="flex items-center gap-2 mt-2">
          {/* Quantity control -- direct numeric input, no +/- buttons */}
          <div className="flex items-center shrink-0">
            <label htmlFor="uniones-count" className="h-12 px-3 border-2 border-r-0 border-white text-white/70 font-mono font-black text-xs flex items-center">
              TOTAL
            </label>
            <input
              id="uniones-count"
              type="number"
              inputMode="numeric"
              min={1}
              max={MAX_UNIONS}
              value={countInput}
              onFocus={(e) => e.target.select()}
              onChange={(e) => {
                // Accept the raw string into local state so the user can clear
                // the field momentarily. Only commit to rows when the value
                // is a valid integer in range; leave rows untouched otherwise.
                const raw = e.target.value;
                setCountInput(raw);
                if (raw === '') return; // user is mid-edit
                const val = parseInt(raw, 10);
                if (!isNaN(val) && val >= 1 && val <= MAX_UNIONS) {
                  handleCountChange(val);
                }
              }}
              onBlur={() => {
                // Reconcile: if the user left the input empty or out of range,
                // snap back to the current rows.length so the UI never shows
                // an inconsistent number vs the rendered union cards.
                const val = parseInt(countInput, 10);
                if (isNaN(val) || val < 1) {
                  setCountInput(String(rows.length || 1));
                } else if (val > MAX_UNIONS) {
                  // Clamp to max; the previous onChange wouldn't have
                  // committed, so we fix both input and rows.
                  setCountInput(String(MAX_UNIONS));
                  handleCountChange(MAX_UNIONS);
                } else {
                  // Canonicalize (e.g. trim leading zeros) to whatever rows.length
                  // ended up being after handleCountChange committed.
                  setCountInput(String(rows.length));
                }
              }}
              aria-label="Cantidad total de uniones"
              className="h-12 w-16 bg-zeues-navy border-2 border-white text-white font-mono font-black text-lg text-center focus:outline-none focus:ring-2 focus:ring-zeues-orange focus:ring-inset [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
            />
          </div>

          {/* Separator */}
          <div className="w-px h-8 bg-white/20 shrink-0" />

          {/* Fill dropdowns */}
          {!loading && rows.length > 0 && (
            <>
              <select
                value={defaultDn ?? ''}
                onChange={(e) => handleDefaultDnChange(e.target.value)}
                aria-label="DN por defecto para uniones vacias"
                className="h-12 flex-1 min-w-0 bg-zeues-navy border border-white/40 text-white font-mono text-sm cursor-pointer focus:outline-none focus:ring-2 focus:ring-zeues-orange focus:ring-inset"
              >
                <option value="">DN</option>
                {DN_UNION_OPTIONS.map((dn) => (
                  <option key={dn.value} value={dn.value} aria-label={dn.ariaLabel}>{dn.label}</option>
                ))}
              </select>
              <select
                value={defaultTipo ?? ''}
                onChange={(e) => handleDefaultTipoChange(e.target.value)}
                aria-label="Tipo por defecto para uniones vacias"
                className="h-12 flex-1 min-w-0 bg-zeues-navy border border-white/40 text-white font-mono text-sm cursor-pointer focus:outline-none focus:ring-2 focus:ring-zeues-orange focus:ring-inset"
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
            {operacion !== null && <span className="min-w-[44px]" />}
            <span className="font-mono font-black text-xs text-white/60 min-w-[2rem] text-center">#</span>
            <span className="font-mono font-black text-xs text-white/60 flex-1">DN</span>
            <span className="font-mono font-black text-xs text-white/60 flex-1">TIPO</span>
            <span className="min-w-[44px]" />
          </div>
        )}
      </div>

      {/* SCROLLABLE MIDDLE ZONE */}
      {loading && (
        <div className="flex items-center justify-center py-8" role="status" aria-label="Cargando">
          <div className="w-8 h-8 border-2 border-white/30 border-t-white rounded-full animate-spin" aria-hidden="true" />
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
              const selectable = isRowSelectable(row, operacion, spoolArmDone);
              const needsArm = operacion === 'SOLD' && row.arm_worker === null && !spoolArmDone;

              const isFlashing = flashedRows.has(row.n_union);
              const isEven = index % 2 === 0;
              let borderClass = 'border-white/20';
              let bgClass = isEven ? 'bg-white/[0.02]' : '';
              if (isFlashing) {
                borderClass = 'border-zeues-orange';
                bgClass = 'bg-zeues-orange/10';
              } else if (row.selected) {
                borderClass = 'border-zeues-orange/60';
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
                  {/* Checkbox (selection modes only) */}
                  {operacion !== null && (
                    <button
                      onClick={() => handleToggleSelect(row.n_union)}
                      disabled={!selectable}
                      aria-label={
                        !selectable
                          ? `Union ${row.n_union} no seleccionable`
                          : row.selected
                            ? `Deseleccionar union ${row.n_union}`
                            : `Seleccionar union ${row.n_union}`
                      }
                      aria-pressed={row.selected}
                      className={`min-w-[44px] min-h-[44px] flex items-center justify-center shrink-0 border-2 focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset ${
                        row.selected
                          ? 'bg-zeues-orange border-zeues-orange'
                          : selectable
                            ? 'border-white/40 hover:border-white/60'
                            : 'border-white/10 opacity-30 cursor-not-allowed'
                      }`}
                    >
                      {row.selected && (
                        <svg className="w-5 h-5 text-white" viewBox="0 0 20 20" fill="currentColor">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      )}
                    </button>
                  )}

                  {/* Union number */}
                  <span className="font-mono font-black text-sm text-white min-w-[2.5rem] h-10 flex items-center justify-center bg-white/10 rounded">
                    {row.n_union}
                  </span>

                  {/* DN dropdown */}
                  <select
                    value={row.dn_union ?? ''}
                    onChange={(e) => handleDnChange(row.n_union, e.target.value)}
                    disabled={row.has_work}
                    aria-label={`DN union ${row.n_union}`}
                    className="h-12 flex-1 bg-zeues-navy border border-white/60 text-white font-mono text-sm cursor-pointer focus:outline-none focus:ring-2 focus:ring-zeues-orange focus:ring-inset disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    <option value="">DN</option>
                    {DN_UNION_OPTIONS.map((dn) => (
                      <option key={dn.value} value={dn.value} aria-label={dn.ariaLabel}>{dn.label}</option>
                    ))}
                  </select>

                  {/* TIPO dropdown */}
                  <select
                    value={row.tipo_union ?? ''}
                    onChange={(e) => handleTipoChange(row.n_union, e.target.value)}
                    disabled={row.has_work}
                    aria-label={`Tipo union ${row.n_union}`}
                    className="h-12 flex-1 bg-zeues-navy border border-white/60 text-white font-mono text-sm cursor-pointer focus:outline-none focus:ring-2 focus:ring-zeues-orange focus:ring-inset disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    <option value="">TIPO</option>
                    {TIPO_UNION_OPTIONS.map((tipo) => (
                      <option key={tipo} value={tipo}>{tipo}</option>
                    ))}
                  </select>

                  {/* Right zone: badges / delete / "Falta ARM" */}
                  <div className="min-w-[44px] min-h-[44px] flex flex-col items-center justify-center gap-0.5 shrink-0">
                    {/* Worker badges */}
                    {row.arm_worker && (operacion === null || operacion === 'ARM' || operacion === 'SOLD') && (
                      <span
                        className={`bg-white/10 text-white/70 font-mono px-2 py-0.5 whitespace-nowrap ${
                          operacion === 'SOLD' ? 'text-[10px]' : 'text-xs'
                        }`}
                        title={`Armador: ${row.arm_worker}`}
                      >
                        {row.arm_worker}
                      </span>
                    )}
                    {row.sol_worker && (operacion === null || operacion === 'SOLD') && (
                      <span
                        className="bg-white/10 text-white/70 font-mono text-xs px-2 py-0.5 whitespace-nowrap"
                        title={`Soldador: ${row.sol_worker}`}
                      >
                        {row.sol_worker}
                      </span>
                    )}
                    {/* "Falta ARM" label for SOLD mode */}
                    {needsArm && !row.has_work && (
                      <span className="text-yellow-400/60 font-mono text-xs whitespace-nowrap">Falta ARM</span>
                    )}
                    {/* Delete button (no work, not confirming) */}
                    {!row.has_work && !isConfirmingThis && !row.arm_worker && !row.sol_worker && (
                      <button
                        onClick={() => handleDeleteRow(row.n_union)}
                        aria-label={`Eliminar union ${row.n_union}`}
                        className="min-w-[44px] min-h-[44px] flex items-center justify-center text-white/40 hover:text-red-400 hover:bg-white/10 font-mono font-black text-sm focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset"
                      >
                        X
                      </button>
                    )}
                    {/* Delete confirmation */}
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
                          aria-label="Cancelar eliminación"
                          className="min-w-[44px] min-h-[44px] flex items-center justify-center text-white/40 hover:text-white hover:bg-white/10 font-mono font-black text-xs focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset"
                        >
                          No
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* FIXED BOTTOM ZONE */}
      {!loading && (
        <div className="shrink-0 p-4 pt-3 border-t border-white/10 flex flex-col gap-2">
          {/* Selection summary (only in selection modes with selections) */}
          {operacion !== null && selectedRows.length > 0 && (
            <div className="font-mono text-sm text-white/80 text-center py-1">
              Seleccionaste {selectedRows.length} {selectedRows.length === 1 ? 'union' : 'uniones'} = {selectedPD} PD
            </div>
          )}
          <button
            onClick={handleGuardar}
            disabled={saving || rows.length === 0}
            aria-label={saving ? 'Guardando...' : guardarLabel}
            className="w-full h-14 bg-zeues-orange text-white font-mono font-black text-lg disabled:opacity-40 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset"
          >
            {saving ? 'GUARDANDO...' : guardarLabel}
          </button>
          <button
            onClick={onClose}
            aria-label="Cancelar y cerrar"
            className="w-full h-12 border border-white/30 text-white/70 font-mono text-sm hover:border-white/50 focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset"
          >
            CANCELAR
          </button>
        </div>
      )}
    </Modal>
  );
}
