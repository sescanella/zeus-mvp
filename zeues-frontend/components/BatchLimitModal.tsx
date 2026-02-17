'use client';

import { useRef, useEffect } from 'react';
import { Modal } from './Modal';
import { AlertCircle } from 'lucide-react';

interface BatchLimitModalProps {
  isOpen: boolean;
  onClose: () => void;
  maxBatch: number;
  totalAvailable: number;
}

export function BatchLimitModal({ isOpen, onClose, maxBatch, totalAvailable }: BatchLimitModalProps) {
  const dismissRef = useRef<HTMLButtonElement>(null);

  // Auto-focus dismiss button when modal opens
  useEffect(() => {
    if (isOpen) {
      // Small delay to ensure modal is rendered
      const timer = setTimeout(() => dismissRef.current?.focus(), 100);
      return () => clearTimeout(timer);
    }
  }, [isOpen]);

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      className="bg-zeues-navy border-4 border-zeues-orange rounded-none max-w-lg"
    >
      <div className="flex items-center gap-4 mb-4">
        <AlertCircle size={40} className="text-zeues-orange flex-shrink-0" strokeWidth={3} />
        <h3 className="text-xl font-black text-white font-mono">LIMITE DE SELECCION</h3>
      </div>

      <div className="space-y-3 mb-6">
        <p className="text-base text-white/90 font-mono">
          Solo se pueden seleccionar <span className="text-zeues-orange font-black">{maxBatch}</span> spools a la vez.
        </p>
        <p className="text-base text-white/90 font-mono">
          Se seleccionaron los primeros {maxBatch} de <span className="text-zeues-orange font-black">{totalAvailable}</span> disponibles.
        </p>
        <p className="text-sm text-white/60 font-mono">
          Usa los filtros de busqueda para reducir la lista.
        </p>
      </div>

      <button
        ref={dismissRef}
        onClick={onClose}
        className="w-full h-14 border-4 border-white text-white font-mono font-black text-lg tracking-[0.15em] active:bg-white active:text-zeues-navy transition-colors focus:outline-none focus:ring-2 focus:ring-zeues-orange focus:ring-inset"
      >
        ENTENDIDO
      </button>
    </Modal>
  );
}
