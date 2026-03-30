'use client';

import React from 'react';
import { Modal } from '@/components/Modal';
import { getValidActions } from '@/lib/spool-state-machine';
import type { SpoolCardData, Action, Operation } from '@/lib/spool-state-machine';

const ACTION_LABELS: Record<Action, string> = {
  INICIAR: 'INICIAR',
  FINALIZAR: 'FINALIZAR',
  PAUSAR: 'PAUSAR',
};

const OPERATION_LABELS: Record<Operation, string> = {
  ARM: 'ARMADO',
  SOLD: 'SOLDADURA',
  MET: 'METROLOGIA',
  REP: 'REPARACION',
};

interface ActionModalProps {
  isOpen: boolean;
  spool: SpoolCardData;
  operation: Operation;
  onSelectAction: (action: Action) => void;
  onClose: () => void;
  isTopOfStack?: boolean;
}

/**
 * ActionModal — Modal for selecting an action (INICIAR/FINALIZAR/PAUSAR).
 *
 * Calls getValidActions(spool) to determine which buttons to show.
 * All actions call onSelectAction(action).
 * Modal X button calls onClose to dismiss without action.
 *
 * Plan: 03-01-PLAN.md Task 2
 */
export function ActionModal({
  isOpen,
  spool,
  operation,
  onSelectAction,
  onClose,
  isTopOfStack,
}: ActionModalProps) {
  const validActions = getValidActions(spool);

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      ariaLabel="Seleccionar acción"
      isTopOfStack={isTopOfStack}
      className="bg-zeues-navy border-4 border-white"
    >
      {/* Header */}
      <div className="mb-4">
        <h2 className="text-xl font-black text-white font-mono tracking-widest">
          SELECCIONAR ACCIÓN
        </h2>
        <p className="text-sm text-white/70 font-mono mt-1">
          {spool.tag_spool} — {OPERATION_LABELS[operation]}
        </p>
      </div>

      {/* Action buttons */}
      <div className="flex flex-col gap-3">
        {validActions.map((action) => (
          <button
            key={action}
            onClick={() => onSelectAction(action)}
            aria-label={ACTION_LABELS[action]}
            className="w-full h-16 border-4 border-white text-white font-mono font-black text-lg cursor-pointer transition-colors hover:bg-white/10 active:bg-white active:text-zeues-navy focus:outline-none focus:ring-2 focus:ring-zeues-orange focus:ring-inset"
          >
            {ACTION_LABELS[action]}
          </button>
        ))}

        <button
          onClick={onClose}
          className="w-full h-12 font-mono font-black text-white/70 border border-white/20 cursor-pointer hover:text-white hover:border-white/40 transition-colors focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset text-sm mt-1"
          aria-label="Cancelar y volver"
        >
          CANCELAR
        </button>
      </div>
    </Modal>
  );
}
