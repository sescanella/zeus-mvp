'use client';

import { ArrowLeft, X } from 'lucide-react';

interface SpoolSelectionFooterProps {
  selectedCount: number;
  hasSpools: boolean;
  onContinue: () => void;
  onBack: () => void;
  onHome: () => void;
}

export function SpoolSelectionFooter({
  selectedCount,
  hasSpools,
  onContinue,
  onBack,
  onHome,
}: SpoolSelectionFooterProps) {
  return (
    <div className="fixed bottom-0 left-0 right-0 bg-zeues-navy z-50 border-t-4 border-white/30 p-6 tablet:p-5">
      <div className="flex flex-col gap-4 tablet:gap-3">
        {/* Continue button - first row (only show if spools available) */}
        {hasSpools && (
          <button
            onClick={onContinue}
            disabled={selectedCount === 0}
            className="w-full h-16 tablet:h-14 bg-transparent border-4 border-white flex items-center justify-center gap-4 cursor-pointer active:bg-zeues-orange active:border-zeues-orange transition-all disabled:opacity-30 disabled:cursor-not-allowed group"
          >
            <span className="text-xl tablet:text-lg narrow:text-lg font-black text-white font-mono tracking-[0.2em] group-active:text-white">
              CONTINUAR CON {selectedCount} SPOOL{selectedCount !== 1 ? 'S' : ''}
            </span>
          </button>
        )}

        {/* Back/Home buttons - always show */}
        <div className="flex gap-4 tablet:gap-3 narrow:flex-col narrow:gap-3">
          <button
            onClick={onBack}
            className="flex-1 narrow:w-full h-16 tablet:h-14 bg-transparent border-4 border-white flex items-center justify-center gap-3 active:bg-white active:text-zeues-navy transition-all group"
          >
            <ArrowLeft size={24} strokeWidth={3} className="text-white group-active:text-zeues-navy" />
            <span className="text-xl tablet:text-lg narrow:text-lg font-black text-white font-mono tracking-[0.15em] group-active:text-zeues-navy">
              VOLVER
            </span>
          </button>

          <button
            onClick={onHome}
            className="flex-1 narrow:w-full h-16 tablet:h-14 bg-transparent border-4 border-red-500 flex items-center justify-center gap-3 active:bg-red-500 active:border-red-500 transition-all group"
          >
            <X size={24} strokeWidth={3} className="text-red-500 group-active:text-white" />
            <span className="text-xl tablet:text-lg narrow:text-lg font-black text-red-500 font-mono tracking-[0.15em] group-active:text-white">
              INICIO
            </span>
          </button>
        </div>
      </div>
    </div>
  );
}
