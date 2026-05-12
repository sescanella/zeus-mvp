'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { X } from 'lucide-react';
import { Modal } from '@/components/Modal';
import { appendNota, getNotas, getWorkers } from '@/lib/api';
import { classifyApiError } from '@/lib/error-classifier';
import type { SpoolCardData, Worker } from '@/lib/types';

const MAX_LENGTH = 500;

interface NotasModalProps {
  isOpen: boolean;
  spool: SpoolCardData;
  workerId: number | null; // hint: if the spool is occupied, preselect this worker; otherwise the modal asks the user to identify themselves.
  onClose: () => void;
  onSaved?: (tagSpool: string) => void;
  isTopOfStack?: boolean;
}

/**
 * NotasModal — v5.1 F-1.
 *
 * Read + append workflow for the per-spool `Notas` column. The previous
 * history is shown read-only (pre-wrap preserves newlines and the
 * `YYYYMMDD:` prefixes written by the backend).
 *
 * Author attribution: if `workerId` is provided (spool occupied), the
 * composer is enabled immediately and that worker signs the note. If
 * `workerId` is null (spool free), the modal loads the active worker list
 * and asks the user to pick who is signing before the textarea unlocks.
 */
export function NotasModal({
  isOpen,
  spool,
  workerId,
  onClose,
  onSaved,
  isTopOfStack = true,
}: NotasModalProps) {
  const [history, setHistory] = useState<string>('');
  const [newText, setNewText] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [pickedWorkerId, setPickedWorkerId] = useState<number | null>(null);
  const [workers, setWorkers] = useState<Worker[]>([]);
  const [workersLoading, setWorkersLoading] = useState(false);
  const [workersError, setWorkersError] = useState<string | null>(null);

  const loadNotas = useCallback(async () => {
    if (!spool.tag_spool) return;
    setLoading(true);
    setError(null);
    try {
      const res = await getNotas(spool.tag_spool);
      setHistory(res.nota);
    } catch (err: unknown) {
      setError(classifyApiError(err).userMessage);
    } finally {
      setLoading(false);
    }
  }, [spool.tag_spool]);

  const loadWorkers = useCallback(async () => {
    setWorkersLoading(true);
    setWorkersError(null);
    try {
      const list = await getWorkers();
      setWorkers(list);
    } catch (err: unknown) {
      setWorkersError(classifyApiError(err).userMessage);
    } finally {
      setWorkersLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isOpen) return;
    setHistory('');
    setNewText('');
    setError(null);
    setPickedWorkerId(workerId);
    loadNotas();
    if (workerId === null) {
      loadWorkers();
    }
  }, [isOpen, workerId, loadNotas, loadWorkers]);

  const pickedWorker = useMemo(
    () =>
      pickedWorkerId === null
        ? null
        : workers.find((w) => w.id === pickedWorkerId) ?? null,
    [pickedWorkerId, workers]
  );

  // The signature is shown only when we resolved the picked worker's name in
  // the locally loaded list. When the prop pre-seeded `pickedWorkerId` (spool
  // occupied case) we don't fetch the workers list, so we just don't show the
  // explicit "Firmando como" line — the spool occupation header already makes
  // authorship obvious.
  const showSignaturePicker = workerId === null;

  const trimmed = newText.trim();
  const canSave = pickedWorkerId !== null && trimmed.length > 0 && !saving;

  async function handleSave() {
    if (!canSave || pickedWorkerId === null) return;
    setSaving(true);
    setError(null);
    try {
      const res = await appendNota(spool.tag_spool, {
        worker_id: pickedWorkerId,
        texto: trimmed,
      });
      setHistory(res.nota);
      setNewText('');
      onSaved?.(spool.tag_spool);
    } catch (err: unknown) {
      setError(classifyApiError(err).userMessage);
    } finally {
      setSaving(false);
    }
  }

  const remaining = MAX_LENGTH - newText.length;
  const composerDisabled = saving || pickedWorkerId === null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      ariaLabel={`Notas del spool ${spool.tag_spool}`}
      isTopOfStack={isTopOfStack}
      className="bg-zeues-navy border-4 border-white max-w-2xl !p-0 flex flex-col max-h-[85vh]"
    >
      {/* Header */}
      <div className="shrink-0 flex items-center justify-between p-4 pb-2">
        <div className="min-w-0">
          <h2 className="font-mono font-black text-lg text-white">NOTAS</h2>
          <p className="font-mono text-sm text-white/70 truncate">{spool.tag_spool}</p>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Cerrar modal"
          className="min-w-[44px] min-h-[44px] flex items-center justify-center text-white/70 hover:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset"
        >
          <X size={24} strokeWidth={3} />
        </button>
      </div>

      {/* History (read-only) */}
      <div className="flex-1 min-h-[6rem] overflow-y-auto px-4 py-2 border-y-2 border-white/10">
        {loading && (
          <div
            className="flex items-center justify-center py-6"
            role="status"
            aria-label="Cargando notas"
          >
            <div
              className="w-6 h-6 border-2 border-white/30 border-t-white rounded-full animate-spin"
              aria-hidden="true"
            />
          </div>
        )}
        {!loading && history === '' && (
          <p className="font-mono text-sm text-white/50 italic">
            Sin notas previas. Agrega la primera abajo.
          </p>
        )}
        {!loading && history !== '' && (
          <pre className="font-mono text-sm text-white whitespace-pre-wrap break-words">
            {history}
          </pre>
        )}
      </div>

      {/* Error */}
      {error && (
        <div
          role="alert"
          className="shrink-0 px-4 py-2 text-red-400 font-mono text-sm bg-red-900/20 border-t-2 border-red-500/40"
        >
          {error}
        </div>
      )}

      {/* Composer */}
      <div className="shrink-0 p-4 pt-2 space-y-2">
        {showSignaturePicker && (
          <div className="space-y-1">
            <label
              htmlFor="nota-worker-select"
              className="block font-mono text-xs text-white/70"
            >
              Selecciona tu nombre para firmar la nota
            </label>
            {workersLoading && (
              <div
                className="flex items-center gap-2 py-2"
                role="status"
                aria-label="Cargando trabajadores"
              >
                <div
                  className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"
                  aria-hidden="true"
                />
                <span className="font-mono text-xs text-white/50">
                  Cargando trabajadores…
                </span>
              </div>
            )}
            {workersError && (
              <p
                role="alert"
                className="font-mono text-xs text-red-400"
              >
                {workersError}
              </p>
            )}
            {!workersLoading && !workersError && (
              <select
                id="nota-worker-select"
                value={pickedWorkerId ?? ''}
                onChange={(e) =>
                  setPickedWorkerId(e.target.value ? parseInt(e.target.value, 10) : null)
                }
                aria-required="true"
                aria-describedby="nota-worker-hint"
                disabled={saving || workers.length === 0}
                className="w-full h-12 px-3 bg-zeues-navy border-2 border-white text-white font-mono text-sm focus:outline-none focus:ring-2 focus:ring-zeues-orange focus:ring-inset disabled:opacity-60"
              >
                <option value="">— Elige un trabajador —</option>
                {workers.map((w) => (
                  <option key={w.id} value={w.id}>
                    {w.nombre}
                    {w.apellido ? ` ${w.apellido}` : ''} ({w.id})
                  </option>
                ))}
              </select>
            )}
            {pickedWorker && (
              <p className="font-mono text-xs text-white/70">
                Firmando como{' '}
                <span className="text-white font-black">
                  {pickedWorker.nombre}
                  {pickedWorker.apellido ? ` ${pickedWorker.apellido}` : ''}
                </span>
              </p>
            )}
          </div>
        )}

        <label htmlFor="nota-input" className="sr-only">
          Nueva nota
        </label>
        <textarea
          id="nota-input"
          value={newText}
          onChange={(e) => setNewText(e.target.value.slice(0, MAX_LENGTH))}
          placeholder={
            pickedWorkerId === null
              ? 'Selecciona tu nombre arriba para escribir una nota.'
              : 'Escribe una nota. Se guardará con la fecha de hoy.'
          }
          rows={3}
          aria-label="Escribir nueva nota"
          aria-describedby={showSignaturePicker ? 'nota-worker-hint' : undefined}
          disabled={composerDisabled}
          className="w-full p-3 bg-zeues-navy border-2 border-white text-white font-mono text-sm placeholder:text-white/40 focus:outline-none focus:ring-2 focus:ring-zeues-orange focus:ring-inset disabled:opacity-60"
        />
        <div className="flex items-center justify-between gap-2">
          <span
            id="nota-worker-hint"
            className={`font-mono text-xs ${
              remaining < 50 ? 'text-yellow-400' : 'text-white/50'
            }`}
            aria-live="polite"
          >
            {remaining} caracteres
          </span>
          <button
            type="button"
            onClick={handleSave}
            disabled={!canSave}
            aria-label="Guardar nueva nota"
            className="h-12 px-6 bg-zeues-orange border-2 border-zeues-orange text-zeues-navy font-mono font-black text-sm cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed hover:bg-zeues-orange/90 focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset"
          >
            {saving ? 'GUARDANDO...' : 'GUARDAR'}
          </button>
        </div>
      </div>
    </Modal>
  );
}
