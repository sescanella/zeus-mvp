'use client';

import React from 'react';
import { Modal } from '@/components/Modal';
import { getValidOperations } from '@/lib/spool-state-machine';
import type { SpoolCardData, Operation } from '@/lib/spool-state-machine';

const OPERATION_LABELS: Record<Operation, string> = {
  ARM: 'ARMADO',
  SOLD: 'SOLDADURA',
  MET: 'METROLOGIA',
  REP: 'REPARACION',
};

interface OperationModalProps {
  isOpen: boolean;
  spool: SpoolCardData;
  onSelectOperation: (op: Operation) => void;
  onSelectMet: () => void;
  onClose: () => void;
  isTopOfStack?: boolean;
}

/**
 * OperationModal — Modal for selecting an operation (ARM/SOLD/MET/REP).
 *
 * Calls getValidOperations(spool) to determine which buttons to show.
 * MET operation routes to onSelectMet() (different flow — MetrologiaModal).
 * All other operations route to onSelectOperation(op).
 * Shows empty state when no operations are valid (BLOQUEADO).
 *
 * Plan: 03-01-PLAN.md Task 2
 */
export function OperationModal({
  isOpen,
  spool,
  onSelectOperation,
  onSelectMet,
  onClose,
  isTopOfStack,
}: OperationModalProps) {
  const validOperations = getValidOperations(spool);

  const handleOperationClick = (op: Operation) => {
    if (op === 'MET') {
      onSelectMet();
    } else {
      onSelectOperation(op);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      ariaLabel="Seleccionar operacion"
      isTopOfStack={isTopOfStack}
      className="bg-zeues-navy border-4 border-white rounded-none max-w-sm"
    >
      {/* Header */}
      <div className="mb-4">
        <h2 className="text-xl font-black text-white font-mono tracking-widest">
          SELECCIONAR OPERACION
        </h2>
        <p className="text-sm text-white/70 font-mono mt-1">{spool.tag_spool}</p>
      </div>

      {/* Operation buttons or empty state */}
      {validOperations.length === 0 ? (
        <div className="py-6 text-center">
          <p className="text-white/50 font-mono font-black text-sm">
            Sin operaciones disponibles
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {validOperations.map((op) => (
            <button
              key={op}
              onClick={() => handleOperationClick(op)}
              aria-label={OPERATION_LABELS[op]}
              className="w-full h-16 border-4 border-white font-mono font-black text-lg text-white active:bg-white active:text-zeues-navy transition-colors focus:outline-none focus:ring-2 focus:ring-zeues-orange focus:ring-inset"
            >
              {OPERATION_LABELS[op]}
            </button>
          ))}
        </div>
      )}
    </Modal>
  );
}
