'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';
import { Puzzle, Flame, SearchCheck, Play, CheckCircle, XCircle, ArrowLeft, X } from 'lucide-react';
import { useAppState } from '@/lib/context';

export default function TipoInteraccionPage() {
  const router = useRouter();
  const { state, setState } = useAppState();

  useEffect(() => {
    if (!state.selectedWorker || !state.selectedOperation) {
      router.push('/');
    }
  }, [state, router]);

  const handleSelectTipo = (tipo: 'iniciar' | 'completar' | 'cancelar') => {
    setState({ selectedTipo: tipo });
    router.push(`/seleccionar-spool?tipo=${tipo}`);
  };

  if (!state.selectedWorker || !state.selectedOperation) return null;

  const operationLabel = state.selectedOperation === 'ARM' ? 'ARMADO' :
                        state.selectedOperation === 'SOLD' ? 'SOLDADURA' : 'METROLOGÍA';

  const OperationIcon = state.selectedOperation === 'ARM' ? Puzzle :
                        state.selectedOperation === 'SOLD' ? Flame : SearchCheck;

  // Get worker roles array (assuming roles is array, fallback to single rol)
  const workerRoles = (Array.isArray(state.selectedWorker.roles)
    ? state.selectedWorker.roles
    : [state.selectedWorker.rol]).filter((r): r is string => r !== undefined);

  return (
    <div
      className="min-h-screen bg-[#001F3F]"
      style={{
        backgroundImage: `
          linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
          linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)
        `,
        backgroundSize: '50px 50px'
      }}
    >
      {/* Logo */}
      <div className="flex justify-center pt-8 pb-6 tablet:header-compact border-b-4 border-white/30">
        <Image
          src="/logos/logo-grisclaro-F8F9FA.svg"
          alt="Kronos Mining"
          width={200}
          height={80}
          priority
        />
      </div>

      {/* Header */}
      <div className="px-10 tablet:px-6 py-6 tablet:py-4 border-b-4 border-white/30">
        <div className="flex items-center justify-center gap-4 mb-4">
          <OperationIcon size={48} strokeWidth={3} className="text-zeues-orange" />
          <h2 className="text-3xl font-black text-white tracking-[0.25em] font-mono">
            {operationLabel}
          </h2>
        </div>
        <p className="text-xl text-center text-white/70 font-mono tracking-[0.15em]">
          ¿QUÉ ACCIÓN REALIZARÁS?
        </p>
      </div>

      {/* Content */}
      <div className="p-8 tablet:p-5 tablet:pb-footer">
        {/* Worker Info Bar - expandido con double-row + left accent */}
        <div className="border-4 border-white mb-6 relative overflow-hidden">
          {/* Left accent bar */}
          <div className="absolute inset-y-0 left-0 w-2 bg-zeues-orange"></div>

          <div className="pl-8 pr-6 py-4">
            {/* Top row */}
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-black text-white/50 font-mono tracking-[0.2em]">
                TRABAJADOR ASIGNADO
              </span>
              <div className="flex items-center gap-2">
                {workerRoles.map((rol, index) => (
                  <div key={index} className="px-3 py-1 border-2 border-white/40">
                    <span className="text-xs font-black text-white/70 font-mono tracking-[0.15em]">
                      {rol.toUpperCase()}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Bottom row */}
            <div className="flex items-center gap-6">
              <div className="px-4 py-2 bg-zeues-orange border-2 border-zeues-orange">
                <span className="text-3xl font-black text-white font-mono">
                  #{state.selectedWorker.id}
                </span>
              </div>

              <div className="h-12 w-1 bg-white/30"></div>

              <div className="flex-1">
                <h3 className="text-3xl font-black text-white tracking-[0.15em] font-mono leading-tight">
                  {state.selectedWorker.nombre}
                </h3>
                <h3 className="text-3xl font-black text-white tracking-[0.15em] font-mono leading-tight">
                  {state.selectedWorker.apellido}
                </h3>
              </div>
            </div>
          </div>
        </div>

        <div className="mb-6 tablet:mb-4">
          {/* Grid 2 columnas */}
          <div className="grid grid-cols-2 gap-4 tablet:gap-3 mb-4">
            {/* INICIAR */}
            <button
              onClick={() => handleSelectTipo('iniciar')}
              className="
                h-40
                bg-transparent
                border-4 border-white
                flex flex-col items-center justify-center gap-4
                cursor-pointer
                active:bg-zeues-orange active:border-zeues-orange
                transition-all duration-200
                group
              "
            >
              <Play size={56} strokeWidth={3} className="text-white group-active:text-white" />
              <h3 className="text-2xl font-black text-white tracking-[0.2em] font-mono group-active:text-white">
                INICIAR
              </h3>
            </button>

            {/* COMPLETAR */}
            <button
              onClick={() => handleSelectTipo('completar')}
              className="
                h-40
                bg-transparent
                border-4 border-white
                flex flex-col items-center justify-center gap-4
                cursor-pointer
                active:bg-green-500 active:border-green-500
                transition-all duration-200
                group
              "
            >
              <CheckCircle size={56} strokeWidth={3} className="text-white group-active:text-white" />
              <h3 className="text-2xl font-black text-white tracking-[0.2em] font-mono group-active:text-white">
                COMPLETAR
              </h3>
            </button>
          </div>

          {/* CANCELAR - full width */}
          <button
            onClick={() => handleSelectTipo('cancelar')}
            className="
              w-full h-24
              bg-transparent
              border-4 border-red-500
              flex items-center justify-center gap-4
              cursor-pointer
              active:bg-red-500 active:border-red-500
              transition-all duration-200
              group
            "
          >
            <XCircle size={40} strokeWidth={3} className="text-red-500 group-active:text-white" />
            <h3 className="text-3xl font-black text-red-500 tracking-[0.2em] font-mono group-active:text-white">
              CANCELAR ACCIÓN
            </h3>
          </button>
        </div>

        {/* Fixed Navigation Footer */}
        <div className="fixed bottom-0 left-0 right-0 bg-[#001F3F] z-50 border-t-4 border-white/30 p-6 tablet:p-5">
          <div className="flex gap-4 tablet:gap-3">
            <button
              onClick={() => router.back()}
              className="
                flex-1 h-16
                bg-transparent
                border-4 border-white
                flex items-center justify-center gap-3
                active:bg-white active:text-[#001F3F]
                transition-all duration-200
                group
              "
            >
              <ArrowLeft size={24} strokeWidth={3} className="text-white group-active:text-[#001F3F]" />
              <span className="text-xl font-black text-white font-mono tracking-[0.15em] group-active:text-[#001F3F]">
                VOLVER
              </span>
            </button>

            <button
              onClick={() => router.push('/')}
              className="
                flex-1 h-16
                bg-transparent
                border-4 border-red-500
                flex items-center justify-center gap-3
                active:bg-red-500 active:border-red-500
                transition-all duration-200
                group
              "
            >
              <X size={24} strokeWidth={3} className="text-red-500 group-active:text-white" />
              <span className="text-xl font-black text-red-500 font-mono tracking-[0.15em] group-active:text-white">
                INICIO
              </span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
