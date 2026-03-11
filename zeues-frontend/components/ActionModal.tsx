'use client';

import React from 'react';
import { Modal } from '@/components/Modal';
import { getValidActions } from '@/lib/spool-state-machine';
import type { SpoolCardData, Action, Operation } from '@/lib/spool-state-machine';

const ACTION_LABELS: Record<Action, string> = {
  INICIAR: 'INICIAR',
  FINALIZAR: 'FINALIZAR',
  PAUSAR: 'PAUSAR',
  CANCELAR: 'CANCELAR',
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
  onCancel: () => void;
  onClose: () => void;
  isTopOfStack?: boolean;
}

/**
 * ActionModal — Modal for selecting an action (INICIAR/FINALIZAR/PAUSAR/CANCELAR).
 *
 * Calls getValidActions(spool) to determine which buttons to show.
 * CANCELAR always calls onCancel() directly — no worker step needed (MODAL-04).
 * Other actions call onSelectAction(action).
 *
 * Plan: 03-01-PLAN.md Task 2
 */
export function ActionModal({
  isOpen,
  spool,
  operation,
  onSelectAction,
  onCancel,
  onClose,
  isTopOfStack,
}: ActionModalProps) {
  const validActions = getValidActions(spool);

  const handleActionClick = (action: Action) => {
    if (action === 'CANCELAR') {
      onCancel();
    } else {
      onSelectAction(action);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      ariaLabel="Seleccionar accion"
      isTopOfStack={isTopOfStack}
      className="bg-zeues-navy border-4 border-white rounded-none max-w-sm"
    >
      {/* Header */}
      <div className="mb-4">
        <h2 className="text-xl font-black text-white font-mono tracking-widest">
          SELECCIONAR ACCION
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
            onClick={() => handleActionClick(action)}
            aria-label={ACTION_LABELS[action]}
            className={`w-full h-16 border-4 font-mono font-black text-lg transition-colors focus:outline-none focus:ring-2 focus:ring-zeues-orange focus:ring-inset ${
              action === 'CANCELAR'
                ? 'border-red-500 text-red-500 active:bg-red-500 active:text-white'
                : 'border-white text-white active:bg-white active:text-zeues-navy'
            }`}
          >
            {ACTION_LABELS[action]}
          </button>
        ))}
      </div>
    </Modal>
  );
}
