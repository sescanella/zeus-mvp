'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';
import { Puzzle, Flame, SearchCheck, Wrench, ArrowLeft, X } from 'lucide-react';
import { ErrorMessage } from '@/components';
import { useAppState } from '@/lib/context';
import type { Worker } from '@/lib/types';

// Mapeo de operaciones a roles necesarios
const OPERATION_TO_ROLES: Record<string, string[]> = {
  'ARM': ['Armador', 'Ayudante'],
  'SOLD': ['Soldador', 'Ayudante'],
  'METROLOGIA': ['Metrologia'],
  'REPARACION': ['Armador', 'Soldador'],  // Union of Armador + Soldador roles for repairs
};

// Iconos por operación (Lucide)
const OPERATION_ICONS = {
  'ARM': Puzzle,
  'SOLD': Flame,
  'METROLOGIA': SearchCheck,
  'REPARACION': Wrench,
};

// Títulos dinámicos por operación
const OPERATION_TITLES: Record<string, string> = {
  'ARM': '¿Quién va a armar?',
  'SOLD': '¿Quién va a soldar?',
  'METROLOGIA': '¿Quién va a medir?',
  'REPARACION': '¿Quién va a reparar?',
};

export default function TrabajadorSelectionPage() {
  const router = useRouter();
  const { state, setState } = useAppState();
  const [filteredWorkers, setFilteredWorkers] = useState<Worker[]>([]);

  useEffect(() => {
    // Validar que existe operación seleccionada
    if (!state.selectedOperation) {
      router.push('/');
      return;
    }

    // Filtrar trabajadores que tienen el rol necesario para esta operación
    const requiredRoles = OPERATION_TO_ROLES[state.selectedOperation] || [];

    const eligible = state.allWorkers.filter(worker => {
      if (!worker.activo) return false;  // Solo trabajadores activos

      // Obtener roles del trabajador (usar array roles o fallback a rol singular)
      const workerRoles = worker.roles && worker.roles.length > 0
        ? worker.roles
        : (worker.rol ? [worker.rol] : []);

      if (workerRoles.length === 0) return false;  // Debe tener al menos un rol

      // Verificar si tiene alguno de los roles necesarios
      return workerRoles.some(role => requiredRoles.includes(role));
    });

    setFilteredWorkers(eligible);
  }, [state.selectedOperation, state.allWorkers, router]);

  const handleSelectWorker = (worker: Worker) => {
    setState({ selectedWorker: worker });

    // METROLOGIA and REPARACION skip tipo-interaccion and go directly to spool selection
    if (state.selectedOperation === 'METROLOGIA') {
      router.push('/seleccionar-spool?tipo=metrologia');
    } else if (state.selectedOperation === 'REPARACION') {
      router.push('/seleccionar-spool?tipo=reparacion');
    } else {
      router.push('/tipo-interaccion');
    }
  };

  if (!state.selectedOperation) return null;

  // Obtener icono y título dinámicos
  const IconComponent = OPERATION_ICONS[state.selectedOperation];
  const pageTitle = OPERATION_TITLES[state.selectedOperation];

  // Mapeo de operaciones a nombres para display
  const operationNames: Record<string, string> = {
    'ARM': 'ARMADO',
    'SOLD': 'SOLDADURA',
    'METROLOGIA': 'METROLOGÍA',
    'REPARACION': 'REPARACIÓN'
  };

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

      {/* Header con operación */}
      <div className="px-10 tablet:px-6 narrow:px-5 py-6 tablet:py-4 border-b-4 border-white/30">
        <div className="flex items-center justify-center gap-4 mb-4">
          <IconComponent size={48} strokeWidth={3} className="text-zeues-orange" />
          <h2 className="text-3xl narrow:text-2xl font-black text-white tracking-[0.25em] font-mono">
            {operationNames[state.selectedOperation]}
          </h2>
        </div>
        <p className="text-xl narrow:text-lg text-center text-white/70 font-mono tracking-[0.15em]">
          {pageTitle.toUpperCase()}
        </p>
      </div>

      {/* Content */}
      <div className="p-8 tablet:p-5 tablet:pb-footer">
        {filteredWorkers.length === 0 ? (
          <div>
            <div className="mb-8 text-center">
              <ErrorMessage
                message={`No hay trabajadores disponibles para ${state.selectedOperation}`}
              />
            </div>
            <button
              onClick={() => router.back()}
              className="
                w-full h-16
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
                VOLVER A SELECCIONAR OPERACIÓN
              </span>
            </button>
          </div>
        ) : (
          <>
            {/* Large touch buttons - VAR-5 */}
            <div className="flex flex-col gap-4 tablet:gap-3 mb-8 tablet:mb-6">
              {filteredWorkers.map((worker) => {
                // Obtener todos los roles del trabajador (multirol)
                const workerRoles = worker.roles && worker.roles.length > 0 ? worker.roles : ['Trabajador'];

                return (
                  <button
                    key={worker.id}
                    onClick={() => handleSelectWorker(worker)}
                    aria-label={`${worker.nombre} ${worker.apellido}`}
                    className="
                      h-24
                      bg-transparent
                      border-4 border-white
                      flex items-center justify-between px-8 narrow:px-4
                      cursor-pointer
                      active:bg-zeues-orange active:border-zeues-orange
                      transition-all duration-200
                      group
                      relative
                      overflow-hidden
                    "
                  >
                    {/* Highlight effect on active */}
                    <div className="absolute inset-0 border-l-8 border-zeues-orange opacity-0 group-active:opacity-100 transition-opacity duration-200"></div>

                    <div className="flex items-center gap-6 relative z-10">
                      <div className="flex flex-col items-center">
                        <span className="text-xs font-black text-white/50 font-mono group-active:text-white/80">
                          ID
                        </span>
                        <span className="text-3xl narrow:text-2xl font-black text-white font-mono group-active:text-white">
                          {worker.id}
                        </span>
                      </div>

                      <div className="h-16 w-1 bg-white/30 group-active:bg-white"></div>

                      <div className="text-left">
                        <h3 className="text-3xl narrow:text-2xl font-black text-white tracking-[0.15em] font-mono group-active:text-white leading-tight">
                          {worker.nombre}
                        </h3>
                        <h3 className="text-3xl narrow:text-2xl font-black text-white tracking-[0.15em] font-mono group-active:text-white leading-tight">
                          {worker.apellido}
                        </h3>
                      </div>
                    </div>

                    {/* Multi-rol badges */}
                    <div className="relative z-10 flex flex-wrap gap-2 justify-end">
                      {workerRoles.map((rol, index) => (
                        <div key={index} className="px-3 py-1 border-2 border-white/50 group-active:border-white">
                          <span className="text-xs font-black text-white/70 font-mono tracking-[0.15em] group-active:text-white">
                            {rol.toUpperCase()}
                          </span>
                        </div>
                      ))}
                    </div>
                  </button>
                );
              })}
            </div>

            {/* Fixed Navigation Footer */}
            <div className="fixed bottom-0 left-0 right-0 bg-[#001F3F] z-50 border-t-4 border-white/30 p-6 tablet:p-5">
              <div className="flex gap-4 tablet:gap-3 narrow:flex-col narrow:gap-3">
                <button
                  onClick={() => router.back()}
                  className="
                    flex-1 narrow:w-full h-16
                    bg-transparent
                    border-4 border-white
                    flex items-center justify-center gap-3
                    active:bg-white active:text-[#001F3F]
                    transition-all duration-200
                    group
                  "
                >
                  <ArrowLeft size={24} strokeWidth={3} className="text-white group-active:text-[#001F3F]" />
                  <span className="text-xl narrow:text-lg font-black text-white font-mono tracking-[0.15em] group-active:text-[#001F3F]">
                    VOLVER
                  </span>
                </button>

                <button
                  onClick={() => router.push('/')}
                  className="
                    flex-1 narrow:w-full h-16
                    bg-transparent
                    border-4 border-red-500
                    flex items-center justify-center gap-3
                    active:bg-red-500 active:border-red-500
                    transition-all duration-200
                    group
                  "
                >
                  <X size={24} strokeWidth={3} className="text-red-500 group-active:text-white" />
                  <span className="text-xl narrow:text-lg font-black text-red-500 font-mono tracking-[0.15em] group-active:text-white">
                    CANCELAR
                  </span>
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
