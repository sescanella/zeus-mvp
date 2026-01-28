'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';
import Link from 'next/link';
import { Puzzle, Flame, SearchCheck, Monitor, Wrench } from 'lucide-react';
import { Loading, ErrorMessage } from '@/components';
import { useAppState } from '@/lib/context';
import { getWorkers } from '@/lib/api';

export default function OperacionSelectionPage() {
  const router = useRouter();
  const { setState } = useAppState();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchWorkers = async () => {
    try {
      setLoading(true);
      setError('');

      // API call real - fetch todos los trabajadores y guardar en context
      const workersData = await getWorkers();

      // Guardar en context para reutilizar en P2 sin re-fetch
      setState({ allWorkers: workersData });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Error al cargar trabajadores. Intenta nuevamente.';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWorkers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Solo ejecutar una vez al montar

  const handleSelectOperation = (operacion: 'ARM' | 'SOLD' | 'METROLOGIA' | 'REPARACION') => {
    setState({ selectedOperation: operacion });

    // METROLOGIA and REPARACION skip tipo-interaccion and go directly to worker selection
    if (operacion === 'METROLOGIA' || operacion === 'REPARACION') {
      router.push('/operacion');
    } else {
      router.push('/operacion');
    }
  };

  // Si está cargando o hay error, mostrar en diseño Blueprint Industrial
  if (loading || error) {
    return (
      <div
        className="min-h-screen bg-[#001F3F] flex flex-col items-center justify-center"
        style={{
          backgroundImage: `
            linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)
          `,
          backgroundSize: '50px 50px'
        }}
      >
        {/* Logo */}
        <div className="mb-12">
          <Image
            src="/logos/logo-grisclaro-F8F9FA.svg"
            alt="Kronos Mining"
            width={200}
            height={80}
            priority
          />
        </div>

        {loading ? (
          <Loading />
        ) : (
          <div className="max-w-2xl mx-auto px-6">
            <ErrorMessage message={error} onRetry={fetchWorkers} />
          </div>
        )}
      </div>
    );
  }

  // Pantalla principal Blueprint Industrial
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
      {/* Logo 200px + Dashboard Link */}
      <div className="relative flex justify-center pt-8 pb-6 border-b-4 border-white/30">
        <Image
          src="/logos/logo-grisclaro-F8F9FA.svg"
          alt="Kronos Mining"
          width={200}
          height={80}
          priority
        />

        {/* Dashboard Link - Top Right */}
        <Link
          href="/dashboard"
          className="absolute right-8 top-8 flex items-center gap-2 px-4 py-3 bg-transparent border-2 border-white hover:bg-white/10 active:bg-zeues-orange active:border-zeues-orange transition-all duration-200 group"
        >
          <Monitor size={24} strokeWidth={3} className="text-white group-active:text-white" />
          <span className="text-sm font-black font-mono text-white tracking-wider group-active:text-white">
            DASHBOARD
          </span>
        </Link>
      </div>

      <div className="px-10 narrow:px-5 py-6 border-b-4 border-white/30">
        <h2 className="text-3xl narrow:text-2xl font-black text-center text-white tracking-[0.25em] font-mono">
          SELECCIONA OPERACIÓN
        </h2>
      </div>

      <div className="flex flex-col p-8 narrow:p-5 gap-6">
        {/* Card Armado */}
        <button
          onClick={() => handleSelectOperation('ARM')}
          className="
            h-[20vh] narrow:h-32 w-full
            bg-transparent
            border-4 border-white
            flex flex-col items-center justify-center gap-4 cursor-pointer
            active:bg-zeues-orange active:text-white
            transition-all duration-200
            relative
            group
          "
        >
          <Puzzle size={80} strokeWidth={3} className="text-zeues-orange group-active:text-white" />
          <h3 className="text-5xl narrow:text-4xl font-black text-white tracking-[0.2em] font-mono group-active:text-white">
            ARMADO
          </h3>
        </button>

        {/* Card Soldadura */}
        <button
          onClick={() => handleSelectOperation('SOLD')}
          className="
            h-[20vh] narrow:h-32 w-full
            bg-transparent
            border-4 border-white
            flex flex-col items-center justify-center gap-4 cursor-pointer
            active:bg-zeues-orange active:text-white
            transition-all duration-200
            relative
            group
          "
        >
          <Flame size={80} strokeWidth={3} className="text-zeues-orange group-active:text-white" />
          <h3 className="text-5xl narrow:text-4xl font-black text-white tracking-[0.2em] font-mono group-active:text-white">
            SOLDADURA
          </h3>
        </button>

        {/* Card Metrología */}
        <button
          onClick={() => handleSelectOperation('METROLOGIA')}
          className="
            h-[20vh] narrow:h-32 w-full
            bg-transparent
            border-4 border-white
            flex flex-col items-center justify-center gap-4 cursor-pointer
            active:bg-zeues-orange active:text-white
            transition-all duration-200
            relative
            group
          "
        >
          <SearchCheck size={80} strokeWidth={3} className="text-zeues-orange group-active:text-white" />
          <h3 className="text-5xl narrow:text-4xl font-black text-white tracking-[0.2em] font-mono group-active:text-white">
            METROLOGÍA
          </h3>
        </button>

        {/* Card Reparación */}
        <button
          onClick={() => handleSelectOperation('REPARACION')}
          className="
            h-[20vh] narrow:h-32 w-full
            bg-transparent
            border-4 border-white
            flex flex-col items-center justify-center gap-4 cursor-pointer
            active:bg-yellow-600 active:text-white
            transition-all duration-200
            relative
            group
          "
        >
          <Wrench size={80} strokeWidth={3} className="text-yellow-600 group-active:text-white" />
          <h3 className="text-5xl narrow:text-4xl font-black text-white tracking-[0.2em] font-mono group-active:text-white">
            REPARACIÓN
          </h3>
        </button>
      </div>
    </div>
  );
}
