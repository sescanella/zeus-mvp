'use client';

import { useCallback, useEffect, useState } from 'react';
import { X } from 'lucide-react';
import { Modal } from '@/components/Modal';
import { appendNota, getNotas } from '@/lib/api';
import { classifyApiError } from '@/lib/error-classifier';
import type { SpoolCardData } from '@/lib/types';

const MAX_LENGTH = 500;

interface NotasModalProps {
  isOpen: boolean;
  spool: SpoolCardData;
  workerId: number | null; // current worker signing the note; null → modal shows read-only
  onClose: () => void;
  onSaved?: (tagSpool: string) => void;
  isTopOfStack?: boolean;
}

/**
 * NotasModal — v5.1 F-1.
 *
 * Read + append workflow for the per-spool `Notas` column. The previous
 * history is shown read-only (pre-wrap preserves newlines and the
 * `YYYYMMDD:` prefixes written by planning). Users can add a new entry;
 * backend prepends today's date in YYYYMMDD format and appends with \n.
 *
 * Requires `workerId` to save; if absent, the textarea/save button are
 * hidden (useful for a "viewer" mode — not currently invoked anywhere).
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

  useEffect(() => {
    if (isOpen) {
      setHistory('');
      setNewText('');
      setError(null);
      loadNotas();
    }
  }, [isOpen, loadNotas]);

  const trimmed = newText.trim();
  const canSave = workerId !== null && trimmed.length > 0 && !saving;

  async function handleSave() {
    if (!canSave || workerId === null) return;
    setSaving(true);
    setError(null);
    try {
      const res = await appendNota(spool.tag_spool, {
        worker_id: workerId,
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
      {workerId !== null && (
        <div className="shrink-0 p-4 pt-2 space-y-2">
          <label htmlFor="nota-input" className="sr-only">
            Nueva nota
          </label>
          <textarea
            id="nota-input"
            value={newText}
            onChange={(e) => setNewText(e.target.value.slice(0, MAX_LENGTH))}
            placeholder="Escribe una nota. Se guardará con la fecha de hoy."
            rows={3}
            aria-label="Escribir nueva nota"
            disabled={saving}
            className="w-full p-3 bg-zeues-navy border-2 border-white text-white font-mono text-sm placeholder:text-white/40 focus:outline-none focus:ring-2 focus:ring-zeues-orange focus:ring-inset disabled:opacity-60"
          />
          <div className="flex items-center justify-between gap-2">
            <span
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
      )}
    </Modal>
  );
}
