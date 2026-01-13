'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button, Loading, ErrorMessage } from '@/components';
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

  const handleSelectOperation = (operacion: 'ARM' | 'SOLD' | 'METROLOGIA') => {
    setState({ selectedOperation: operacion });
    router.push('/operacion');
  };

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-3xl font-bold text-center text-[#FF5B00] mb-2">
          ZEUS by KM
        </h1>
        <h2 className="text-2xl font-semibold text-center text-slate-700 mb-8">
          ¿Qué operación vas a realizar?
        </h2>

        {loading && <Loading />}
        {error && <ErrorMessage message={error} onRetry={fetchWorkers} />}

        {!loading && !error && (
          <div className="space-y-4">
            <Button onClick={() => handleSelectOperation('ARM')}>
              🛠️ Armado
            </Button>
            <Button onClick={() => handleSelectOperation('SOLD')}>
              🔥 Soldadura
            </Button>
            <Button onClick={() => handleSelectOperation('METROLOGIA')}>
              📐 Metrología
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
