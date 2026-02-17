'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';
import { ArrowLeft, X, Loader2, AlertCircle, ChevronDown } from 'lucide-react';
import { BlueprintPageWrapper, FixedFooter } from '@/components';
import { useAppState } from '@/lib/context';
import { submitNoConformidad } from '@/lib/api';
import type { NoConformidadRequest } from '@/lib/types';

type OrigenType = NoConformidadRequest['origen'];
type TipoNCType = NoConformidadRequest['tipo'];

const ORIGEN_OPTIONS: { value: OrigenType; label: string }[] = [
  { value: 'Interna', label: 'INTERNA' },
  { value: 'Cliente/ITO', label: 'CLIENTE/ITO' },
  { value: 'Otro', label: 'OTRO' },
];

const TIPO_OPTIONS: { value: TipoNCType; label: string }[] = [
  { value: 'Proceso', label: 'PROCESO' },
  { value: 'Procedimiento/Protocolo', label: 'PROCEDIMIENTO' },
  { value: 'Producto', label: 'PRODUCTO' },
  { value: 'Post-Venta', label: 'POST-VENTA' },
  { value: 'Condición Insegura', label: 'COND. INSEGURA' },
];

export default function NoConformidadFormPage() {
  const router = useRouter();
  const { state } = useAppState();

  const [origen, setOrigen] = useState<OrigenType | null>(null);
  const [tipoNC, setTipoNC] = useState<TipoNCType | null>(null);
  const [descripcion, setDescripcion] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [expandedSection, setExpandedSection] = useState<'origen' | 'tipo' | null>(null);

  useEffect(() => {
    if (!state.selectedSpool || !state.selectedWorker) {
      router.push('/');
    }
  }, [state.selectedSpool, state.selectedWorker, router]);

  const isOrigenCollapsed = origen !== null && expandedSection !== 'origen';
  const isTipoCollapsed = tipoNC !== null && expandedSection !== 'tipo';

  const handleOrigenSelect = (value: OrigenType) => {
    setOrigen(value);
    setExpandedSection(null);
  };

  const handleTipoSelect = (value: TipoNCType) => {
    setTipoNC(value);
    setExpandedSection(null);
  };

  const handleSectionToggle = (section: 'origen' | 'tipo') => {
    setExpandedSection(prev => prev === section ? null : section);
  };

  const getOrigenLabel = () => ORIGEN_OPTIONS.find(o => o.value === origen)?.label ?? '';
  const getTipoLabel = () => TIPO_OPTIONS.find(o => o.value === tipoNC)?.label ?? '';

  const isFormValid = origen !== null && tipoNC !== null && descripcion.trim().length > 0;

  const handleSubmit = async () => {
    if (!isFormValid || !state.selectedSpool || !state.selectedWorker) return;

    try {
      setLoading(true);
      setError('');

      await submitNoConformidad({
        tag_spool: state.selectedSpool,
        worker_id: state.selectedWorker.id,
        origen: origen!,
        tipo: tipoNC!,
        descripcion: descripcion.trim(),
      });

      router.push('/exito');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Error desconocido';
      setError(errorMessage);
      setLoading(false);
    }
  };

  if (!state.selectedSpool || !state.selectedWorker) {
    return (
      <BlueprintPageWrapper>
        <div className="flex items-center justify-center min-h-screen">
          <div className="text-center">
            <p className="text-xl text-white font-mono mb-6">
              Redirigiendo al inicio...
            </p>
            <button
              onClick={() => router.push('/')}
              className="px-8 py-4 border-4 border-white text-white font-mono font-black active:bg-white active:text-zeues-navy"
            >
              IR AL INICIO
            </button>
          </div>
        </div>
      </BlueprintPageWrapper>
    );
  }

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
        <h2 className="text-3xl narrow:text-2xl font-black text-center text-white tracking-[0.25em] font-mono">
          NO CONFORMIDAD
        </h2>
      </div>

      {/* Content */}
      <div className="p-8 tablet:p-5 pb-footer tablet:pb-footer narrow:pb-footer">
        {/* Spool Info Card */}
        <div className="border-4 border-white p-6 mb-8">
          <div className="text-center">
            <p className="text-sm font-black text-white/50 font-mono mb-2">SPOOL SELECCIONADO</p>
            <h3 className="text-4xl narrow:text-3xl font-black text-zeues-orange font-mono tracking-wider">
              {state.selectedSpool}
            </h3>
          </div>
        </div>

        {/* Error Message */}
        {error && !loading && (
          <div className="border-4 border-red-500 p-8 mb-6 bg-red-500/10">
            <div className="flex items-center gap-4 mb-4">
              <AlertCircle size={48} className="text-red-500" strokeWidth={3} />
              <h3 className="text-2xl font-black text-red-500 font-mono">ERROR</h3>
            </div>
            <p className="text-lg text-white font-mono mb-6">{error}</p>
            <button
              onClick={() => { setError(''); handleSubmit(); }}
              className="px-6 py-3 border-4 border-white text-white font-mono font-black active:bg-white active:text-zeues-navy"
            >
              REINTENTAR
            </button>
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="flex flex-col items-center justify-center py-20">
            <Loader2 size={64} className="text-zeues-orange animate-spin mb-4" strokeWidth={3} />
            <span className="text-xl font-black text-white font-mono">REGISTRANDO...</span>
          </div>
        )}

        {/* Form Fields */}
        {!loading && (
          <div className="flex flex-col gap-8">
            {/* ORIGEN */}
            <div>
              {isOrigenCollapsed ? (
                <button
                  onClick={() => handleSectionToggle('origen')}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      handleSectionToggle('origen');
                    }
                  }}
                  aria-expanded={false}
                  aria-controls="origen-panel"
                  aria-label={`Origen seleccionado: ${getOrigenLabel()}. Pulsar para cambiar`}
                  className="
                    w-full h-16 narrow:h-14
                    border-4 border-white/20
                    flex items-center justify-between
                    px-5 font-mono
                    active:bg-white/10
                    transition-all duration-200
                    focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset
                  "
                >
                  <span className="text-sm font-black text-white/50 tracking-[0.15em]">ORIGEN</span>
                  <div className="flex items-center gap-3">
                    <span className="px-4 py-1.5 bg-zeues-orange/20 border-2 border-zeues-orange text-zeues-orange font-black text-sm tracking-[0.1em]">
                      {getOrigenLabel()}
                    </span>
                    <ChevronDown size={20} className="text-white/40" strokeWidth={3} />
                  </div>
                </button>
              ) : (
                <>
                  <p className="text-lg font-black text-white/70 font-mono tracking-[0.15em] mb-4">
                    ORIGEN
                  </p>
                  <div id="origen-panel" role="region" aria-label="Opciones de origen" className="grid grid-cols-3 gap-3">
                    {ORIGEN_OPTIONS.map((opt) => (
                      <button
                        key={opt.value}
                        onClick={() => handleOrigenSelect(opt.value)}
                        aria-pressed={origen === opt.value}
                        className={`
                          h-16 narrow:h-14
                          border-4 flex items-center justify-center
                          font-black font-mono tracking-[0.1em]
                          transition-all duration-200
                          text-base narrow:text-sm
                          focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset
                          ${origen === opt.value
                            ? 'bg-zeues-orange border-zeues-orange-border text-white'
                            : 'bg-transparent border-white/40 text-white/70 active:bg-white/10'
                          }
                        `}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </>
              )}
            </div>

            {/* TIPO NC */}
            <div>
              {isTipoCollapsed ? (
                <button
                  onClick={() => handleSectionToggle('tipo')}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      handleSectionToggle('tipo');
                    }
                  }}
                  aria-expanded={false}
                  aria-controls="tipo-panel"
                  aria-label={`Tipo seleccionado: ${getTipoLabel()}. Pulsar para cambiar`}
                  className="
                    w-full h-16 narrow:h-14
                    border-4 border-white/20
                    flex items-center justify-between
                    px-5 font-mono
                    active:bg-white/10
                    transition-all duration-200
                    focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset
                  "
                >
                  <span className="text-sm font-black text-white/50 tracking-[0.15em]">TIPO</span>
                  <div className="flex items-center gap-3">
                    <span className="px-4 py-1.5 bg-zeues-orange/20 border-2 border-zeues-orange text-zeues-orange font-black text-sm tracking-[0.1em]">
                      {getTipoLabel()}
                    </span>
                    <ChevronDown size={20} className="text-white/40" strokeWidth={3} />
                  </div>
                </button>
              ) : (
                <>
                  <p className="text-lg font-black text-white/70 font-mono tracking-[0.15em] mb-4">
                    TIPO
                  </p>
                  <div id="tipo-panel" role="region" aria-label="Opciones de tipo" className="grid grid-cols-2 gap-3 narrow:grid-cols-1">
                    {TIPO_OPTIONS.map((opt) => (
                      <button
                        key={opt.value}
                        onClick={() => handleTipoSelect(opt.value)}
                        aria-pressed={tipoNC === opt.value}
                        className={`
                          h-16 narrow:h-14 px-4
                          border-4 flex items-center justify-center
                          font-black font-mono tracking-[0.1em]
                          transition-all duration-200
                          text-base narrow:text-sm
                          focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset
                          ${tipoNC === opt.value
                            ? 'bg-zeues-orange border-zeues-orange-border text-white'
                            : 'bg-transparent border-white/40 text-white/70 active:bg-white/10'
                          }
                        `}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </>
              )}
            </div>

            {/* DESCRIPCIÓN */}
            <div>
              <label htmlFor="descripcion-input" className="text-lg font-black text-white/70 font-mono tracking-[0.15em] mb-4 block">
                DESCRIPCIÓN
              </label>
              <textarea
                id="descripcion-input"
                aria-describedby="descripcion-counter"
                value={descripcion}
                onChange={(e) => setDescripcion(e.target.value)}
                placeholder="Describe la no conformidad..."
                maxLength={2000}
                rows={4}
                className="
                  w-full p-4
                  bg-transparent
                  border-4 border-white/40
                  text-white text-lg font-mono
                  placeholder:text-white/30
                  focus:outline-none focus:ring-2 focus:ring-zeues-orange focus:ring-inset focus:border-zeues-orange
                  resize-none
                "
              />
              <p id="descripcion-counter" className="text-sm text-white/40 font-mono mt-2 text-right">
                {descripcion.length}/2000
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Fixed Navigation Footer */}
      {!loading && (
        <FixedFooter
          backButton={{
            text: "VOLVER",
            onClick: () => router.back(),
            icon: <ArrowLeft size={24} strokeWidth={3} />,
          }}
          primaryButton={isFormValid ? {
            text: "REGISTRAR",
            onClick: handleSubmit,
            variant: "primary",
          } : {
            text: "INICIO",
            onClick: () => router.push('/'),
            variant: "danger",
            icon: <X size={24} strokeWidth={3} />,
          }}
        />
      )}
    </BlueprintPageWrapper>
  );
}
