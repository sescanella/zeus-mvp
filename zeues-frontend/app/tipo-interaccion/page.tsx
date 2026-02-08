'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';
import { Play, Pause, CheckCircle, XCircle, ArrowLeft, X } from 'lucide-react';
import { BlueprintPageWrapper, FixedFooter } from '@/components';
import { useAppState } from '@/lib/context';
import { getUnionMetricas } from '@/lib/api';
import { detectSpoolVersion } from '@/lib/version';
import { OPERATION_WORKFLOWS, OPERATION_ICONS } from '@/lib/operation-config';

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
      // If no spool selected yet, default to v4.0 workflow (new default)
      if (!state.selectedSpool) {
        setSpoolVersion('v4.0');
        setLoadingVersion(false);
        return;
      }

      try {
        setLoadingVersion(true);

        // Call metricas endpoint
        const metrics = await getUnionMetricas(state.selectedSpool);
        // Detect version based on total_uniones field using centralized utility
        const version = detectSpoolVersion(metrics);

        setSpoolVersion(version);

      } catch (error) {
        console.error('Error detecting version:', error);
        // Default to v4.0 on error (new default workflow)
        setSpoolVersion('v4.0');
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
    // Navigate to spool selection to show occupied spools by this worker
    router.push('/seleccionar-spool');
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
      <BlueprintPageWrapper>
        <div className="flex items-center justify-center min-h-screen">
          <div className="text-white text-xl font-mono tracking-[0.15em]">
            Detectando versión...
          </div>
        </div>
      </BlueprintPageWrapper>
    );
  }

  // Error boundary for version detection failure
  if (!loadingVersion && !spoolVersion) {
    return (
      <BlueprintPageWrapper>
        <div className="flex items-center justify-center min-h-screen p-8">
          <div className="max-w-md w-full">
          <div className="bg-red-900/30 border-4 border-red-500 rounded p-6">
            <p className="text-red-200 text-lg font-mono mb-4">
              Error detectando versión. Usando modo v3.0.
            </p>
            <button
              onClick={() => window.location.reload()}
              className="w-full h-12 bg-transparent border-4 border-white flex items-center justify-center cursor-pointer active:bg-white active:text-[#001F3F] transition-all duration-200 group"
            >
              <span className="text-lg font-black text-white font-mono tracking-[0.15em] group-active:text-[#001F3F]">
                REINTENTAR
              </span>
            </button>
          </div>
        </div>
        </div>
      </BlueprintPageWrapper>
    );
  }

  const operationLabel = OPERATION_WORKFLOWS[state.selectedOperation].label;
  const OperationIcon = OPERATION_ICONS[state.selectedOperation];

  // Get worker roles array (assuming roles is array, fallback to single rol)
  const workerRoles = (Array.isArray(state.selectedWorker.roles)
    ? state.selectedWorker.roles
    : [state.selectedWorker.rol]).filter((r): r is string => r !== undefined);

  return (
    <BlueprintPageWrapper>
      {/* Logo */}
      <div className="flex justify-center pt-4 pb-3 tablet:header-compact narrow:header-compact border-b-4 border-white/30">
        <Image
          src="/logos/logo-grisclaro-F8F9FA.svg"
          alt="Kronos Mining"
          width={140}
          height={56}
          priority
        />
      </div>

      {/* Header */}
      <div className="px-10 tablet:px-6 narrow:px-5 py-6 tablet:py-4 border-b-4 border-white/30">
        <div className="flex items-center justify-center gap-4">
          <OperationIcon size={48} strokeWidth={3} className="text-zeues-orange" />
          <h1 className="text-3xl narrow:text-2xl font-black text-white tracking-[0.25em] font-mono">
            {operationLabel}
          </h1>
        </div>
      </div>

      {/* Content */}
      <div className="p-8 tablet:p-5 pb-footer tablet:pb-footer narrow:pb-footer">
        {/* Worker Info Bar - compact inline with orange accent */}
        <div className="border-4 border-white/30 mb-6 relative overflow-hidden">
          <div className="absolute inset-y-0 left-0 w-2 bg-zeues-orange" />
          <div className="flex items-center h-[60px] narrow:h-[52px] pl-6 pr-4 narrow:pl-4 gap-4 narrow:gap-3">
            <div className="flex-shrink-0 bg-zeues-orange px-3 py-1">
              <span className="text-xl narrow:text-lg font-black text-white font-mono">#{state.selectedWorker.id}</span>
            </div>
            <div className="h-8 w-px bg-white/30" />
            <span className="text-lg narrow:text-base font-black text-white tracking-[0.1em] font-mono truncate">
              {state.selectedWorker.nombre} {state.selectedWorker.apellido}
            </span>
            <div className="flex items-center gap-2">
              {workerRoles.map((rol, index) => (
                <div key={index} className="flex-shrink-0 px-2 py-1 border-2 border-white/40">
                  <span className="text-xs font-black text-white/70 font-mono tracking-[0.15em]">{rol.toUpperCase()}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* v4.0 buttons - INICIAR/FINALIZAR (A1 massive colored style) */}
        {!loadingVersion && spoolVersion === 'v4.0' && (
          <div className="flex flex-col gap-4">
            <button
              onClick={handleIniciar}
              aria-label="Iniciar trabajo en spool"
              className="w-full h-[120px] tablet:h-[100px] narrow:h-[90px] bg-green-600 border-4 border-green-700 flex items-center justify-center gap-6 active:bg-green-700 active:border-green-800 transition-all duration-200"
            >
              <Play size={64} strokeWidth={3} className="text-white" />
              <span className="text-5xl tablet:text-4xl narrow:text-3xl font-black text-white tracking-[0.25em] font-mono">INICIAR</span>
            </button>
            <button
              onClick={handleFinalizar}
              aria-label="Finalizar trabajo en spool"
              className="w-full h-[120px] tablet:h-[100px] narrow:h-[90px] bg-zeues-orange border-4 border-[#E55D26] flex items-center justify-center gap-6 active:bg-[#E55D26] active:border-[#CC5322] transition-all duration-200"
            >
              <CheckCircle size={64} strokeWidth={3} className="text-white" />
              <span className="text-5xl tablet:text-4xl narrow:text-3xl font-black text-white tracking-[0.25em] font-mono">FINALIZAR</span>
            </button>
          </div>
        )}

        {/* v3.0 buttons - REPARACION (A1 massive colored style) */}
        {!loadingVersion && spoolVersion === 'v3.0' && (
          <div className="flex flex-col gap-4">
            <button
              onClick={() => handleSelectTipo('tomar')}
              aria-label="Tomar spool"
              className="w-full h-[100px] tablet:h-[90px] narrow:h-[80px] bg-green-600 border-4 border-green-700 flex items-center justify-center gap-6 active:bg-green-700 active:border-green-800 transition-all duration-200"
            >
              <Play size={56} strokeWidth={3} className="text-white" />
              <span className="text-4xl tablet:text-3xl narrow:text-2xl font-black text-white tracking-[0.25em] font-mono">TOMAR</span>
            </button>
            <button
              onClick={() => handleSelectTipo('pausar')}
              aria-label="Pausar trabajo"
              className="w-full h-[100px] tablet:h-[90px] narrow:h-[80px] bg-yellow-500 border-4 border-yellow-600 flex items-center justify-center gap-6 active:bg-yellow-600 active:border-yellow-700 transition-all duration-200"
            >
              <Pause size={56} strokeWidth={3} className="text-white" />
              <span className="text-4xl tablet:text-3xl narrow:text-2xl font-black text-white tracking-[0.25em] font-mono">PAUSAR</span>
            </button>
            <button
              onClick={() => handleSelectTipo('completar')}
              aria-label="Completar trabajo"
              className="w-full h-[100px] tablet:h-[90px] narrow:h-[80px] bg-blue-600 border-4 border-blue-700 flex items-center justify-center gap-6 active:bg-blue-700 active:border-blue-800 transition-all duration-200"
            >
              <CheckCircle size={56} strokeWidth={3} className="text-white" />
              <span className="text-4xl tablet:text-3xl narrow:text-2xl font-black text-white tracking-[0.25em] font-mono">COMPLETAR</span>
            </button>
            {state.selectedOperation === 'REPARACION' && (
              <button
                onClick={() => handleSelectTipo('cancelar')}
                aria-label="Cancelar reparación"
                className="w-full h-[80px] narrow:h-[70px] bg-transparent border-4 border-red-500 flex items-center justify-center gap-4 active:bg-red-500 active:border-red-500 transition-all duration-200 group"
              >
                <XCircle size={40} strokeWidth={3} className="text-red-500 group-active:text-white" />
                <span className="text-3xl narrow:text-2xl font-black text-red-500 tracking-[0.2em] font-mono group-active:text-white">CANCELAR REPARACIÓN</span>
              </button>
            )}
          </div>
        )}
      </div>

      {/* Fixed Navigation Footer */}
      <FixedFooter
        backButton={{
          text: "VOLVER",
          onClick: handleBack,
          icon: <ArrowLeft size={24} strokeWidth={3} />
        }}
        primaryButton={{
          text: "INICIO",
          onClick: () => router.push('/'),
          variant: "danger",
          icon: <X size={24} strokeWidth={3} />
        }}
      />
    </BlueprintPageWrapper>
  );
}
