'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';
import { Puzzle, Flame, SearchCheck, Play, Pause, CheckCircle, XCircle, ArrowLeft, X } from 'lucide-react';
import { useAppState } from '@/lib/context';
import { getUnionMetricas } from '@/lib/api';
import { cacheSpoolVersion, getCachedVersion } from '@/lib/version';

export default function TipoInteraccionPage() {
  const router = useRouter();
  const { state, setState, resetV4State } = useAppState();
  const [spoolVersion, setSpoolVersion] = useState<'v3.0' | 'v4.0' | null>(null);
  const [loadingVersion, setLoadingVersion] = useState(true);

  useEffect(() => {
    // Redirect check
    if (!state.selectedWorker || !state.selectedOperation) {
      router.push('/');
      return;
    }

    // METROLOGÍA bypass - skip P3, go directly to resultado
    if (state.selectedOperation === 'METROLOGIA') {
      router.push('/resultado-metrologia');
      return;
    }

    // Version detection for v4.0 workflow (only if spool already selected)
    // This page can be reached BEFORE spool selection (P2→P3 flow) or AFTER (v4.0 flow)
    const detectVersion = async () => {
      // If no spool selected yet, default to v3.0 workflow (traditional flow: P2→P3→P4)
      if (!state.selectedSpool) {
        setSpoolVersion('v3.0');
        setLoadingVersion(false);
        return;
      }

      // Check cache first
      const cached = getCachedVersion(state.selectedSpool);
      if (cached) {
        setSpoolVersion(cached);
        setLoadingVersion(false);
        return;
      }

      try {
        setLoadingVersion(true);

        // Call metricas endpoint
        const metrics = await getUnionMetricas(state.selectedSpool);
        // Detect version based on total_uniones field
        const version = metrics.total_uniones > 0 ? 'v4.0' : 'v3.0';

        setSpoolVersion(version);
        cacheSpoolVersion(state.selectedSpool, version);

      } catch (error) {
        console.error('Error detecting version:', error);
        // Default to v3.0 on error (backward compatible)
        setSpoolVersion('v3.0');
      } finally {
        setLoadingVersion(false);
      }
    };

    detectVersion();
  }, [state.selectedWorker, state.selectedOperation, state.selectedSpool, router]);

  const handleSelectTipo = (tipo: 'tomar' | 'pausar' | 'completar' | 'cancelar') => {
    setState({ selectedTipo: tipo });
    router.push(`/seleccionar-spool?tipo=${tipo}`);
  };

  // v4.0 button handlers
  const handleIniciar = () => {
    setState({ accion: 'INICIAR' });
    router.push('/seleccionar-spool');
  };

  const handleFinalizar = () => {
    setState({ accion: 'FINALIZAR' });
    // Skip P4 - worker already knows which spool they're working on
    router.push('/seleccionar-uniones');
  };

  // Back button with v4.0 cleanup
  const handleBack = () => {
    resetV4State();  // Clear v4.0 state
    router.back();
  };

  if (!state.selectedWorker || !state.selectedOperation) return null;

  // Loading state while detecting version
  if (loadingVersion) {
    return (
      <div className="min-h-screen bg-[#001F3F] flex items-center justify-center">
        <div className="text-white text-xl font-mono tracking-[0.15em]">
          Detectando versión...
        </div>
      </div>
    );
  }

  // Error boundary for version detection failure
  if (!loadingVersion && !spoolVersion) {
    return (
      <div className="min-h-screen bg-[#001F3F] flex items-center justify-center p-8">
        <div className="max-w-md w-full">
          <div className="bg-red-900/30 border-4 border-red-500 rounded p-6">
            <p className="text-red-200 text-lg font-mono mb-4">
              Error detectando versión. Usando modo v3.0.
            </p>
            <button
              onClick={() => window.location.reload()}
              className="
                w-full h-12
                bg-transparent
                border-4 border-white
                flex items-center justify-center
                cursor-pointer
                active:bg-white active:text-[#001F3F]
                transition-all duration-200
                group
              "
            >
              <span className="text-lg font-black text-white font-mono tracking-[0.15em] group-active:text-[#001F3F]">
                REINTENTAR
              </span>
            </button>
          </div>
        </div>
      </div>
    );
  }

  const operationLabel = state.selectedOperation === 'ARM' ? 'ARMADO' :
                        state.selectedOperation === 'SOLD' ? 'SOLDADURA' : 'METROLOGÍA';

  const OperationIcon = state.selectedOperation === 'ARM' ? Puzzle :
                        state.selectedOperation === 'SOLD' ? Flame : SearchCheck;

  // Get worker roles array (assuming roles is array, fallback to single rol)
  const workerRoles = (Array.isArray(state.selectedWorker.roles)
    ? state.selectedWorker.roles
    : [state.selectedWorker.rol]).filter((r): r is string => r !== undefined);

  // Version badge component
  const VersionBadge = ({ version }: { version: 'v3.0' | 'v4.0' }) => (
    <span className={`
      inline-flex items-center px-3 py-1 text-xs font-black tracking-[0.15em] rounded font-mono
      ${version === 'v4.0'
        ? 'text-green-700 bg-green-100 border-2 border-green-700'
        : 'text-gray-700 bg-gray-100 border-2 border-gray-700'}
    `}>
      {version}
    </span>
  );

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
      <div className="px-10 tablet:px-6 narrow:px-5 py-6 tablet:py-4 border-b-4 border-white/30">
        <div className="flex items-center justify-center gap-4 mb-4">
          <OperationIcon size={48} strokeWidth={3} className="text-zeues-orange" />
          <h2 className="text-3xl narrow:text-2xl font-black text-white tracking-[0.25em] font-mono">
            {operationLabel}
          </h2>
        </div>
        <p className="text-xl narrow:text-lg text-center text-white/70 font-mono tracking-[0.15em]">
          ¿QUÉ ACCIÓN REALIZARÁS?
        </p>
      </div>

      {/* Content */}
      <div className="p-8 tablet:p-5 tablet:pb-footer">
        {/* Worker Info Bar - expandido con double-row + left accent */}
        <div className="border-4 border-white mb-6 relative overflow-hidden">
          {/* Left accent bar */}
          <div className="absolute inset-y-0 left-0 w-2 bg-zeues-orange"></div>

          <div className="pl-8 pr-6 py-4 narrow:pl-4 narrow:pr-4 narrow:py-3">
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
                <span className="text-3xl narrow:text-2xl font-black text-white font-mono">
                  #{state.selectedWorker.id}
                </span>
              </div>

              <div className="h-12 w-1 bg-white/30"></div>

              <div className="flex-1">
                <h3 className="text-3xl narrow:text-2xl font-black text-white tracking-[0.15em] font-mono leading-tight">
                  {state.selectedWorker.nombre}
                </h3>
                <h3 className="text-3xl narrow:text-2xl font-black text-white tracking-[0.15em] font-mono leading-tight">
                  {state.selectedWorker.apellido}
                </h3>
              </div>
            </div>
          </div>
        </div>

        {/* Spool Info with Version Badge */}
        {state.selectedSpool && spoolVersion && (
          <div className="border-4 border-white/30 mb-6 p-5">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-xs font-black text-white/50 font-mono tracking-[0.2em] mb-2">
                  SPOOL SELECCIONADO
                </p>
                <p className="text-2xl narrow:text-xl font-black text-white font-mono tracking-[0.15em]">
                  {state.selectedSpool}
                </p>
              </div>
              <VersionBadge version={spoolVersion} />
            </div>
          </div>
        )}

        <div className="mb-6 tablet:mb-4">
          {/* v4.0 buttons - INICIAR/FINALIZAR */}
          {!loadingVersion && spoolVersion === 'v4.0' && (
            <div className="space-y-4">
              <h2 className="text-2xl font-black text-white tracking-[0.15em] font-mono mb-6">
                ¿QUÉ DESEAS HACER?
              </h2>

              <button
                onClick={handleIniciar}
                className="
                  w-full h-20
                  bg-transparent
                  border-4 border-white
                  flex items-center justify-center gap-4
                  cursor-pointer
                  active:bg-zeues-orange active:border-zeues-orange
                  transition-all duration-200
                  group
                "
              >
                <Play size={48} strokeWidth={3} className="text-white group-active:text-white" />
                <h3 className="text-3xl narrow:text-2xl font-black text-white tracking-[0.2em] font-mono group-active:text-white">
                  INICIAR
                </h3>
              </button>

              <button
                onClick={handleFinalizar}
                className="
                  w-full h-20
                  bg-transparent
                  border-4 border-white
                  flex items-center justify-center gap-4
                  cursor-pointer
                  active:bg-green-500 active:border-green-500
                  transition-all duration-200
                  group
                "
              >
                <CheckCircle size={48} strokeWidth={3} className="text-white group-active:text-white" />
                <h3 className="text-3xl narrow:text-2xl font-black text-white tracking-[0.2em] font-mono group-active:text-white">
                  FINALIZAR
                </h3>
              </button>

              <p className="text-sm text-white/60 mt-4 font-mono tracking-[0.1em] text-center">
                Versión 4.0 - Trabajo por uniones
              </p>

              {/* Help text for v4.0 */}
              <div className="mt-6 p-4 bg-blue-900/30 border-2 border-blue-500/50 rounded">
                <p className="text-sm text-blue-200 font-mono">
                  <strong className="text-blue-100">INICIAR:</strong> Ocupar spool para comenzar trabajo
                </p>
                <p className="text-sm text-blue-200 mt-2 font-mono">
                  <strong className="text-blue-100">FINALIZAR:</strong> Registrar uniones completadas y liberar spool
                </p>
              </div>
            </div>
          )}

          {/* v3.0 buttons - TOMAR/PAUSAR/COMPLETAR */}
          {!loadingVersion && spoolVersion === 'v3.0' && (
            <>
              <h2 className="text-2xl font-black text-white tracking-[0.15em] font-mono mb-6">
                SELECCIONA LA ACCIÓN
              </h2>

              {/* Grid 3 columnas - TOMAR/PAUSAR/COMPLETAR */}
              <div className="grid grid-cols-3 gap-4 tablet:gap-3 mb-4">
                {/* TOMAR */}
                <button
                  onClick={() => handleSelectTipo('tomar')}
                  className="
                    h-40 narrow:h-32
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
                    TOMAR
                  </h3>
                </button>

                {/* PAUSAR */}
                <button
                  onClick={() => handleSelectTipo('pausar')}
                  className="
                    h-40 narrow:h-32
                    bg-transparent
                    border-4 border-white
                    flex flex-col items-center justify-center gap-4
                    cursor-pointer
                    active:bg-yellow-500 active:border-yellow-500
                    transition-all duration-200
                    group
                  "
                >
                  <Pause size={56} strokeWidth={3} className="text-white group-active:text-white" />
                  <h3 className="text-2xl font-black text-white tracking-[0.2em] font-mono group-active:text-white">
                    PAUSAR
                  </h3>
                </button>

                {/* COMPLETAR */}
                <button
                  onClick={() => handleSelectTipo('completar')}
                  className="
                    h-40 narrow:h-32
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

              {/* CANCELAR - full width (REPARACIÓN only) */}
              {state.selectedOperation === 'REPARACION' && (
                <button
                  onClick={() => handleSelectTipo('cancelar')}
                  className="
                    w-full h-24 narrow:h-20
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
                  <h3 className="text-3xl narrow:text-2xl font-black text-red-500 tracking-[0.2em] font-mono group-active:text-white">
                    CANCELAR REPARACIÓN
                  </h3>
                </button>
              )}

              <p className="text-sm text-white/60 mt-4 font-mono tracking-[0.1em] text-center">
                Versión 3.0 - Trabajo por spool completo
              </p>

              {/* Help text for v3.0 */}
              <div className="mt-6 p-4 bg-gray-800/50 border-2 border-gray-500/50 rounded">
                <p className="text-sm text-gray-300 font-mono text-center">
                  Flujo tradicional: trabajo a nivel de spool completo
                </p>
              </div>
            </>
          )}
        </div>

        {/* Fixed Navigation Footer */}
        <div className="fixed bottom-0 left-0 right-0 bg-[#001F3F] z-50 border-t-4 border-white/30 p-6 tablet:p-5">
          <div className="flex gap-4 tablet:gap-3 narrow:flex-col narrow:gap-3">
            <button
              onClick={handleBack}
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
                INICIO
              </span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
