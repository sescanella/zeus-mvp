'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft } from 'lucide-react';
import { BlueprintPageWrapper } from '@/components';

interface OccupiedSpool {
  tag_spool: string;
  worker_nombre: string;
  estado_detalle: string;
  fecha_ocupacion: string;
}

export default function DashboardPage() {
  const router = useRouter();
  const [spools, setSpools] = useState<Map<string, OccupiedSpool>>(new Map());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Fetch initial dashboard state
  useEffect(() => {
    const fetchInitialState = async () => {
      try {
        setLoading(true);
        setError('');

        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/dashboard/occupied`);
        if (!response.ok) {
          throw new Error(`Error ${response.status}: ${response.statusText}`);
        }

        const data: OccupiedSpool[] = await response.json();

        // Convert array to Map for O(1) updates
        const spoolMap = new Map<string, OccupiedSpool>();
        data.forEach(spool => {
          spoolMap.set(spool.tag_spool, spool);
        });

        setSpools(spoolMap);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Error al cargar dashboard';
        setError(message);
      } finally {
        setLoading(false);
      }
    };

    fetchInitialState();
  }, []);

  // Calculate time occupied
  const getTimeOccupied = (fecha: string): string => {
    try {
      const ocupado = new Date(fecha);
      const ahora = new Date();
      const diffMs = ahora.getTime() - ocupado.getTime();
      const diffMins = Math.floor(diffMs / 60000);

      if (diffMins < 60) {
        return `${diffMins}m`;
      }

      const hours = Math.floor(diffMins / 60);
      const mins = diffMins % 60;
      return `${hours}h ${mins}m`;
    } catch {
      return 'N/A';
    }
  };

  const spoolsArray = Array.from(spools.values());

  return (
    <BlueprintPageWrapper>
      {/* Header with Back Button */}
      <div className="flex items-center justify-between px-8 pt-8 pb-6 border-b-4 border-white/30">
        <button
          onClick={() => router.push('/')}
          className="flex items-center gap-2 px-4 py-3 bg-transparent border-2 border-white hover:bg-white/10 active:bg-zeues-orange active:border-zeues-orange transition-all duration-200 group"
        >
          <ArrowLeft size={24} strokeWidth={3} className="text-white group-active:text-white" />
          <span className="text-sm font-black font-mono text-white tracking-wider group-active:text-white">
            VOLVER
          </span>
        </button>

        <h1 className="text-3xl narrow:text-2xl font-black text-white tracking-[0.25em] font-mono">
          DASHBOARD
        </h1>

        <div className="w-[120px]">{/* Spacer for centering */}</div>
      </div>

      {/* Content */}
      <div className="px-8 narrow:px-5 py-6">
        {loading && (
          <div className="text-center text-white font-mono text-xl">
            Cargando...
          </div>
        )}

        {error && (
          <div className="text-center text-red-500 font-mono text-xl">
            {error}
          </div>
        )}

        {!loading && !error && spoolsArray.length === 0 && (
          <div className="text-center text-white/70 font-mono text-xl mt-12">
            No hay carretes ocupados actualmente
          </div>
        )}

        {!loading && !error && spoolsArray.length > 0 && (
          <div className="grid gap-4">
            {spoolsArray.map(spool => (
              <div
                key={spool.tag_spool}
                className="bg-transparent border-4 border-white p-6"
              >
                <div className="flex justify-between items-start mb-3">
                  <h2 className="text-3xl narrow:text-2xl font-black text-white font-mono tracking-wider">
                    {spool.tag_spool}
                  </h2>
                  <span className="text-lg font-mono text-white/70">
                    {getTimeOccupied(spool.fecha_ocupacion)}
                  </span>
                </div>

                <div className="space-y-2">
                  <p className="text-xl font-mono text-white">
                    <span className="text-white/70">Trabajador:</span>{' '}
                    <span className="font-black">{spool.worker_nombre}</span>
                  </p>

                  <p className="text-lg font-mono text-white/90">
                    {spool.estado_detalle}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Stats Footer */}
        {!loading && !error && (
          <div className="mt-8 pt-6 border-t-4 border-white/30 text-center">
            <p className="text-xl font-mono text-white/70">
              Total Ocupados:{' '}
              <span className="font-black text-white">{spoolsArray.length}</span>
            </p>
          </div>
        )}
      </div>
    </BlueprintPageWrapper>
  );
}
