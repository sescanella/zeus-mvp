'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button, Loading, ErrorMessage } from '@/components';
import { useAppState } from '@/lib/context';
import { getWorkers } from '@/lib/api';
import type { Worker } from '@/lib/types';

export default function IdentificacionPage() {
  const router = useRouter();
  const { setState } = useAppState();
  const [workers, setWorkers] = useState<Worker[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchWorkers = async () => {
    try {
      setLoading(true);
      setError('');

      // API call real
      const workersData = await getWorkers();
      setWorkers(workersData);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Error al cargar trabajadores. Intenta nuevamente.';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWorkers();
  }, []);

  const handleSelectWorker = (worker: Worker) => {
    setState({ selectedWorker: worker });
    router.push('/operacion');
  };

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-3xl font-bold text-center text-[#FF5B00] mb-2">
          ZEUES - Trazabilidad
        </h1>
        <h2 className="text-2xl font-semibold text-center text-slate-700 mb-8">
          ¿Quién eres?
        </h2>

        {loading && <Loading />}
        {error && <ErrorMessage message={error} onRetry={fetchWorkers} />}

        {!loading && !error && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {workers.map((worker) => (
              <Button
                key={worker.id}
                onClick={() => handleSelectWorker(worker)}
              >
                {worker.nombre_completo}
              </Button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
