'use client';

import { useState, useEffect, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, User } from 'lucide-react';
import { BlueprintPageWrapper } from '@/components';
import { getWorkers, getDashboardOccupied } from '@/lib/api';
import type { DashboardOccupiedSpool } from '@/lib/api';
import type { Worker } from '@/lib/types';

interface WorkerGroup {
  worker_key: string;
  worker_display: string;
  spools: DashboardOccupiedSpool[];
}

function groupSpoolsByWorker(
  spools: DashboardOccupiedSpool[],
  nameMap: Map<string, string>
): WorkerGroup[] {
  const groupMap = new Map<string, DashboardOccupiedSpool[]>();
  for (const spool of spools) {
    const existing = groupMap.get(spool.worker_nombre);
    if (existing) existing.push(spool);
    else groupMap.set(spool.worker_nombre, [spool]);
  }
  return Array.from(groupMap.entries())
    .map(([key, groupSpools]) => ({
      worker_key: key,
      worker_display: nameMap.get(key) || key,
      spools: groupSpools,
    }))
    .sort((a, b) =>
      b.spools.length - a.spools.length ||
      a.worker_display.localeCompare(b.worker_display)
    );
}

export default function DashboardPage() {
  const router = useRouter();
  const [spools, setSpools] = useState<DashboardOccupiedSpool[]>([]);
  const [workerNameMap, setWorkerNameMap] = useState<Map<string, string>>(new Map());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError('');

        const spoolsPromise = getDashboardOccupied();

        const workersPromise = getWorkers().catch((): Worker[] => []);

        const [spoolsData, workers] = await Promise.all([spoolsPromise, workersPromise]);

        const nameMap = new Map<string, string>();
        for (const w of workers) {
          nameMap.set(w.nombre_completo, `${w.nombre} ${w.apellido || ''}`.trim());
        }

        setSpools(spoolsData);
        setWorkerNameMap(nameMap);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Error al cargar dashboard';
        setError(message);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

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

  const workerGroups = useMemo(
    () => groupSpoolsByWorker(spools, workerNameMap),
    [spools, workerNameMap]
  );

  return (
    <BlueprintPageWrapper>
      {/* Header with Back Button */}
      <div className="flex items-center justify-between px-8 pt-8 pb-6 border-b-4 border-white/30">
        <button
          onClick={() => router.push('/')}
          aria-label="Volver a la página principal"
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

        {!loading && !error && spools.length === 0 && (
          <div className="text-center text-white/70 font-mono text-xl mt-12">
            No hay spools ocupados actualmente
          </div>
        )}

        {!loading && !error && spools.length > 0 && (
          <>
            {/* Summary Bar */}
            <div className="flex justify-center gap-12 mb-8 py-4 border-2 border-white/30 bg-white/5">
              <p className="text-lg font-mono text-white/70 tracking-wider">
                TRABAJADORES ACTIVOS:{' '}
                <span className="font-black text-white">{workerGroups.length}</span>
              </p>
              <p className="text-lg font-mono text-white/70 tracking-wider">
                TOTAL OCUPADOS:{' '}
                <span className="font-black text-white">{spools.length}</span>
              </p>
            </div>

            {/* Worker Groups */}
            <div className="grid gap-8">
              {workerGroups.map(group => (
                <section
                  key={group.worker_key}
                  aria-label={`Spools de ${group.worker_display}`}
                  className="border-4 border-white"
                >
                  {/* Worker Header */}
                  <div className="flex items-center justify-between px-6 py-4 bg-white/10 border-b-4 border-white">
                    <div className="flex items-center gap-3">
                      <User size={28} strokeWidth={3} className="text-zeues-orange" />
                      <h2 className="text-2xl font-black text-white font-mono tracking-wider">
                        {group.worker_display}
                      </h2>
                    </div>
                    <span className="px-4 py-1 bg-zeues-orange text-white font-black font-mono text-lg tracking-wider">
                      {group.spools.length} {group.spools.length === 1 ? 'SPOOL' : 'SPOOLS'}
                    </span>
                  </div>

                  {/* Spool Cards */}
                  <div className="grid gap-3 p-4">
                    {group.spools.map(spool => (
                      <div
                        key={spool.tag_spool}
                        className="bg-transparent border-2 border-white/50 p-5"
                      >
                        <div className="flex justify-between items-start mb-2">
                          <h3 className="text-2xl narrow:text-xl font-black text-white font-mono tracking-wider">
                            {spool.tag_spool}
                          </h3>
                          <span className="text-lg font-mono text-white/70">
                            {getTimeOccupied(spool.fecha_ocupacion)}
                          </span>
                        </div>

                        <p className="text-lg font-mono text-white/90">
                          {spool.estado_detalle}
                        </p>
                      </div>
                    ))}
                  </div>
                </section>
              ))}
            </div>
          </>
        )}
      </div>
    </BlueprintPageWrapper>
  );
}
